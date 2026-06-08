"""API unificada de construcción de visuales y reportes.

Capa de orquestación de alto nivel sobre los módulos especializados:

- :mod:`~powerbi_mcp.visuals.pbip_visuals` (visuales JSON nativos PBIR),
- :mod:`~powerbi_mcp.visuals.html_visuals` (visuales HTML interactivos),
- :mod:`~powerbi_mcp.visuals.pages` (páginas y layout).

Expone operaciones que el servidor MCP traduce a herramientas, escondiendo los
detalles de formato detrás de una interfaz coherente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import PbipProject
from powerbi_mcp.visuals.html_visuals import create_html_visual
from powerbi_mcp.visuals.pages import add_visual_to_page, auto_grid_layout, create_page
from powerbi_mcp.visuals.pbip_visuals import build_visual_json, make_field_ref

logger = get_logger(__name__)


def create_visual_in_report(
    project: PbipProject,
    page_id: str,
    visual_type: str,
    field_spec: dict[str, list[dict[str, str]]],
    *,
    position: dict[str, float] | None = None,
    title: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Crea un visual nativo PBIR y lo añade a una página del reporte.

    El ``field_spec`` mapea cada *data role* a una lista de campos descritos como
    diccionarios ``{"table": ..., "column": ..., "aggregation": opcional}``.

    Args:
        project: Proyecto destino.
        page_id: Página donde insertar el visual.
        visual_type: Tipo de visual PBIR (ej. ``"columnChart"``).
        field_spec: Mapeo de roles a campos. Ej::

            {
              "Category": [{"table": "Fecha", "column": "Mes"}],
              "Y": [{"table": "Ventas", "column": "Importe", "aggregation": "Sum"}]
            }

        position: ``{x, y, width, height}``. Si es ``None``, usa un tamaño por defecto.
        title: Título del visual.
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.

    Returns:
        Diccionario con el resultado de la inserción del visual.

    Raises:
        ValidationError: Si el ``field_spec`` está vacío o mal formado.
    """
    if not field_spec:
        raise ValidationError("Debes especificar al menos un campo (field_spec vacío).")

    fields: dict[str, list[dict[str, Any]]] = {}
    for role, items in field_spec.items():
        fields[role] = [
            make_field_ref(item["table"], item["column"], aggregation=item.get("aggregation"))
            for item in items
        ]

    pos = position or {"x": 0.0, "y": 60.0, "width": 600.0, "height": 400.0}
    visual_json = build_visual_json(
        visual_type,
        fields=fields,
        x=pos.get("x", 0.0),
        y=pos.get("y", 0.0),
        width=pos.get("width", 600.0),
        height=pos.get("height", 400.0),
        title=title,
    )
    return add_visual_to_page(project, page_id, visual_json, dry_run=dry_run)


def create_dashboard_page(
    project: PbipProject,
    display_name: str,
    visuals: list[dict[str, Any]],
    *,
    columns: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Crea una página completa con varios visuales distribuidos en cuadrícula.

    Args:
        project: Proyecto destino.
        display_name: Nombre de la página.
        visuals: Lista de especificaciones de visual, cada una con
            ``visual_type``, ``field_spec`` y opcionalmente ``title``.
        columns: Columnas de la cuadrícula (auto si es ``None``).
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.

    Returns:
        Diccionario con la página creada y los visuales añadidos.

    Raises:
        ValidationError: Si la lista de visuales está vacía.
    """
    if not visuals:
        raise ValidationError("Debes especificar al menos un visual.")

    page_result = create_page(project, display_name, dry_run=dry_run)
    page_id = page_result["page_id"]

    positions = auto_grid_layout(len(visuals), columns=columns)
    added: list[dict[str, Any]] = []
    for spec, pos in zip(visuals, positions, strict=False):
        added.append(
            create_visual_in_report(
                project,
                page_id,
                spec["visual_type"],
                spec["field_spec"],
                position=pos,
                title=spec.get("title"),
                dry_run=dry_run,
            )
        )

    logger.info("Dashboard '%s' creado con %d visuales", display_name, len(added))
    return {
        "created": True,
        "page": page_result,
        "visuals_added": len(added),
        "visuals": added,
    }


def export_visual_html(
    data: Any,
    chart_type: str,
    *,
    output_path: str | Path,
    x: str | None = None,
    y: str | list[str] | None = None,
    color: str | None = None,
    title: str = "",
    palette: list[str] | None = None,
) -> dict[str, Any]:
    """Exporta un visual como archivo HTML interactivo independiente.

    Atajo directo sobre :func:`~powerbi_mcp.visuals.html_visuals.create_html_visual`.

    Args:
        data: Datos a graficar.
        chart_type: Tipo de gráfico HTML.
        output_path: Ruta del archivo HTML de salida.
        x: Columna del eje X / categorías.
        y: Columna(s) del eje Y / valores.
        color: Columna de agrupación por color.
        title: Título del gráfico.
        palette: Paleta de colores opcional.

    Returns:
        Diccionario con la ruta del HTML generado.
    """
    return create_html_visual(
        data,
        chart_type,
        x=x,
        y=y,
        color=color,
        title=title,
        palette=palette,
        output_path=output_path,
        include_plotlyjs=True,
    )


__all__ = [
    "create_dashboard_page",
    "create_visual_in_report",
    "export_visual_html",
]
