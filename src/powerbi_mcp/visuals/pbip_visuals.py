"""Generación de visuales en JSON nativo PBIP (esquema PBIR de Microsoft Fabric).

Construye archivos ``visual.json`` conformes al esquema PBIR usado por Power BI
Desktop al guardar un proyecto en formato PBIP/PBIR. Cada visual define:

- ``name`` (identificador único),
- ``position`` (x, y, z, ancho, alto),
- ``visual`` con ``visualType`` y el mapeo de campos a *data roles*
  (Category, Y, Values, Legend, Tooltips...).

Se cubren los tipos de visual más usados. Para tipos no mapeados explícitamente
se aplica un conjunto de roles genérico (``Category``/``Y``).
"""

from __future__ import annotations

import uuid
from typing import Any

from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

#: Esquema PBIR de un visual container.
_VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/1.0.0/schema.json"
)

#: Mapa de tipo de visual -> *data roles* esperados (en orden).
VISUAL_DATA_ROLES: dict[str, list[str]] = {
    "columnChart": ["Category", "Y", "Series"],
    "clusteredColumnChart": ["Category", "Y", "Series"],
    "barChart": ["Category", "Y", "Series"],
    "clusteredBarChart": ["Category", "Y", "Series"],
    "lineChart": ["Category", "Y", "Series"],
    "areaChart": ["Category", "Y", "Series"],
    "lineClusteredColumnComboChart": ["Category", "Y", "Y2"],
    "pieChart": ["Category", "Y"],
    "donutChart": ["Category", "Y"],
    "scatterChart": ["Category", "X", "Y", "Size"],
    "map": ["Category", "Y", "Size"],
    "filledMap": ["Category", "Y"],
    "treemap": ["Group", "Values"],
    "funnel": ["Category", "Y"],
    "waterfallChart": ["Category", "Y"],
    "gauge": ["Y", "MinValue", "MaxValue", "TargetValue"],
    "card": ["Values"],
    "multiRowCard": ["Values"],
    "kpi": ["Indicator", "TrendAxis", "Goal"],
    "table": ["Values"],
    "matrix": ["Rows", "Columns", "Values"],
    "slicer": ["Values"],
    "ribbonChart": ["Category", "Y", "Series"],
}

#: Tipos de visual soportados.
SUPPORTED_VISUAL_TYPES: frozenset[str] = frozenset(VISUAL_DATA_ROLES)


def make_field_ref(table: str, column: str, *, aggregation: str | None = None) -> dict[str, Any]:
    """Crea la referencia a un campo (columna o medida agregada) para un visual.

    Args:
        table: Tabla del campo.
        column: Columna o medida.
        aggregation: Agregación opcional (``Sum``, ``Average``, ``Count``,
            ``Min``, ``Max``). Si es ``None``, se referencia el campo directo
            (apropiado para medidas o columnas de eje).

    Returns:
        La estructura de proyección de campo en formato PBIR.
    """
    source_ref = {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}
    query_ref = f"{table}.{column}"

    if aggregation:
        agg_map = {"Sum": 0, "Avg": 1, "Average": 1, "Min": 3, "Max": 4, "Count": 2}
        function = agg_map.get(aggregation, 0)
        field = {
            "Aggregation": {
                "Expression": {"Column": source_ref},
                "Function": function,
            }
        }
        query_ref = f"{aggregation}({table}.{column})"
    else:
        field = {"Column": source_ref}

    return {"field": field, "queryRef": query_ref}


def build_visual_json(
    visual_type: str,
    *,
    fields: dict[str, list[dict[str, Any]]],
    x: float = 0.0,
    y: float = 0.0,
    width: float = 400.0,
    height: float = 300.0,
    z: float = 0.0,
    title: str | None = None,
    name: str | None = None,
    objects: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye el ``visual.json`` completo de un visual PBIR.

    Args:
        visual_type: Tipo de visual (ver :data:`SUPPORTED_VISUAL_TYPES`).
        fields: Mapeo *data role* -> lista de proyecciones de campo (usa
            :func:`make_field_ref`). Ej. ``{"Category": [...], "Y": [...]}``.
        x: Posición X en el lienzo (px).
        y: Posición Y en el lienzo (px).
        width: Ancho (px).
        height: Alto (px).
        z: Orden Z (apilamiento).
        title: Título visible del visual (opcional).
        name: Identificador único. Si es ``None`` se genera uno.
        objects: Objetos de formato adicionales (colores, ejes, etiquetas...).

    Returns:
        Diccionario con la definición completa del visual.

    Raises:
        ValidationError: Si el tipo no se reconoce o un *data role* no aplica.
    """
    if visual_type not in SUPPORTED_VISUAL_TYPES:
        logger.warning("Tipo de visual no mapeado explícitamente: %s", visual_type)

    visual_name = name or _new_visual_id()
    projections = _build_projections(visual_type, fields)

    visual_node: dict[str, Any] = {
        "visualType": visual_type,
        "query": {"queryState": projections},
        "drillFilterOtherVisuals": True,
    }

    format_objects = objects.copy() if objects else {}
    if title:
        format_objects.setdefault(
            "title",
            [{"properties": {"text": {"expr": {"Literal": {"Value": f"'{title}'"}}}}}],
        )
    if format_objects:
        visual_node["objects"] = format_objects

    return {
        "$schema": _VISUAL_SCHEMA,
        "name": visual_name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "width": width,
            "height": height,
            "tabOrder": int(z),
        },
        "visual": visual_node,
    }


def _build_projections(
    visual_type: str, fields: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Valida los *data roles* y construye el bloque ``queryState``."""
    valid_roles = VISUAL_DATA_ROLES.get(visual_type)
    query_state: dict[str, Any] = {}
    for role, projections in fields.items():
        if valid_roles is not None and role not in valid_roles:
            raise ValidationError(
                "Data role no válido para este visual.",
                details={"visual_type": visual_type, "role": role, "valid_roles": valid_roles},
            )
        query_state[role] = {"projections": projections}
    if not query_state:
        raise ValidationError("El visual debe tener al menos un campo asignado.")
    return query_state


def _new_visual_id() -> str:
    """Genera un identificador único para un visual."""
    return uuid.uuid4().hex[:20]


__all__ = [
    "SUPPORTED_VISUAL_TYPES",
    "VISUAL_DATA_ROLES",
    "build_visual_json",
    "make_field_ref",
]
