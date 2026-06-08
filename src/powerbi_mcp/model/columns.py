"""Gestión de columnas del modelo semántico.

Permite crear columnas de datos y columnas calculadas (DAX), cambiar el tipo de
dato, el formato y otras propiedades, y eliminarlas. Muta el modelo en memoria;
la persistencia la hace la capa de servidor con respaldo automático.
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.core.exceptions import (
    DaxValidationError,
    DuplicateObjectError,
    ObjectNotFoundError,
    ValidationError,
)
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.core.validators import validate_object_name
from powerbi_mcp.model.dax_validator import validate_dax
from powerbi_mcp.pbip.models import Column, SemanticModel

logger = get_logger(__name__)

#: Tipos de dato tabulares válidos en Power BI (TMSL).
VALID_DATA_TYPES: frozenset[str] = frozenset(
    {
        "string", "int64", "double", "decimal", "dateTime", "boolean",
        "binary", "variant", "automatic",
    }
)

#: Valores válidos para ``summarizeBy``.
VALID_SUMMARIZE_BY: frozenset[str] = frozenset(
    {"none", "sum", "min", "max", "count", "average", "distinctCount"}
)


def add_data_column(
    model: SemanticModel,
    table_name: str,
    column_name: str,
    data_type: str,
    *,
    source_column: str | None = None,
    format_string: str | None = None,
    summarize_by: str | None = None,
    is_hidden: bool = False,
) -> dict[str, Any]:
    """Añade una columna de datos (mapeada a una columna del origen).

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla destino.
        column_name: Nombre de la nueva columna.
        data_type: Tipo de dato (ver :data:`VALID_DATA_TYPES`).
        source_column: Columna del origen (por defecto, el mismo nombre).
        format_string: Cadena de formato.
        summarize_by: Agregación por defecto (ver :data:`VALID_SUMMARIZE_BY`).
        is_hidden: Si la columna se crea oculta.

    Returns:
        Diccionario confirmando la creación.

    Raises:
        ObjectNotFoundError: Si la tabla no existe.
        DuplicateObjectError: Si la columna ya existe.
        ValidationError: Si el tipo o la agregación no son válidos.
    """
    column_name = validate_object_name(column_name, kind="columna")
    _validate_data_type(data_type)
    if summarize_by is not None:
        _validate_summarize_by(summarize_by)

    table = _require_table(model, table_name)
    if table.get_column(column_name) is not None:
        raise DuplicateObjectError(
            "Ya existe una columna con ese nombre en la tabla.",
            details={"table": table_name, "column": column_name},
        )

    column = Column(
        name=column_name,
        dataType=data_type,
        sourceColumn=source_column or column_name,
        formatString=format_string,
        summarizeBy=summarize_by,
        isHidden=is_hidden,
    )
    table.columns.append(column)
    logger.info("Columna de datos añadida: %s[%s] (%s)", table_name, column_name, data_type)
    return {"created": True, "table": table_name, "column": column_name, "data_type": data_type}


def add_calculated_column(
    model: SemanticModel,
    table_name: str,
    column_name: str,
    expression: str,
    *,
    data_type: str = "automatic",
    format_string: str | None = None,
    is_hidden: bool = False,
    strict: bool = True,
) -> dict[str, Any]:
    """Añade una columna calculada (definida por una expresión DAX).

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla destino.
        column_name: Nombre de la nueva columna.
        expression: Expresión DAX que define la columna.
        data_type: Tipo de dato resultante (``automatic`` por defecto).
        format_string: Cadena de formato.
        is_hidden: Si la columna se crea oculta.
        strict: Si es ``True``, rechaza expresiones DAX inválidas.

    Returns:
        Diccionario con la creación y la validación DAX.

    Raises:
        ObjectNotFoundError: Si la tabla no existe.
        DuplicateObjectError: Si la columna ya existe.
        DaxValidationError: Si ``strict`` y la expresión es inválida.
    """
    column_name = validate_object_name(column_name, kind="columna")
    _validate_data_type(data_type)
    table = _require_table(model, table_name)
    if table.get_column(column_name) is not None:
        raise DuplicateObjectError(
            "Ya existe una columna con ese nombre en la tabla.",
            details={"table": table_name, "column": column_name},
        )

    validation = validate_dax(expression, model=model)
    if strict and not validation.is_valid:
        raise DaxValidationError(
            "La expresión DAX de la columna calculada no es válida.",
            details={"column": column_name, "errors": validation.errors},
        )

    column = Column(
        name=column_name,
        dataType=data_type,
        expression=expression,
        formatString=format_string,
        isHidden=is_hidden,
    )
    table.columns.append(column)
    logger.info("Columna calculada añadida: %s[%s]", table_name, column_name)
    return {
        "created": True,
        "table": table_name,
        "column": column_name,
        "validation": validation.to_dict(),
    }


def update_column(
    model: SemanticModel,
    table_name: str,
    column_name: str,
    *,
    data_type: str | None = None,
    format_string: str | None = None,
    summarize_by: str | None = None,
    is_hidden: bool | None = None,
    data_category: str | None = None,
    new_name: str | None = None,
) -> dict[str, Any]:
    """Modifica propiedades de una columna existente.

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla anfitriona.
        column_name: Nombre actual de la columna.
        data_type: Nuevo tipo de dato (si se indica).
        format_string: Nueva cadena de formato (si se indica).
        summarize_by: Nueva agregación por defecto (si se indica).
        is_hidden: Nueva visibilidad (si se indica).
        data_category: Categoría de datos (``WebUrl``, ``Address``...).
        new_name: Nuevo nombre (si se renombra).

    Returns:
        Diccionario con los cambios aplicados.

    Raises:
        ObjectNotFoundError: Si la tabla o la columna no existen.
        ValidationError: Si algún valor propuesto es inválido.
        DuplicateObjectError: Si ``new_name`` ya existe en la tabla.
    """
    table = _require_table(model, table_name)
    column = table.get_column(column_name)
    if column is None:
        raise ObjectNotFoundError(
            "La columna no existe.", details={"table": table_name, "column": column_name}
        )

    changes: dict[str, Any] = {}
    if data_type is not None:
        _validate_data_type(data_type)
        column.data_type = data_type
        changes["data_type"] = data_type
    if format_string is not None:
        column.format_string = format_string
        changes["format_string"] = format_string
    if summarize_by is not None:
        _validate_summarize_by(summarize_by)
        column.summarize_by = summarize_by
        changes["summarize_by"] = summarize_by
    if is_hidden is not None:
        column.is_hidden = is_hidden
        changes["is_hidden"] = is_hidden
    if data_category is not None:
        column.data_category = data_category
        changes["data_category"] = data_category
    if new_name is not None and new_name != column_name:
        new_name = validate_object_name(new_name, kind="columna")
        if table.get_column(new_name) is not None:
            raise DuplicateObjectError(
                "Ya existe una columna con el nuevo nombre.",
                details={"table": table_name, "column": new_name},
            )
        column.name = new_name
        changes["renamed_to"] = new_name

    logger.info("Columna actualizada: %s[%s] (%s)", table_name, column_name, ", ".join(changes))
    return {"updated": True, "table": table_name, "column": column.name, "changes": changes}


def delete_column(model: SemanticModel, table_name: str, column_name: str) -> dict[str, Any]:
    """Elimina una columna de una tabla.

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla anfitriona.
        column_name: Columna a eliminar.

    Returns:
        Diccionario confirmando la eliminación.

    Raises:
        ObjectNotFoundError: Si la tabla o la columna no existen.
    """
    table = _require_table(model, table_name)
    column = table.get_column(column_name)
    if column is None:
        raise ObjectNotFoundError(
            "La columna no existe.", details={"table": table_name, "column": column_name}
        )
    table.columns.remove(column)
    logger.info("Columna eliminada: %s[%s]", table_name, column_name)
    return {"deleted": True, "table": table_name, "column": column_name}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _require_table(model: SemanticModel, table_name: str) -> Any:
    """Devuelve la tabla o lanza :class:`ObjectNotFoundError`."""
    table = model.get_table(table_name)
    if table is None:
        raise ObjectNotFoundError("La tabla no existe.", details={"table": table_name})
    return table


def _validate_data_type(data_type: str) -> None:
    """Valida que el tipo de dato sea uno de los soportados."""
    if data_type not in VALID_DATA_TYPES:
        raise ValidationError(
            "Tipo de dato no válido.",
            details={"data_type": data_type, "valid": sorted(VALID_DATA_TYPES)},
        )


def _validate_summarize_by(summarize_by: str) -> None:
    """Valida el valor de ``summarizeBy``."""
    if summarize_by not in VALID_SUMMARIZE_BY:
        raise ValidationError(
            "Valor de summarizeBy no válido.",
            details={"summarize_by": summarize_by, "valid": sorted(VALID_SUMMARIZE_BY)},
        )


__all__ = [
    "VALID_DATA_TYPES",
    "VALID_SUMMARIZE_BY",
    "add_calculated_column",
    "add_data_column",
    "delete_column",
    "update_column",
]
