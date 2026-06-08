"""Servidor MCP de Power BI: registro de todas las herramientas.

Define la instancia :data:`mcp` (FastMCP) y registra las herramientas que el
asistente puede invocar en lenguaje natural, agrupadas por dominio:

- Proyecto (abrir, estructura, backups, PBIX).
- Modelo (tablas, columnas, medidas, relaciones, DAX).
- IA (anomalías, clustering, forecasting, RFM, correlación, árbol, regresión,
  clasificación) con integración opcional al modelo.
- Visuales (páginas, visuales PBIR, HTML, temas).
- Análisis (calidad, perfilado, rendimiento, buenas prácticas).
- Documentación (técnica, diccionario, changelog).
- Seguridad (masking, claves subrogadas, encriptación, auditoría).
- Power BI Service (REST API).

Cada herramienta está tipada y documentada; los errores del dominio se capturan
y devuelven de forma estructurada mediante el decorador :func:`_tool`.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, Literal, TypeVar

from powerbi_mcp import __version__
from powerbi_mcp.config import get_settings
from powerbi_mcp.core.exceptions import PowerBIMCPError
from powerbi_mcp.core.logger import get_logger, setup_logging

logger = get_logger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "El SDK de MCP no está instalado. Ejecuta 'pip install mcp' "
        "o 'pip install -e .' en la raíz del proyecto."
    ) from exc

#: Instancia principal del servidor MCP.
mcp = FastMCP("powerbi-mcp")

F = TypeVar("F", bound=Callable[..., Any])


def _tool(func: F) -> F:
    """Decorador: captura errores del dominio y los devuelve estructurados.

    Preserva la firma original (vía :func:`functools.wraps`) para que FastMCP
    genere correctamente el esquema de parámetros de la herramienta.
    """

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

    return wrapper  # type: ignore[return-value]


def _audit_action(
    action: str,
    *,
    target: str = "",
    status: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Registra auditoria sin acoplar cada herramienta al logger concreto."""
    from powerbi_mcp.security.audit import audit

    audit(action, target=target, status=status, details=details)


def _reload_after_write(dry_run: bool) -> None:
    """Mantiene la sesion sincronizada con disco tras escrituras PBIR."""
    from powerbi_mcp.session import session

    if not dry_run:
        session.reload()


def _commit_model(
    reason: str,
    *,
    action: str,
    object_type: str,
    object_name: str,
    dry_run: bool,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Persiste el modelo activo y registra changelog + auditoría.

    Args:
        reason: Motivo del cambio (para backup/changelog).
        action: Acción (estilo changelog: added/changed/removed...).
        object_type: Tipo de objeto afectado.
        object_name: Nombre del objeto afectado.
        dry_run: Si es ``True``, no escribe en disco.
        payload: Resultado de la operación a incluir en la respuesta.

    Returns:
        Respuesta combinada con el resultado de persistencia.
    """
    from powerbi_mcp.docs.changelog import record_change
    from powerbi_mcp.pbip.writer import save_semantic_model
    from powerbi_mcp.session import session

    project = session.require()
    try:
        save_result = save_semantic_model(project, reason=reason, dry_run=dry_run)
    finally:
        if dry_run:
            session.reload()
    if not dry_run:
        record_change(
            project.root_path,
            action=action,
            object_type=object_type,
            object_name=object_name,
            description=reason,
        )
    _audit_action(action, target=object_name, details={"dry_run": dry_run})
    return {"ok": True, "dry_run": dry_run, "save": save_result, **payload}


# ===========================================================================
# Registro de todas las herramientas desde módulos especializados
# ===========================================================================
def _register_all_tools() -> None:
    """Registra todas las herramientas de los 8 módulos especializados."""
    from powerbi_mcp.tools import (
        register_ai_tools,
        register_analysis_tools,
        register_docs_tools,
        register_model_tools,
        register_pbi_api_tools,
        register_project_tools,
        register_security_tools,
        register_visuals_tools,
    )

    register_project_tools(mcp)
    register_model_tools(mcp)
    register_ai_tools(mcp)
    register_visuals_tools(mcp)
    register_analysis_tools(mcp)
    register_docs_tools(mcp)
    register_security_tools(mcp)
    register_pbi_api_tools(mcp)


# ===========================================================================
# Arranque del servidor
# ===========================================================================
def run(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Inicializa el logging y arranca el servidor MCP.

    Args:
        transport: Transporte de comunicación (actualmente solo ``"stdio"``).
    """
    settings = get_settings()
    settings.ensure_directories()
    setup_logging(settings)
    logger.info("Iniciando powerbi-mcp v%s (transport=%s)", __version__, transport)
    _register_all_tools()
    mcp.run(transport=transport)


__all__ = ["mcp", "run", "_tool", "_audit_action", "_reload_after_write", "_commit_model"]
