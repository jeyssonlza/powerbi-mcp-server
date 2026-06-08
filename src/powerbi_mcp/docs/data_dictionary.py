"""Generación del diccionario de datos del modelo semántico.

Produce un inventario estructurado de todos los objetos del modelo (tablas,
columnas, medidas, relaciones) con sus atributos clave, en forma de estructura
de datos reutilizable y exportable a Markdown, HTML o CSV.
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import SemanticModel

logger = get_logger(__name__)


def build_data_dictionary(model: SemanticModel) -> dict[str, Any]:
    """Construye el diccionario de datos del modelo como estructura de datos.

    Args:
        model: Modelo semántico.

    Returns:
        Diccionario con listas ``tables``, ``columns``, ``measures`` y
        ``relationships``, cada una con sus atributos documentados.
    """
    tables: list[dict[str, Any]] = []
    columns: list[dict[str, Any]] = []
    measures: list[dict[str, Any]] = []

    for table in model.tables:
        tables.append(
            {
                "table": table.name,
                "type": "calculated" if table.is_calculated_table else "data",
                "hidden": table.is_hidden,
                "columns": len(table.columns),
                "measures": len(table.measures),
                "description": table.description or "",
            }
        )
        for col in table.columns:
            columns.append(
                {
                    "table": table.name,
                    "column": col.name,
                    "data_type": col.data_type,
                    "kind": "calculated" if col.is_calculated else "data",
                    "format": col.format_string or "",
                    "hidden": col.is_hidden,
                    "summarize_by": col.summarize_by or "",
                    "data_category": col.data_category or "",
                    "expression": col.expression if col.is_calculated else "",
                }
            )
        for measure in table.measures:
            measures.append(
                {
                    "table": table.name,
                    "measure": measure.name,
                    "format": measure.format_string or "",
                    "display_folder": measure.display_folder or "",
                    "hidden": measure.is_hidden,
                    "description": measure.description or "",
                    "expression": measure.expression_text,
                }
            )

    relationships = [
        {
            "name": rel.name or "",
            "from_table": rel.from_table,
            "from_column": rel.from_column,
            "to_table": rel.to_table,
            "to_column": rel.to_column,
            "cardinality": f"{rel.from_cardinality or 'many'}:{rel.to_cardinality or 'one'}",
            "cross_filter": rel.cross_filtering_behavior,
            "active": rel.is_active,
        }
        for rel in model.relationships
    ]

    logger.info(
        "Diccionario de datos: %d tablas, %d columnas, %d medidas",
        len(tables),
        len(columns),
        len(measures),
    )
    return {
        "tables": tables,
        "columns": columns,
        "measures": measures,
        "relationships": relationships,
    }


def dictionary_to_markdown(dictionary: dict[str, Any]) -> str:
    """Convierte el diccionario de datos a tablas Markdown.

    Args:
        dictionary: Estructura devuelta por :func:`build_data_dictionary`.

    Returns:
        Documento Markdown con una sección por tipo de objeto.
    """
    parts: list[str] = ["# Diccionario de datos\n"]

    parts.append("## Tablas\n")
    parts.append(_md_table(
        ["Tabla", "Tipo", "Oculta", "Columnas", "Medidas", "Descripción"],
        [
            [t["table"], t["type"], _yn(t["hidden"]), str(t["columns"]), str(t["measures"]), t["description"]]
            for t in dictionary["tables"]
        ],
    ))

    parts.append("\n## Columnas\n")
    parts.append(_md_table(
        ["Tabla", "Columna", "Tipo dato", "Clase", "Formato", "Oculta"],
        [
            [c["table"], c["column"], c["data_type"], c["kind"], c["format"], _yn(c["hidden"])]
            for c in dictionary["columns"]
        ],
    ))

    parts.append("\n## Medidas\n")
    parts.append(_md_table(
        ["Tabla", "Medida", "Formato", "Carpeta", "Descripción"],
        [
            [m["table"], m["measure"], m["format"], m["display_folder"], m["description"]]
            for m in dictionary["measures"]
        ],
    ))

    parts.append("\n## Relaciones\n")
    parts.append(_md_table(
        ["Desde", "Hacia", "Cardinalidad", "Filtro cruzado", "Activa"],
        [
            [
                f"{r['from_table']}[{r['from_column']}]",
                f"{r['to_table']}[{r['to_column']}]",
                r["cardinality"],
                r["cross_filter"],
                _yn(r["active"]),
            ]
            for r in dictionary["relationships"]
        ],
    ))

    return "\n".join(parts)


def dictionary_to_csv(dictionary: dict[str, Any], section: str = "columns") -> str:
    """Exporta una sección del diccionario a CSV.

    Args:
        dictionary: Estructura devuelta por :func:`build_data_dictionary`.
        section: Sección a exportar (``tables``, ``columns``, ``measures``,
            ``relationships``).

    Returns:
        Cadena CSV con encabezado.
    """
    import csv
    import io

    rows = dictionary.get(section, [])
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    """Construye una tabla Markdown a partir de encabezados y filas."""
    if not rows:
        return "_(sin datos)_\n"
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(_escape_md(c) for c in row) + " |" for row in rows)
    return f"{head}\n{sep}\n{body}\n"


def _escape_md(value: str) -> str:
    """Escapa caracteres que rompen tablas Markdown."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _yn(value: bool) -> str:
    """Convierte un booleano a 'Sí'/'No'."""
    return "Sí" if value else "No"


__all__ = [
    "build_data_dictionary",
    "dictionary_to_csv",
    "dictionary_to_markdown",
]
