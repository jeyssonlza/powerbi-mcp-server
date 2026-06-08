"""Autenticación contra Azure AD para la Power BI REST API (MSAL).

Soporta dos flujos:

- **Service Principal** (client credentials): no interactivo, ideal para
  automatización. Requiere ``tenant_id``, ``client_id`` y ``client_secret``.
- **Device Code**: interactivo, el usuario autoriza en el navegador. Requiere
  ``tenant_id`` y ``client_id`` (app pública).

Los tokens se obtienen y cachean mediante MSAL. Las credenciales se leen de la
configuración (:mod:`powerbi_mcp.config`) y **nunca** se registran en logs.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from powerbi_mcp.config import Settings, get_settings
from powerbi_mcp.core.exceptions import AuthenticationError, ConfigError
from powerbi_mcp.core.logger import get_logger

if TYPE_CHECKING:
    from msal import ClientApplicationBase

logger = get_logger(__name__)

_AUTHORITY_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}"


class PowerBIAuth:
    """Gestiona la adquisición de tokens de acceso para la Power BI REST API.

    Implementa caching de tokens en disco para minimizar solicitudes a Azure AD.

    Args:
        settings: Configuración con las credenciales. Si es ``None``, se toma la
            configuración global.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._app: ClientApplicationBase | None = None
        self._token_cache: dict[str, object] | None = None
        self._token_expiry: float | None = None

    def _ensure_config(self, *, require_secret: bool) -> None:
        """Valida que existan las credenciales mínimas necesarias.

        Args:
            require_secret: Si es True, valida que exista client_secret.

        Raises:
            ConfigError: Si faltan credenciales requeridas.
        """
        if not self.settings.azure_tenant_id or not self.settings.azure_client_id:
            raise ConfigError(
                "Faltan credenciales de Azure (PBIMCP_AZURE_TENANT_ID y "
                "PBIMCP_AZURE_CLIENT_ID son obligatorios)."
            )
        if require_secret and not self.settings.azure_client_secret:
            raise ConfigError(
                "Falta PBIMCP_AZURE_CLIENT_SECRET para el flujo de service principal."
            )

    def _get_cache_file(self) -> Path:
        """Ruta del archivo de caché de tokens.

        Returns:
            Ruta absoluta del caché de tokens.
        """
        cache_dir = Path(self.settings.log_dir or ".").expanduser().resolve()
        return cache_dir / ".token_cache"

    def _load_cached_token(self) -> str | None:
        """Intenta cargar un token válido del caché en disco.

        Returns:
            El token si existe y no ha expirado, None en caso contrario.
        """
        cache_file = self._get_cache_file()
        if not cache_file.exists():
            return None

        try:
            import json

            data = json.loads(cache_file.read_text(encoding="utf-8"))
            expiry = data.get("expiry", 0)
            if expiry > time.time():
                token = data.get("token")
                if token:
                    logger.debug("Token del caché reutilizado (expira en %.0f segundos).", expiry - time.time())
                    return token
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Error al leer caché de tokens: %s", exc)
        return None

    def _save_token_cache(self, token: str, expires_in: int = 3600) -> None:
        """Guarda un token en caché con su tiempo de expiración.

        Args:
            token: Token de acceso a cachear.
            expires_in: Segundos hasta que expira (por defecto 1 hora).
        """
        try:
            import json

            cache_file = self._get_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            expiry = time.time() + expires_in
            cache_file.write_text(
                json.dumps({"token": token, "expiry": expiry}, ensure_ascii=False),
                encoding="utf-8",
            )
            cache_file.chmod(0o600)
        except OSError as exc:
            logger.warning("No se pudo guardar caché de tokens: %s", exc)

    @property
    def authority(self) -> str:
        """URL de autoridad de Azure AD para el inquilino configurado."""
        return _AUTHORITY_TEMPLATE.format(tenant_id=self.settings.azure_tenant_id)

    def acquire_token_service_principal(self) -> str:
        """Obtiene un token mediante el flujo de service principal (no interactivo).

        Este flujo es automático y no requiere interacción del usuario. Es ideal
        para automatización de tareas programadas.

        Returns:
            El token de acceso (bearer).

        Raises:
            ConfigError: Si faltan credenciales.
            AuthenticationError: Si Azure AD rechaza la solicitud.
        """
        self._ensure_config(require_secret=True)
        try:
            from msal import ConfidentialClientApplication
        except ImportError as exc:  # pragma: no cover
            raise AuthenticationError("La librería 'msal' no está instalada.") from exc

        try:
            app = ConfidentialClientApplication(
                client_id=self.settings.azure_client_id,
                client_credential=self.settings.azure_client_secret,
                authority=self.authority,
            )
            result = app.acquire_token_for_client(scopes=self.settings.azure_scope_list)
            return self._extract_token(result)
        except Exception as exc:
            raise AuthenticationError(
                f"Error al adquirir token (service principal): {exc}",
                details={"authority": self.authority},
            ) from exc

    def acquire_token_device_code(self) -> str:
        """Obtiene un token mediante el flujo de código de dispositivo (interactivo).

        Guía al usuario a abrir un navegador, introducir un código de dispositivo
        y autorizar la aplicación. Las instrucciones se muestran en stderr vía logger.

        Returns:
            El token de acceso (bearer).

        Raises:
            ConfigError: Si faltan credenciales.
            AuthenticationError: Si falla la autorización.
        """
        self._ensure_config(require_secret=False)
        try:
            from msal import PublicClientApplication
        except ImportError as exc:  # pragma: no cover
            raise AuthenticationError("La librería 'msal' no está instalada.") from exc

        try:
            app = PublicClientApplication(
                client_id=self.settings.azure_client_id,
                authority=self.authority,
            )
            flow = app.initiate_device_flow(scopes=self.settings.azure_scope_list)
            if "user_code" not in flow:
                raise AuthenticationError(
                    "No se pudo iniciar el flujo de device code.",
                    details={"response": flow},
                )
            # El mensaje guía al usuario; va a stderr vía logger (no a stdout/MCP).
            logger.warning("Acción requerida: %s", flow.get("message", ""))
            result = app.acquire_token_by_device_flow(flow)
            return self._extract_token(result)
        except Exception as exc:
            if isinstance(exc, AuthenticationError):
                raise
            raise AuthenticationError(
                f"Error al adquirir token (device code): {exc}",
                details={"authority": self.authority},
            ) from exc

    def get_token(self) -> str:
        """Obtiene un token usando el mejor flujo disponible según la config.

        Primero intenta reutilizar un token en caché si está disponible y
        válido; en caso contrario, adquiere uno nuevo usando el flujo
        configurado (service principal o device code).

        Returns:
            El token de acceso (bearer).
        """
        # Intentar reutilizar caché
        cached = self._load_cached_token()
        if cached:
            return cached

        # Adquirir nuevo token
        token = (
            self.acquire_token_service_principal()
            if self.settings.azure_client_secret
            else self.acquire_token_device_code()
        )
        # Cachear para usos posteriores
        self._save_token_cache(token, expires_in=3600)
        return token

    def refresh_token(self, force: bool = False) -> str:
        """Fuerza una renovación del token.

        Args:
            force: Si es True, adquiere uno nuevo sin revisar caché.

        Returns:
            El token de acceso renovado.
        """
        logger.info("Renovando token de acceso...")
        token = (
            self.acquire_token_service_principal()
            if self.settings.azure_client_secret
            else self.acquire_token_device_code()
        )
        self._save_token_cache(token, expires_in=3600)
        return token

    @staticmethod
    def _extract_token(result: dict[str, object] | None) -> str:
        """Extrae el ``access_token`` de la respuesta de MSAL o lanza error."""
        if not result or "access_token" not in result:
            error = (result or {}).get("error_description") or (result or {}).get("error")
            raise AuthenticationError(
                "No se obtuvo token de acceso de Azure AD.",
                details={"error": str(error) if error else "respuesta vacía"},
            )
        logger.info("Token de acceso de Power BI adquirido correctamente.")
        return str(result["access_token"])


__all__ = ["PowerBIAuth"]
