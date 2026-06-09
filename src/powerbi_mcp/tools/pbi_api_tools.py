"""Herramientas para integración con Power BI Service REST API.

5 herramientas:
- pbi_list_workspaces, pbi_list_datasets, pbi_list_reports
- pbi_execute_dax, pbi_refresh_dataset
"""

from __future__ import annotations

from typing import Any


def _tool(func: Any) -> Any:
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


def register_pbi_api_tools(mcp: Any) -> None:
    """Registra todas las herramientas de Power BI API en la instancia MCP."""

    @mcp.tool()
    @_tool
    def pbi_list_workspaces() -> dict[str, Any]:
        """Lista los workspaces de Power BI Service accesibles.

        Returns:
            Lista de workspaces.
        """
        from powerbi_mcp.powerbi_api.client import PowerBIClient

        workspaces = PowerBIClient().list_workspaces()
        _audit_action("pbi_list_workspaces", details={"count": len(workspaces)})
        return {"ok": True, "workspaces": workspaces}

    @mcp.tool()
    @_tool
    def pbi_list_datasets(workspace_id: str | None = None) -> dict[str, Any]:
        """Lista los datasets de un workspace (o del área personal).

        Args:
            workspace_id: ID del workspace (opcional).

        Returns:
            Lista de datasets.
        """
        from powerbi_mcp.powerbi_api.client import PowerBIClient

        datasets = PowerBIClient().list_datasets(workspace_id)
        _audit_action(
            "pbi_list_datasets",
            target=workspace_id or "my_workspace",
            details={"count": len(datasets)},
        )
        return {"ok": True, "datasets": datasets}

    @mcp.tool()
    @_tool
    def pbi_list_reports(workspace_id: str | None = None) -> dict[str, Any]:
        """Lista los reportes de un workspace (o del área personal).

        Args:
            workspace_id: ID del workspace (opcional).

        Returns:
            Lista de reportes.
        """
        from powerbi_mcp.powerbi_api.client import PowerBIClient

        reports = PowerBIClient().list_reports(workspace_id)
        _audit_action(
            "pbi_list_reports",
            target=workspace_id or "my_workspace",
            details={"count": len(reports)},
        )
        return {"ok": True, "reports": reports}

    @mcp.tool()
    @_tool
    def pbi_execute_dax(dataset_id: str, dax_query: str, workspace_id: str | None = None) -> dict[str, Any]:
        """Ejecuta una consulta DAX contra un dataset publicado en Power BI Service.

        Args:
            dataset_id: ID del dataset.
            dax_query: Consulta DAX (debe empezar por EVALUATE).
            workspace_id: ID del workspace (opcional).

        Returns:
            Filas resultantes de la consulta.
        """
        from powerbi_mcp.powerbi_api.client import PowerBIClient

        result = PowerBIClient().execute_dax(dataset_id, dax_query, workspace_id=workspace_id)
        _audit_action(
            "pbi_execute_dax",
            target=dataset_id,
            details={"workspace_id": workspace_id, "row_count": result.get("row_count")},
        )
        return {"ok": True, **result}

    @mcp.tool()
    @_tool
    def pbi_refresh_dataset(dataset_id: str, workspace_id: str | None = None) -> dict[str, Any]:
        """Dispara un refresco de un dataset en Power BI Service.

        Args:
            dataset_id: ID del dataset.
            workspace_id: ID del workspace (opcional).

        Returns:
            Confirmación de la solicitud de refresco.
        """
        from powerbi_mcp.powerbi_api.client import PowerBIClient

        result = PowerBIClient().refresh_dataset(dataset_id, workspace_id=workspace_id)
        _audit_action(
            "pbi_refresh_dataset",
            target=dataset_id,
            details={"workspace_id": workspace_id},
        )
        return {"ok": True, **result}
