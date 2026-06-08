"""Gestión de tablas del modelo semántico.

Permite crear tablas (de datos vía Power Query M o calculadas vía DAX),
renombrarlas, ocultarlas y eliminarlas. Muta el modelo en memoria; la
persistencia la realiza la capa de servidor con respaldo automático.
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.core.exceptions import (
    DaxValidationError,
    DuplicateObjectError,
    ObjectNotFoundError,
)
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.core.validators import validate_object_name
from powerbi_mcp.model.dax_validator import validate_dax
from powerbi_mcp.pbip.models import Column, Partition, SemanticModel, Table

logger = get_logger(__name__)


def add_table(
    model: SemanticModel,
    table_name: str,
    *,
    m_expression: str | None = None,
    columns: list[dict[str, Any]] | None = None,
    is_hidden: bool = False,
    description: str | None = None,
) -> dict[str, Any]:
    """Crea una tabla nueva, opcionalmente con origen Power Query (M).

    Args:
        model: Modelo semántico a modificar.
        table_name: Nombre de la nueva tabla.
        m_expression: Expresión M (Power Query) que define el origen. Si es
            ``None`` se crea una partición vacía que deberás completar.
        columns: Lista opcional de definiciones de columnas, cada una con al
            menos ``name`` y ``data_type``.
        is_hidden: Si la tabla se crea oculta.
        description: Descripción de la tabla.

    Returns:
        Diccionario confirmando la creación.

    Raises:
        DuplicateObjectError: Si ya existe una tabla con ese nombre.
    """
    table_name = validate_object_name(table_name, kind="tabla")
    if model.get_table(table_name) is not None:
        raise DuplicateObjectError(
            "Ya existe una tabla con ese nombre.", details={"table": table_name}
        )

    table = Table(name=table_name, isHidden=is_hidden, description=description)

    if columns:
        for col_def in columns:
            table.columns.append(
                Column(
                    name=col_def["name"],
                    dataType=col_def.get("data_type", "string"),
                    sourceColumn=col_def.get("source_column", col_def["name"]),
                    formatString=col_def.get("format_string"),
                )
            )

    if m_expression is not None:
        table.partitions.append(
            Partition(
                name=table_name,
                mode="import",
                source={"type": "m", "expression": m_expression},
            )
        )

    model.tables.append(table)
    logger.info("Tabla creada: %s (%d columnas)", table_name, len(table.columns))
    return {"created": True, "table": table_name, "columns": len(table.columns)}


def add_calculated_table(
    model: SemanticModel,
    table_name: str,
    dax_expression: str,
    *,
    is_hidden: bool = False,
    description: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Crea una tabla calculada definida por una expresión DAX.

    Args:
        model: Modelo semántico a modificar.
        table_name: Nombre de la nueva tabla.
        dax_expression: Expresión DAX que produce la tabla (ej. ``CALENDARAUTO()``).
        is_hidden: Si la tabla se crea oculta.
        description: Descripción de la tabla.
        strict: Si es ``True``, rechaza expresiones DAX inválidas.

    Returns:
        Diccionario con la creación y la validación DAX.

    Raises:
        DuplicateObjectError: Si ya existe una tabla con ese nombre.
        DaxValidationError: Si ``strict`` y la expresión es inválida.
    """
    table_name = validate_object_name(table_name, kind="tabla")
    if model.get_table(table_name) is not None:
        raise DuplicateObjectError(
            "Ya existe una tabla con ese nombre.", details={"table": table_name}
        )

    validation = validate_dax(dax_expression, model=model)
    if strict and not validation.is_valid:
        raise DaxValidationError(
            "La expresión DAX de la tabla calculada no es válida.",
            details={"table": table_name, "errors": validation.errors},
        )

    table = Table(name=table_name, isHidden=is_hidden, description=description)
    table.partitions.append(
        Partition(
            name=table_name,
            mode="import",
            source={"type": "calculated", "expression": dax_expression},
        )
    )
    model.tables.append(table)
    logger.info("Tabla calculada creada: %s", table_name)
    return {"created": True, "table": table_name, "validation": validation.to_dict()}


def rename_table(model: SemanticModel, table_name: str, new_name: str) -> dict[str, Any]:
    """Renombra una tabla y actualiza las relaciones que la referencian.

    Args:
        model: Modelo semántico a modificar.
        table_name: Nombre actual.
        new_name: Nuevo nombre.

    Returns:
        Diccionario con el resultado y cuántas relaciones se actualizaron.

    Raises:
        ObjectNotFoundError: Si la tabla no existe.
        DuplicateObjectError: Si el nuevo nombre ya está en uso.
    """
    new_name = validate_object_name(new_name, kind="tabla")
    table = model.get_table(table_name)
    if table is None:
        raise ObjectNotFoundError("La tabla no existe.", details={"table": table_name})
    if model.get_table(new_name) is not None:
        raise DuplicateObjectError(
            "Ya existe una tabla con el nuevo nombre.", details={"table": new_name}
        )

    table.name = new_name
    updated = 0
    for rel in model.relationships:
        if rel.from_table == table_name:
            rel.from_table = new_name
            updated += 1
        if rel.to_table == table_name:
            rel.to_table = new_name
            updated += 1

    logger.info("Tabla renombrada: %s -> %s (%d relaciones actualizadas)", table_name, new_name, updated)
    return {"renamed": True, "from": table_name, "to": new_name, "relationships_updated": updated}


def delete_table(
    model: SemanticModel, table_name: str, *, cascade_relationships: bool = True
) -> dict[str, Any]:
    """Elimina una tabla y, opcionalmente, sus relaciones asociadas.

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla a eliminar.
        cascade_relationships: Si es ``True``, elimina también las relaciones que
            usen la tabla. Si es ``False`` y existen relaciones, no elimina.

    Returns:
        Diccionario con el resultado y las relaciones eliminadas.

    Raises:
        ObjectNotFoundError: Si la tabla no existe.
    """
    table = model.get_table(table_name)
    if table is None:
        raise ObjectNotFoundError("La tabla no existe.", details={"table": table_name})

    related = [r for r in model.relationships if table_name in {r.from_table, r.to_table}]
    if related and not cascade_relationships:
        return {
            "deleted": False,
            "reason": "La tabla tiene relaciones; usa cascade_relationships=True.",
            "relationships": len(related),
        }

    model.tables.remove(table)
    for rel in related:
        model.relationships.remove(rel)

    logger.info("Tabla eliminada: %s (%d relaciones)", table_name, len(related))
    return {"deleted": True, "table": table_name, "relationships_deleted": len(related)}


def set_table_hidden(model: SemanticModel, table_name: str, hidden: bool) -> dict[str, Any]:
    """Oculta o muestra una tabla.

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla a modificar.
        hidden: ``True`` para ocultar, ``False`` para mostrar.

    Returns:
        Diccionario confirmando el cambio.

    Raises:
        ObjectNotFoundError: Si la tabla no existe.
    """
    table = model.get_table(table_name)
    if table is None:
        raise ObjectNotFoundError("La tabla no existe.", details={"table": table_name})
    table.is_hidden = hidden
    return {"table": table_name, "is_hidden": hidden}


__all__ = [
    "add_calculated_table",
    "add_table",
    "delete_table",
    "rename_table",
    "set_table_hidden",
]
