"""Herramientas para seguridad, privacidad y auditoría.

6 herramientas:
- mask_data, generate_surrogate_keys, encrypt_value, decrypt_value
- generate_encryption_key, get_audit_log
"""

from __future__ import annotations

from typing import Any


def _tool(func):
    """Decorador: captura errores del dominio y los devuelve estructurados."""
    import functools
    from powerbi_mcp.core.exceptions import PowerBIMCPError
    from powerbi_mcp.core.logger import get_logger

    logger = get_logger(__name__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PowerBIMCPError as exc:
            logger.warning("Error en '%s': %s", func.__name__, exc)
            return {"ok": False, **exc.to_dict()}
        except Exception as exc:
            logger.exception("Error inesperado en '%s'", func.__name__)
            return {
                "ok": False,
                "error": exc.__class__.__name__,
                "code": "unexpected_error",
                "message": str(exc),
            }

    return wrapper


def register_security_tools(mcp) -> None:
    """Registra todas las herramientas de seguridad en la instancia MCP."""

    @mcp.tool()
    @_tool
    def mask_data(
        data: Any,
        columns: list[str] | None = None,
        strategy: str = "partial",
        auto_detect: bool = True,
    ) -> dict[str, Any]:
        """Enmascara columnas con información personal (PII) en un conjunto de datos.

        Args:
            data: Datos (ruta o registros).
            columns: Columnas a enmascarar (autodetecta si es ``None``).
            strategy: 'partial', 'full' o 'hash'.
            auto_detect: Si detecta automáticamente columnas PII.

        Returns:
            Datos enmascarados y columnas afectadas.
        """
        from powerbi_mcp.security.masking import mask_dataset

        return {"ok": True, **mask_dataset(data, columns=columns, strategy=strategy, auto_detect=auto_detect)}

    @mcp.tool()
    @_tool
    def generate_surrogate_keys(
        data: Any,
        column: str,
        method: str = "deterministic",
        key_length: int = 16,
    ) -> dict[str, Any]:
        """Genera claves subrogadas para una columna sensible.

        Args:
            data: Datos (ruta o registros).
            column: Columna a sustituir por claves subrogadas.
            method: 'deterministic' (HMAC) o 'sequential' (enteros).
            key_length: Longitud de la clave determinista.

        Returns:
            Tabla con claves subrogadas y tabla de mapeo.
        """
        from powerbi_mcp.security.surrogate_keys import generate_surrogate_keys as _gen

        return {"ok": True, **_gen(data, column, method=method, key_length=key_length)}

    @mcp.tool()
    @_tool
    def encrypt_value(value: str) -> dict[str, Any]:
        """Encripta un valor con la clave maestra configurada.

        Args:
            value: Texto a encriptar.

        Returns:
            El token cifrado.
        """
        from powerbi_mcp.security.encryption import Encryptor

        return {"ok": True, "token": Encryptor().encrypt(value)}

    @mcp.tool()
    @_tool
    def decrypt_value(token: str) -> dict[str, Any]:
        """Desencripta un token con la clave maestra configurada.

        Args:
            token: Token cifrado a desencriptar.

        Returns:
            El texto plano original.
        """
        from powerbi_mcp.security.encryption import Encryptor

        return {"ok": True, "value": Encryptor().decrypt(token)}

    @mcp.tool()
    @_tool
    def generate_encryption_key() -> dict[str, Any]:
        """Genera una nueva clave de encriptación Fernet.

        Returns:
            La clave generada (guárdala en PBIMCP_SECRET_KEY).
        """
        from powerbi_mcp.security.encryption import generate_key

        return {"ok": True, "key": generate_key()}

    @mcp.tool()
    @_tool
    def get_audit_log(action: str | None = None, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        """Consulta el registro de auditoría del servidor.

        Args:
            action: Filtra por acción (opcional).
            status: Filtra por estado 'success'/'error' (opcional).
            limit: Máximo de entradas a devolver.

        Returns:
            Entradas de auditoría que cumplen los filtros y un resumen.
        """
        from powerbi_mcp.security.audit import get_audit_logger

        auditor = get_audit_logger()
        return {
            "ok": True,
            "entries": auditor.query(action=action, status=status, limit=limit),
            "summary": auditor.summary(),
        }
