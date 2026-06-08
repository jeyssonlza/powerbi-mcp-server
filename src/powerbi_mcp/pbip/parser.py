"""Navegación y consulta de la estructura de un proyecto PBIP cargado.

Ofrece una API de **solo lectura** sobre :class:`~powerbi_mcp.pbip.models.PbipProject`
para responder preguntas frecuentes (estructura de carpetas, inventario de
objetos, búsqueda) sin modificar nada. Es la capa que alimenta muchas de las
herramientas MCP de exploración.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from powerbi_mcp.pbip.models import PbipProject


def build_file_tree(root: str | Path, *, max_depth: int = 6) -> dict[str, Any]:
    """Construye un árbol de archivos/carpetas del proyecto en disco.

    Args:
        root: Carpeta raíz a recorrer.
        max_depth: Profundidad máxima de recursión.

    Returns:
        Estructura anidada con ``name``, ``type`` (``dir``/``file``), ``size``
        (solo archivos) y ``children`` (solo directorios).
    """
    root_path = Path(root).expanduser().resolve()

    def _walk(path: Path, depth: int) -> dict[str, Any]:
        node: dict[str, Any] = {"name": path.name, "type": "dir", "children": []}
        if depth >= max_depth:
            node["truncated"] = True
            return node
        try:
            for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if child.is_dir():
                    node["children"].append(_walk(child, depth + 1))
                else:
                    node["children"].append(
                        {
                            "name": child.name,
                            "type": "file",
                            "size": child.stat().st_size,
                        }
                    )
        except OSError:
            node["error"] = "no accesible"
        return node

    return _walk(root_path, 0)


def list_tables(project: PbipProject) -> list[dict[str, Any]]:
    """Lista las tablas del modelo con conteos resumidos.

    Args:
        project: Proyecto cargado.

    Returns:
        Lista de diccionarios con ``name``, ``columns``, ``measures``,
        ``is_hidden`` y ``is_calculated``.
    """
    if project.semantic_model is None:
        return []
    return [
        {
            "name": t.name,
            "columns": len(t.columns),
            "measures": len(t.measures),
            "is_hidden": t.is_hidden,
            "is_calculated": t.is_calculated_table,
            "description": t.description,
        }
        for t in project.semantic_model.tables
    ]


def describe_table(project: PbipProject, table_name: str) -> dict[str, Any] | None:
    """Devuelve el detalle completo de una tabla (columnas y medidas).

    Args:
        project: Proyecto cargado.
        table_name: Nombre de la tabla a describir.

    Returns:
        Diccionario con la descripción de la tabla, o ``None`` si no existe.
    """
    if project.semantic_model is None:
        return None
    table = project.semantic_model.get_table(table_name)
    if table is None:
        return None
    return {
        "name": table.name,
        "is_hidden": table.is_hidden,
        "is_calculated": table.is_calculated_table,
        "description": table.description,
        "columns": [
            {
                "name": c.name,
                "data_type": c.data_type,
                "is_calculated": c.is_calculated,
                "is_hidden": c.is_hidden,
                "format_string": c.format_string,
            }
            for c in table.columns
        ],
        "measures": [
            {
                "name": m.name,
                "expression": m.expression_text,
                "format_string": m.format_string,
                "display_folder": m.display_folder,
            }
            for m in table.measures
        ],
    }


def list_measures(project: PbipProject) -> list[dict[str, Any]]:
    """Lista todas las medidas del modelo con su tabla anfitriona.

    Args:
        project: Proyecto cargado.

    Returns:
        Lista de diccionarios ``{table, name, expression, format_string}``.
    """
    if project.semantic_model is None:
        return []
    return [
        {
            "table": table_name,
            "name": m.name,
            "expression": m.expression_text,
            "format_string": m.format_string,
            "display_folder": m.display_folder,
        }
        for table_name, m in project.semantic_model.all_measures()
    ]


def list_relationships(project: PbipProject) -> list[dict[str, Any]]:
    """Lista las relaciones del modelo.

    Args:
        project: Proyecto cargado.

    Returns:
        Lista de diccionarios describiendo cada relación.
    """
    if project.semantic_model is None:
        return []
    return [
        {
            "name": r.name,
            "from": f"{r.from_table}[{r.from_column}]",
            "to": f"{r.to_table}[{r.to_column}]",
            "cross_filter": r.cross_filtering_behavior,
            "is_active": r.is_active,
            "is_bidirectional": r.is_bidirectional,
        }
        for r in project.semantic_model.relationships
    ]


def list_pages(project: PbipProject) -> list[dict[str, Any]]:
    """Lista las páginas del reporte con su número de visuales.

    Args:
        project: Proyecto cargado.

    Returns:
        Lista de diccionarios ``{name, display_name, visuals}``.
    """
    if project.report is None:
        return []
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "visuals": len(p.visuals),
            "width": p.width,
            "height": p.height,
        }
        for p in project.report.pages
    ]


def search_objects(project: PbipProject, term: str) -> dict[str, list[str]]:
    """Busca un término (case-insensitive) en nombres de objetos del modelo.

    Args:
        project: Proyecto cargado.
        term: Texto a buscar.

    Returns:
        Diccionario con coincidencias por categoría: ``tables``, ``columns``,
        ``measures``, ``pages``.
    """
    term_low = term.lower()
    result: dict[str, list[str]] = {"tables": [], "columns": [], "measures": [], "pages": []}

    if project.semantic_model is not None:
        for table in project.semantic_model.tables:
            if term_low in table.name.lower():
                result["tables"].append(table.name)
            for col in table.columns:
                if term_low in col.name.lower():
                    result["columns"].append(f"{table.name}[{col.name}]")
            for meas in table.measures:
                if term_low in meas.name.lower():
                    result["measures"].append(f"{table.name}[{meas.name}]")

    if project.report is not None:
        for page in project.report.pages:
            label = page.display_name or page.name or ""
            if term_low in label.lower():
                result["pages"].append(label)

    return result


__all__ = [
    "build_file_tree",
    "describe_table",
    "list_measures",
    "list_pages",
    "list_relationships",
    "list_tables",
    "search_objects",
]
