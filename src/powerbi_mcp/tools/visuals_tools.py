"""Herramientas para visuales y páginas del reporte.

7 herramientas:
- list_pages, create_page, create_visual, create_dashboard, export_html_visual
- list_color_palettes, create_theme
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.session import session


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
    if not dry_run:
        session.reload()


def register_visuals_tools(mcp) -> None:
    """Registra todas las herramientas de visuales en la instancia MCP."""

    @mcp.tool()
    @_tool
    def list_pages() -> dict[str, Any]:
        """Lista las páginas del reporte activo con su número de visuales.

        Returns:
            Lista de páginas.
        """
        from powerbi_mcp.pbip.parser import list_pages as _list

        return {"ok": True, "pages": _list(session.require())}

    @mcp.tool()
    @_tool
    def create_page(
        display_name: str,
        width: float = 1280.0,
        height: float = 720.0,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea una página nueva en el reporte PBIR del proyecto activo.

        Args:
            display_name: Nombre visible de la pestaña.
            width: Ancho del lienzo (px).
            height: Alto del lienzo (px).
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación de la página.
        """
        from powerbi_mcp.visuals.pages import create_page as _create

        project = session.require()
        result = _create(project, display_name, width=width, height=height, dry_run=dry_run)
        _audit_action(
            "create_page",
            target=display_name,
            details={"dry_run": dry_run, "page_id": result.get("page_id")},
        )
        _reload_after_write(dry_run)
        return {"ok": True, **result}

    @mcp.tool()
    @_tool
    def create_visual(
        page_id: str,
        visual_type: str,
        field_spec: dict[str, list[dict[str, str]]],
        position: dict[str, float] | None = None,
        title: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea un visual nativo PBIR y lo añade a una página.

        Args:
            page_id: Página donde insertar el visual.
            visual_type: Tipo de visual (columnChart, barChart, lineChart, pieChart,
                card, table, matrix, slicer, gauge, treemap, funnel...).
            field_spec: Mapeo de roles a campos. Cada campo es
                ``{"table": ..., "column": ..., "aggregation": opcional}``.
                Ej: ``{"Category": [{"table": "Fecha", "column": "Mes"}],
                "Y": [{"table": "Ventas", "column": "Importe", "aggregation": "Sum"}]}``.
            position: ``{x, y, width, height}`` (opcional).
            title: Título del visual (opcional).
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la inserción del visual.
        """
        from powerbi_mcp.visuals.builder import create_visual_in_report

        project = session.require()
        result = create_visual_in_report(
            project, page_id, visual_type, field_spec,
            position=position, title=title, dry_run=dry_run,
        )
        _audit_action(
            "create_visual",
            target=result.get("visual_id", page_id),
            details={"dry_run": dry_run, "page_id": page_id, "visual_type": visual_type},
        )
        _reload_after_write(dry_run)
        return {"ok": True, **result}

    @mcp.tool()
    @_tool
    def create_dashboard(
        display_name: str,
        visuals: list[dict[str, Any]],
        columns: int | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Crea una página completa con varios visuales en cuadrícula automática.

        Args:
            display_name: Nombre de la página.
            visuals: Lista de especificaciones, cada una con ``visual_type``,
                ``field_spec`` y opcionalmente ``title``.
            columns: Columnas de la cuadrícula (auto si es ``None``).
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado de la creación del dashboard.
        """
        from powerbi_mcp.visuals.builder import create_dashboard_page

        project = session.require()
        result = create_dashboard_page(project, display_name, visuals, columns=columns, dry_run=dry_run)
        _audit_action(
            "create_dashboard",
            target=display_name,
            details={"dry_run": dry_run, "visuals": len(visuals)},
        )
        _reload_after_write(dry_run)
        return {"ok": True, **result}

    @mcp.tool()
    @_tool
    def export_html_visual(
        data: Any,
        chart_type: str,
        output_path: str,
        x: str | None = None,
        y: Any = None,
        color: str | None = None,
        title: str = "",
        palette: list[str] | None = None,
    ) -> dict[str, Any]:
        """Exporta un visual interactivo independiente como archivo HTML.

        Args:
            data: Datos (ruta o registros).
            chart_type: bar, column, line, area, pie, donut, scatter, histogram,
                box, heatmap, treemap, funnel, waterfall, gauge, table, kpi_card.
            output_path: Ruta del archivo HTML de salida.
            x: Columna del eje X / categorías.
            y: Columna(s) del eje Y / valores.
            color: Columna de agrupación por color.
            title: Título del gráfico.
            palette: Lista de colores HEX (opcional).

        Returns:
            Ruta del HTML generado.
        """
        from powerbi_mcp.visuals.builder import export_visual_html

        result = export_visual_html(
            data, chart_type, output_path=output_path,
            x=x, y=y, color=color, title=title, palette=palette,
        )
        _audit_action(
            "export_html_visual",
            target=str(output_path),
            details={"chart_type": chart_type},
        )
        return {"ok": True, "chart_type": result["chart_type"], "path": result.get("path")}

    @mcp.tool()
    @_tool
    def list_color_palettes() -> dict[str, Any]:
        """Lista las paletas de colores predefinidas disponibles.

        Returns:
            Diccionario de paletas (nombre -> colores HEX).
        """
        from powerbi_mcp.visuals.themes import list_palettes

        return {"ok": True, "palettes": list_palettes()}

    @mcp.tool()
    @_tool
    def create_theme(
        name: str,
        palette: Any = "corporate_blue",
        background: str = "#FFFFFF",
        foreground: str = "#252423",
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Crea un tema de Power BI (JSON) y opcionalmente lo guarda en disco.

        Args:
            name: Nombre del tema.
            palette: Lista de colores HEX o nombre de paleta predefinida.
            background: Color de fondo.
            foreground: Color de texto.
            output_path: Ruta donde guardar el JSON del tema (opcional).

        Returns:
            La definición del tema y, si aplica, la ruta guardada.
        """
        import json
        from pathlib import Path

        from powerbi_mcp.visuals.themes import build_theme

        theme = build_theme(name, palette=palette, background=background, foreground=foreground)
        result: dict[str, Any] = {"ok": True, "theme": theme}
        if output_path:
            path = Path(output_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(theme, indent=2, ensure_ascii=False), encoding="utf-8")
            result["path"] = str(path)
            _audit_action("create_theme", target=str(path), details={"name": name})
        return result
