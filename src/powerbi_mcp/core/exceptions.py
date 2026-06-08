"""Jerarquía de excepciones del servidor Power BI MCP.

Todas las excepciones derivan de :class:`PowerBIMCPError`, lo que permite a las
herramientas MCP capturar de forma uniforme cualquier error del dominio y
devolver mensajes claros al cliente, conservando un ``code`` estable y detalles
estructurados para el log de auditoría.

Ejemplo::

    from powerbi_mcp.core.exceptions import PBIPParseError

    raise PBIPParseError(
        "No se encontró el archivo definition.pbism",
        details={"path": str(path)},
    )
"""

from __future__ import annotations

from typing import Any


class PowerBIMCPError(Exception):
    """Excepción base de todos los errores del servidor Power BI MCP.

    Attributes:
        message: Mensaje legible para humanos.
        code: Código corto y estable para identificar el tipo de error.
        details: Diccionario opcional con contexto estructurado (rutas,
            nombres de objetos, valores ofensores, etc.).
    """

    #: Código por defecto; las subclases lo sobreescriben.
    code: str = "powerbi_mcp_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details: dict[str, Any] = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serializa la excepción a un diccionario JSON-serializable.

        Returns:
            Diccionario con ``error``, ``code``, ``message`` y ``details``.
        """
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:  # pragma: no cover - representación trivial
        if self.details:
            return f"{self.message} | detalles={self.details}"
        return self.message


# ---------------------------------------------------------------------------
# Configuración / entorno
# ---------------------------------------------------------------------------
class ConfigError(PowerBIMCPError):
    """Error de configuración (variables de entorno o ``.env`` inválidos)."""

    code = "config_error"


# ---------------------------------------------------------------------------
# Validación genérica
# ---------------------------------------------------------------------------
class ValidationError(PowerBIMCPError):
    """Una entrada no superó las reglas de validación."""

    code = "validation_error"


# ---------------------------------------------------------------------------
# PBIP / PBIX
# ---------------------------------------------------------------------------
class PBIPError(PowerBIMCPError):
    """Error genérico relacionado con proyectos PBIP/PBIX."""

    code = "pbip_error"


class PBIPParseError(PBIPError):
    """No se pudo leer o interpretar la estructura de un proyecto PBIP."""

    code = "pbip_parse_error"


class PBIPWriteError(PBIPError):
    """No se pudo escribir un cambio en el proyecto PBIP."""

    code = "pbip_write_error"


class PBIPNotFoundError(PBIPError):
    """No se encontró el proyecto, archivo u objeto PBIP solicitado."""

    code = "pbip_not_found"


class PBIXError(PBIPError):
    """Error durante la conversión o empaquetado a PBIX."""

    code = "pbix_error"


# ---------------------------------------------------------------------------
# Modelo semántico
# ---------------------------------------------------------------------------
class ModelError(PowerBIMCPError):
    """Error en el modelo semántico (tablas, columnas, relaciones, medidas)."""

    code = "model_error"


class ObjectNotFoundError(ModelError):
    """El objeto del modelo (tabla/columna/medida/relación) no existe."""

    code = "object_not_found"


class DuplicateObjectError(ModelError):
    """Ya existe un objeto con el mismo nombre en el modelo."""

    code = "duplicate_object"


class DaxValidationError(ModelError):
    """Una expresión DAX no superó la validación sintáctica o semántica."""

    code = "dax_validation_error"


class RelationshipError(ModelError):
    """Relación inválida o ambigua entre tablas."""

    code = "relationship_error"


# ---------------------------------------------------------------------------
# IA / Machine Learning
# ---------------------------------------------------------------------------
class AIModelError(PowerBIMCPError):
    """Error al entrenar o aplicar un modelo de IA."""

    code = "ai_model_error"


class InsufficientDataError(AIModelError):
    """Datos insuficientes para entrenar o aplicar el modelo."""

    code = "insufficient_data"


# ---------------------------------------------------------------------------
# Visuales
# ---------------------------------------------------------------------------
class VisualError(PowerBIMCPError):
    """Error al construir o modificar un visual."""

    code = "visual_error"


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------
class BackupError(PowerBIMCPError):
    """Error al crear o restaurar un respaldo."""

    code = "backup_error"


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
class SecurityError(PowerBIMCPError):
    """Error de seguridad (encriptación, secretos, masking)."""

    code = "security_error"


# ---------------------------------------------------------------------------
# Power BI Service / REST API
# ---------------------------------------------------------------------------
class PowerBIAPIError(PowerBIMCPError):
    """Error en una llamada a la Power BI REST API."""

    code = "powerbi_api_error"


class AuthenticationError(PowerBIAPIError):
    """Fallo de autenticación contra Azure AD / Power BI."""

    code = "authentication_error"


__all__ = [
    "AIModelError",
    "AuthenticationError",
    "BackupError",
    "ConfigError",
    "DaxValidationError",
    "DuplicateObjectError",
    "InsufficientDataError",
    "ModelError",
    "ObjectNotFoundError",
    "PBIPError",
    "PBIPNotFoundError",
    "PBIPParseError",
    "PBIPWriteError",
    "PBIXError",
    "PowerBIAPIError",
    "PowerBIMCPError",
    "RelationshipError",
    "SecurityError",
    "ValidationError",
    "VisualError",
]
