"""Gestión de relaciones del modelo semántico.

Permite crear, modificar y eliminar relaciones, configurar cardinalidad y
dirección de filtro cruzado, y diagnosticar problemas habituales:

- Relaciones que apuntan a columnas/tablas inexistentes.
- Relaciones **ambiguas** o caminos múltiples entre tablas.
- Filtros **bidireccionales** (que suelen introducir ambigüedad/rendimiento).
- Clasificación del esquema (estrella vs. copo de nieve).
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.core.exceptions import (
    ObjectNotFoundError,
    RelationshipError,
)
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import Relationship, SemanticModel

logger = get_logger(__name__)

#: Cardinalidades válidas.
VALID_CARDINALITIES: frozenset[str] = frozenset({"one", "many"})

#: Comportamientos de filtro cruzado válidos.
VALID_CROSS_FILTER: frozenset[str] = frozenset({"oneDirection", "bothDirections", "automatic"})


def add_relationship(
    model: SemanticModel,
    from_table: str,
    from_column: str,
    to_table: str,
    to_column: str,
    *,
    from_cardinality: str = "many",
    to_cardinality: str = "one",
    cross_filter: str = "oneDirection",
    is_active: bool = True,
    name: str | None = None,
) -> dict[str, Any]:
    """Crea una relación entre dos columnas de tablas distintas.

    Args:
        model: Modelo semántico a modificar.
        from_table: Tabla origen (lado "muchos" por defecto).
        from_column: Columna origen.
        to_table: Tabla destino (lado "uno" por defecto).
        to_column: Columna destino.
        from_cardinality: Cardinalidad del origen (``many``/``one``).
        to_cardinality: Cardinalidad del destino (``one``/``many``).
        cross_filter: Dirección del filtro (ver :data:`VALID_CROSS_FILTER`).
        is_active: Si la relación se crea activa.
        name: Identificador opcional (se genera uno si se omite).

    Returns:
        Diccionario confirmando la creación y advertencias detectadas.

    Raises:
        ObjectNotFoundError: Si alguna columna referenciada no existe.
        RelationshipError: Si los parámetros son inválidos o crea ambigüedad.
    """
    _validate_cardinality(from_cardinality)
    _validate_cardinality(to_cardinality)
    _validate_cross_filter(cross_filter)
    _require_column(model, from_table, from_column)
    _require_column(model, to_table, to_column)

    if from_table == to_table:
        raise RelationshipError(
            "No se puede crear una relación de una tabla consigo misma por esta vía.",
            details={"table": from_table},
        )

    # Detecta duplicado exacto.
    for rel in model.relationships:
        if (
            rel.from_table == from_table
            and rel.from_column == from_column
            and rel.to_table == to_table
            and rel.to_column == to_column
        ):
            raise RelationshipError(
                "Ya existe una relación idéntica.",
                details={"from": f"{from_table}[{from_column}]", "to": f"{to_table}[{to_column}]"},
            )

    rel_name = name or f"{from_table}_{from_column}__{to_table}_{to_column}"
    relationship = Relationship(
        name=rel_name,
        from_table=from_table,
        from_column=from_column,
        to_table=to_table,
        to_column=to_column,
        from_cardinality=from_cardinality,
        to_cardinality=to_cardinality,
        cross_filtering_behavior=cross_filter,
        is_active=is_active,
    )

    warnings: list[str] = []
    # Si ya hay otra relación activa entre estas tablas, la nueva debe ser inactiva.
    active_between = [
        r
        for r in model.relationships
        if {r.from_table, r.to_table} == {from_table, to_table} and r.is_active
    ]
    if active_between and is_active:
        relationship.is_active = False
        warnings.append(
            "Ya existía una relación activa entre estas tablas; la nueva se creó "
            "como inactiva para evitar ambigüedad (usa USERELATIONSHIP en DAX)."
        )
    if cross_filter == "bothDirections":
        warnings.append(
            "Filtro bidireccional: puede causar ambigüedad y afectar el rendimiento. "
            "Úsalo solo si es estrictamente necesario."
        )

    model.relationships.append(relationship)
    logger.info("Relación creada: %s[%s] -> %s[%s]", from_table, from_column, to_table, to_column)
    return {
        "created": True,
        "name": rel_name,
        "is_active": relationship.is_active,
        "warnings": warnings,
    }


def update_relationship(
    model: SemanticModel,
    name: str,
    *,
    cross_filter: str | None = None,
    is_active: bool | None = None,
    from_cardinality: str | None = None,
    to_cardinality: str | None = None,
) -> dict[str, Any]:
    """Modifica propiedades de una relación existente.

    Args:
        model: Modelo semántico a modificar.
        name: Identificador de la relación.
        cross_filter: Nueva dirección de filtro (si se indica).
        is_active: Nuevo estado activo/inactivo (si se indica).
        from_cardinality: Nueva cardinalidad origen (si se indica).
        to_cardinality: Nueva cardinalidad destino (si se indica).

    Returns:
        Diccionario con los cambios aplicados.

    Raises:
        ObjectNotFoundError: Si la relación no existe.
        RelationshipError: Si algún valor es inválido.
    """
    rel = _require_relationship(model, name)
    changes: dict[str, Any] = {}

    if cross_filter is not None:
        _validate_cross_filter(cross_filter)
        rel.cross_filtering_behavior = cross_filter
        changes["cross_filter"] = cross_filter
    if is_active is not None:
        rel.is_active = is_active
        changes["is_active"] = is_active
    if from_cardinality is not None:
        _validate_cardinality(from_cardinality)
        rel.from_cardinality = from_cardinality
        changes["from_cardinality"] = from_cardinality
    if to_cardinality is not None:
        _validate_cardinality(to_cardinality)
        rel.to_cardinality = to_cardinality
        changes["to_cardinality"] = to_cardinality

    logger.info("Relación actualizada: %s (%s)", name, ", ".join(changes))
    return {"updated": True, "name": name, "changes": changes}


def delete_relationship(model: SemanticModel, name: str) -> dict[str, Any]:
    """Elimina una relación por su identificador.

    Args:
        model: Modelo semántico a modificar.
        name: Identificador de la relación.

    Returns:
        Diccionario confirmando la eliminación.

    Raises:
        ObjectNotFoundError: Si la relación no existe.
    """
    rel = _require_relationship(model, name)
    model.relationships.remove(rel)
    logger.info("Relación eliminada: %s", name)
    return {"deleted": True, "name": name}


def diagnose_relationships(model: SemanticModel) -> dict[str, Any]:
    """Diagnostica problemas en el grafo de relaciones del modelo.

    Detecta:
    - Relaciones con extremos inexistentes.
    - Múltiples relaciones activas entre el mismo par de tablas (ambigüedad).
    - Relaciones bidireccionales.
    - Tablas aisladas (sin ninguna relación).

    Args:
        model: Modelo semántico a analizar.

    Returns:
        Diccionario con listas de hallazgos por categoría.
    """
    broken: list[str] = []
    bidirectional: list[str] = []
    pair_active: dict[frozenset[str], int] = {}
    connected: set[str] = set()

    table_names = {t.name for t in model.tables}
    column_index = {
        f"{t.name}[{c.name}]" for t in model.tables for c in t.columns
    }

    for rel in model.relationships:
        from_ref = f"{rel.from_table}[{rel.from_column}]"
        to_ref = f"{rel.to_table}[{rel.to_column}]"
        if from_ref not in column_index or to_ref not in column_index:
            broken.append(f"{rel.name}: {from_ref} -> {to_ref}")
        if rel.is_bidirectional:
            bidirectional.append(rel.name or f"{from_ref} -> {to_ref}")
        if rel.is_active:
            key = frozenset({rel.from_table, rel.to_table})
            pair_active[key] = pair_active.get(key, 0) + 1
        connected.add(rel.from_table)
        connected.add(rel.to_table)

    ambiguous = [
        " <-> ".join(sorted(pair)) for pair, count in pair_active.items() if count > 1
    ]
    isolated = sorted(table_names - connected)

    return {
        "broken_relationships": broken,
        "ambiguous_pairs": ambiguous,
        "bidirectional": bidirectional,
        "isolated_tables": isolated,
        "total_relationships": len(model.relationships),
    }


def classify_schema(model: SemanticModel) -> dict[str, Any]:
    """Clasifica el esquema del modelo (estrella vs. copo de nieve).

    Heurística: una tabla es de **hechos** si es el lado "muchos" de varias
    relaciones; es de **dimensión** si es el lado "uno". Si una dimensión se
    relaciona con otra dimensión, hay indicios de **copo de nieve**.

    Args:
        model: Modelo semántico a analizar.

    Returns:
        Diccionario con ``schema_type``, tablas de hechos y dimensiones.
    """
    many_side: dict[str, int] = {}
    one_side: dict[str, int] = {}
    for rel in model.relationships:
        many_side[rel.from_table] = many_side.get(rel.from_table, 0) + 1
        one_side[rel.to_table] = one_side.get(rel.to_table, 0) + 1

    fact_tables = sorted(t for t in many_side if many_side[t] >= 2 and t not in one_side)
    dimension_tables = sorted(t for t in one_side if t not in fact_tables)

    # Copo de nieve: una dimensión es origen ("muchos") hacia otra dimensión.
    snowflake = any(
        rel.from_table in dimension_tables and rel.to_table in dimension_tables
        for rel in model.relationships
    )

    schema_type = "snowflake" if snowflake else "star" if fact_tables else "undetermined"
    return {
        "schema_type": schema_type,
        "fact_tables": fact_tables,
        "dimension_tables": dimension_tables,
    }


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _require_relationship(model: SemanticModel, name: str) -> Relationship:
    """Devuelve la relación por nombre o lanza :class:`ObjectNotFoundError`."""
    for rel in model.relationships:
        if rel.name == name:
            return rel
    raise ObjectNotFoundError("La relación no existe.", details={"name": name})


def _require_column(model: SemanticModel, table_name: str, column_name: str) -> None:
    """Verifica que exista ``Tabla[Columna]`` o lanza error."""
    table = model.get_table(table_name)
    if table is None:
        raise ObjectNotFoundError("La tabla no existe.", details={"table": table_name})
    if table.get_column(column_name) is None:
        raise ObjectNotFoundError(
            "La columna no existe.",
            details={"table": table_name, "column": column_name},
        )


def _validate_cardinality(value: str) -> None:
    """Valida una cardinalidad."""
    if value not in VALID_CARDINALITIES:
        raise RelationshipError(
            "Cardinalidad no válida.",
            details={"value": value, "valid": sorted(VALID_CARDINALITIES)},
        )


def _validate_cross_filter(value: str) -> None:
    """Valida un comportamiento de filtro cruzado."""
    if value not in VALID_CROSS_FILTER:
        raise RelationshipError(
            "Comportamiento de filtro cruzado no válido.",
            details={"value": value, "valid": sorted(VALID_CROSS_FILTER)},
        )


__all__ = [
    "VALID_CARDINALITIES",
    "VALID_CROSS_FILTER",
    "add_relationship",
    "classify_schema",
    "delete_relationship",
    "diagnose_relationships",
    "update_relationship",
]
