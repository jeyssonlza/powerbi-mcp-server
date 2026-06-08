"""Integración de resultados de IA al modelo semántico Power BI.

Convierte un :class:`~powerbi_mcp.ai._base.AIResult` en una tabla del modelo,
en cualquiera de los dos formatos soportados por Power BI:

- **DAX** (``DATATABLE``): tabla calculada con los datos embebidos. Ideal para
  resultados pequeños/medianos que deben vivir dentro del modelo sin origen.
- **Power Query (M)** (``#table``): consulta que materializa los datos. Mejor
  para conjuntos algo mayores y refrescables.

Además genera la expresión y, opcionalmente, la añade al modelo cargado usando
:mod:`powerbi_mcp.model.tables`.
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.ai._base import AIResult
from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.model.tables import add_calculated_table, add_table
from powerbi_mcp.pbip.models import SemanticModel

logger = get_logger(__name__)

#: Mapeo de tipos Python -> tipo DAX para DATATABLE.
_DAX_TYPE_MAP = {
    int: "INTEGER",
    float: "DOUBLE",
    bool: "BOOLEAN",
    str: "STRING",
}


def _infer_column_types(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, type]:
    """Infiere el tipo predominante de cada columna a partir de los datos."""
    types: dict[str, type] = {}
    for col in columns:
        col_type: type = str
        for row in rows:
            value = row.get(col)
            if value is None:
                continue
            if isinstance(value, bool):
                col_type = bool
            elif isinstance(value, int):
                col_type = int
            elif isinstance(value, float):
                col_type = float
            else:
                col_type = str
                break
        types[col] = col_type
    return types


def result_to_dax_datatable(result: AIResult, *, max_rows: int = 2000) -> str:
    """Genera una expresión DAX ``DATATABLE`` a partir de un resultado de IA.

    Args:
        result: Resultado de IA a materializar.
        max_rows: Límite de filas (DATATABLE no es apto para volúmenes grandes).

    Returns:
        La expresión DAX como cadena.

    Raises:
        ValidationError: Si el resultado no tiene filas o excede ``max_rows``.
    """
    if not result.table:
        raise ValidationError("El resultado de IA no contiene filas.")
    if len(result.table) > max_rows:
        raise ValidationError(
            "Demasiadas filas para DATATABLE; usa el formato M (Power Query).",
            details={"rows": len(result.table), "max_rows": max_rows},
        )

    columns = result.columns or list(result.table[0].keys())
    types = _infer_column_types(result.table, columns)

    col_defs = ",\n    ".join(f'"{col}", {_DAX_TYPE_MAP[types[col]]}' for col in columns)

    data_rows = []
    for row in result.table:
        cells = [_dax_literal(row.get(col), types[col]) for col in columns]
        data_rows.append("        {" + ", ".join(cells) + "}")
    data_block = ",\n".join(data_rows)

    return f"DATATABLE(\n    {col_defs},\n    {{\n{data_block}\n    }}\n)"


def _dax_literal(value: Any, dtype: type) -> str:
    """Formatea un valor como literal DAX según su tipo."""
    if value is None:
        return '""' if dtype is str else "0"
    if dtype is bool:
        return "TRUE" if value else "FALSE"
    if dtype is str:
        escaped = str(value).replace('"', '""')
        return f'"{escaped}"'
    return str(value)


def result_to_m_query(result: AIResult) -> str:
    """Genera una consulta Power Query (M) que materializa el resultado de IA.

    Args:
        result: Resultado de IA a materializar.

    Returns:
        La expresión M como cadena (usando ``#table``).

    Raises:
        ValidationError: Si el resultado no tiene filas.
    """
    if not result.table:
        raise ValidationError("El resultado de IA no contiene filas.")

    columns = result.columns or list(result.table[0].keys())
    types = _infer_column_types(result.table, columns)

    m_type_map = {int: "Int64.Type", float: "type number", bool: "type logical", str: "type text"}
    col_specs = ", ".join(f'{{"{col}", {m_type_map[types[col]]}}}' for col in columns)

    row_literals = []
    for row in result.table:
        cells = [_m_literal(row.get(col), types[col]) for col in columns]
        row_literals.append("{" + ", ".join(cells) + "}")
    rows_block = ",\n        ".join(row_literals)

    return (
        "let\n"
        f"    Source = #table(\n"
        f"        type table [{col_specs}],\n"
        f"        {{\n        {rows_block}\n        }}\n"
        f"    )\n"
        "in\n"
        "    Source"
    )


def _m_literal(value: Any, dtype: type) -> str:
    """Formatea un valor como literal M según su tipo."""
    if value is None:
        return "null"
    if dtype is bool:
        return "true" if value else "false"
    if dtype is str:
        escaped = str(value).replace('"', '""')
        return f'"{escaped}"'
    return str(value)


def integrate_ai_result(
    model: SemanticModel,
    result: AIResult,
    table_name: str,
    *,
    format: str = "dax",
) -> dict[str, Any]:
    """Integra un resultado de IA al modelo como una tabla nueva.

    Args:
        model: Modelo semántico donde añadir la tabla.
        result: Resultado de IA a integrar.
        table_name: Nombre de la tabla a crear.
        format: ``"dax"`` (tabla calculada ``DATATABLE``) o ``"m"`` (Power Query).

    Returns:
        Diccionario con el resultado de la creación y la expresión generada.

    Raises:
        ValidationError: Si el formato no es válido o el resultado está vacío.
    """
    if format not in {"dax", "m"}:
        raise ValidationError("Formato no válido (usa 'dax' o 'm').", details={"format": format})

    if format == "dax":
        expression = result_to_dax_datatable(result)
        outcome = add_calculated_table(
            model,
            table_name,
            expression,
            description=f"Generada por IA: {result.model_type}",
        )
    else:
        expression = result_to_m_query(result)
        outcome = add_table(
            model,
            table_name,
            m_expression=expression,
            description=f"Generada por IA: {result.model_type}",
        )

    logger.info("Resultado de IA '%s' integrado como tabla '%s' (%s)", result.model_type, table_name, format)
    return {
        "integrated": True,
        "table": table_name,
        "format": format,
        "model_type": result.model_type,
        "rows": len(result.table),
        "expression": expression,
        "creation": outcome,
    }


__all__ = [
    "integrate_ai_result",
    "result_to_dax_datatable",
    "result_to_m_query",
]
