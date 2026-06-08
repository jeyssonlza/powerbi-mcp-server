"""Configuración global del servidor Power BI MCP.

La configuración se carga (en orden de precedencia) desde:

1. Argumentos explícitos al instanciar :class:`Settings`.
2. Variables de entorno con prefijo ``PBIMCP_``.
3. Archivo ``.env`` en el directorio de trabajo.
4. Valores por defecto definidos aquí.

Uso típico::

    from powerbi_mcp.config import get_settings

    settings = get_settings()
    print(settings.log_level)

La instancia se cachea con :func:`functools.lru_cache` para que toda la
aplicación comparta la misma configuración.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Configuración tipada del servidor, cargada desde entorno y ``.env``.

    Todos los campos pueden sobreescribirse con variables de entorno usando el
    prefijo ``PBIMCP_`` (por ejemplo ``PBIMCP_LOG_LEVEL=DEBUG``).
    """

    model_config = SettingsConfigDict(
        env_prefix="PBIMCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------------------------------------------- General
    log_level: LogLevel = Field(
        default="INFO",
        description="Nivel de detalle del logging.",
    )
    log_dir: Path = Field(
        default=Path("logs"),
        description="Directorio donde se escriben los archivos de log.",
    )
    workspace_dir: Path | None = Field(
        default=None,
        description="Directorio raíz por defecto de los proyectos PBIP.",
    )

    # ----------------------------------------------------------------- Backups
    backup_enabled: bool = Field(
        default=True,
        description="Si es True, se crea un respaldo antes de cada escritura.",
    )
    backup_dir: Path = Field(
        default=Path(".pbip_backups"),
        description="Directorio donde se almacenan los respaldos.",
    )
    backup_max: int = Field(
        default=50,
        ge=0,
        description="Máximo de respaldos a conservar por proyecto (0 = ilimitado).",
    )
    backup_encrypt: bool = Field(
        default=False,
        description="Encriptar los respaldos (requiere secret_key).",
    )

    # ------------------------------------------------------------ Seguridad
    secret_key: str | None = Field(
        default=None,
        description="Clave maestra (Fernet/AES) para encriptación de secretos.",
    )
    surrogate_salt: str | None = Field(
        default=None,
        description="Salt para la generación de claves subrogadas (HMAC).",
    )

    # ------------------------------------------------------ Power BI REST API
    azure_tenant_id: str | None = Field(default=None, description="Azure AD Tenant ID.")
    azure_client_id: str | None = Field(default=None, description="Azure AD Client ID.")
    azure_client_secret: str | None = Field(
        default=None, description="Azure AD Client Secret (service principal)."
    )
    azure_scopes: str = Field(
        default="https://analysis.windows.net/powerbi/api/.default",
        description="Scopes OAuth2 separados por espacio.",
    )

    # ------------------------------------------- Analysis Services (opcional)
    as_connection_string: str | None = Field(
        default=None,
        description="Cadena de conexión XMLA a un Analysis Services / Power BI Desktop.",
    )

    # --------------------------------------------------------------- Validadores
    @field_validator("log_dir", "backup_dir", mode="before")
    @classmethod
    def _expand_path(cls, value: str | Path) -> Path:
        """Expande ``~`` y variables a una ruta absoluta resoluble."""
        return Path(value).expanduser()

    @property
    def azure_scope_list(self) -> list[str]:
        """Devuelve los scopes OAuth2 como lista."""
        return [s for s in self.azure_scopes.split(" ") if s]

    @property
    def powerbi_api_configured(self) -> bool:
        """True si hay credenciales mínimas para usar la REST API."""
        return bool(self.azure_tenant_id and self.azure_client_id)

    def ensure_directories(self) -> None:
        """Crea los directorios de logs y respaldos si no existen."""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if self.backup_enabled:
            self.backup_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la instancia única (cacheada) de :class:`Settings`.

    Returns:
        Configuración global compartida por toda la aplicación.
    """
    return Settings()


def reload_settings() -> Settings:
    """Limpia la caché y recarga la configuración desde el entorno/``.env``.

    Útil en tests o tras modificar variables de entorno en tiempo de ejecución.

    Returns:
        La nueva instancia de configuración.
    """
    get_settings.cache_clear()
    return get_settings()
