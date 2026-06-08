"""Infraestructura transversal del servidor Power BI MCP.

Reúne los componentes usados por todos los demás dominios:

- :mod:`~powerbi_mcp.core.logger`      Configuración de logging.
- :mod:`~powerbi_mcp.core.exceptions`  Jerarquía de excepciones del dominio.
- :mod:`~powerbi_mcp.core.backup`      Respaldo automático y restauración.
- :mod:`~powerbi_mcp.core.validators`  Validadores base reutilizables.
"""

from __future__ import annotations

from powerbi_mcp.core.backup import BackupManager
from powerbi_mcp.core.exceptions import (
    BackupError,
    DaxValidationError,
    ModelError,
    PBIPParseError,
    PBIPWriteError,
    PowerBIMCPError,
    SecurityError,
    ValidationError,
)
from powerbi_mcp.core.logger import get_logger, setup_logging

__all__ = [
    "BackupError",
    "BackupManager",
    "DaxValidationError",
    "ModelError",
    "PBIPParseError",
    "PBIPWriteError",
    "PowerBIMCPError",
    "SecurityError",
    "ValidationError",
    "get_logger",
    "setup_logging",
]
