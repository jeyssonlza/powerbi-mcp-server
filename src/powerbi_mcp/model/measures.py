"""Gestión de medidas DAX del modelo semántico.

Las funciones mutan un :class:`~powerbi_mcp.pbip.models.SemanticModel` en
memoria y devuelven la entidad afectada. La **persistencia** en disco (con
respaldo automático) la realiza la capa de servidor llamando a
:func:`~powerbi_mcp.pbip.writer.save_semantic_model`.

Toda creación/modificación valida la expresión DAX con
:func:`~powerbi_mcp.model.dax_validator.validate_dax` y puede operar en modo
estricto (rechazar si hay errores) o permisivo (avisar pero aplicar).
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
from powerbi_mcp.pbip.models import Measure, SemanticModel

logger = get_logger(__name__)


def add_measure(
    model: SemanticModel,
    table_name: str,
    measure_name: str,
    expression: str,
    *,
    format_string: str | None = None,
    display_folder: str | None = None,
    description: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Crea una nueva medida DAX en la tabla indicada.

    Args:
        model: Modelo semántico a modificar.
        table_name: Tabla anfitriona de la medida.
        measure_name: Nombre de la nueva medida (único en todo el modelo).
        expression: Expresión DAX.
        format_string: Cadena de formato (ej. ``"#,0"``, ``"0.0%"``).
        display_folder: Carpeta de visualización para organizar la medida.
        description: Documentación de la medida.
        strict: Si es ``True``, lanza error cuando la DAX no es válida.

    Returns:
        Diccionario con la medida creada y el resultado de validación DAX.

    Raises:
        ObjectNotFoundError: Si la tabla no existe.
        DuplicateObjectError: Si ya existe una medida con ese nombre.
        DaxValidationError: Si ``strict`` y la expresión DAX es inválida.
    """
    measure_name = validate_object_name(measure_name, kind="medida")
    table = model.get_table(table_name)
    if table is None:
        raise ObjectNotFoundError(
            "La tabla destino no existe.", details={"table": table_name}
        )

    if model.find_measure(measure_name) is not None:
        raise DuplicateObjectError(
            "Ya existe una medida con ese nombre en el modelo.",
            details={"measure": measure_name},
        )

    validation = validate_dax(expression, model=model)
    if strict and not validation.is_valid:
        raise DaxValidationError(
            "La expresión DAX no es válida.",
            details={"measure": measure_name, "errors": validation.errors},
        )

    measure = Measure(
        name=measure_name,
        expression=expression,
        formatString=format_string,
        displayFolder=display_folder,
        description=description,
    )
    table.measures.append(measure)
    logger.info("Medida añadida: %s[%s]", table_name, measure_name)

    return {
        "created": True,
        "table": table_name,
        "measure": measure_name,
        "validation": validation.to_dict(),
    }


def update_measure(
    model: SemanticModel,
    measure_name: str,
    *,
    expression: str | None = None,
    format_string: str | None = None,
    display_folder: str | None = None,
    description: str | None = None,
    new_name: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Modifica una medida existente (cualquier subconjunto de propiedades).

    Args:
        model: Modelo semántico a modificar.
        measure_name: Nombre actual de la medida.
        expression: Nueva expresión DAX (si se indica).
        format_string: Nueva cadena de formato (si se indica).
        display_folder: Nueva carpeta de visualización (si se indica).
        description: Nueva descripción (si se indica).
        new_name: Nuevo nombre de la medida (si se renombra).
        strict: Si es ``True``, valida la nueva DAX y rechaza si es inválida.

    Returns:
        Diccionario con los cambios aplicados y, si procede, la validación DAX.

    Raises:
        ObjectNotFoundError: Si la medida no existe.
        DuplicateObjectError: Si ``new_name`` ya está en uso.
        DaxValidationError: Si ``strict`` y la nueva expresión es inválida.
    """
    found = model.find_measure(measure_name)
    if found is None:
        raise ObjectNotFoundError(
            "La medida no existe.", details={"measure": measure_name}
        )
    _, measure = found
    changes: dict[str, Any] = {}

    if expression is not None:
        validation = validate_dax(expression, model=model)
        if strict and not validation.is_valid:
            raise DaxValidationError(
                "La nueva expresión DAX no es válida.",
                details={"measure": measure_name, "errors": validation.errors},
            )
        measure.expression = expression
        changes["expression"] = validation.to_dict()

    if format_string is not None:
        measure.format_string = format_string
        changes["format_string"] = format_string
    if display_folder is not None:
        measure.display_folder = display_folder
        changes["display_folder"] = display_folder
    if description is not None:
        measure.description = description
        changes["description"] = description

    if new_name is not None and new_name != measure_name:
        new_name = validate_object_name(new_name, kind="medida")
        if model.find_measure(new_name) is not None:
            raise DuplicateObjectError(
                "Ya existe una medida con el nuevo nombre.",
                details={"measure": new_name},
            )
        measure.name = new_name
        changes["renamed_to"] = new_name

    logger.info("Medida actualizada: %s (%s)", measure_name, ", ".join(changes) or "sin cambios")
    return {"updated": True, "measure": measure.name, "changes": changes}


def delete_measure(model: SemanticModel, measure_name: str) -> dict[str, Any]:
    """Elimina una medida del modelo.

    Args:
        model: Modelo semántico a modificar.
        measure_name: Nombre de la medida a eliminar.

    Returns:
        Diccionario confirmando la eliminación.

    Raises:
        ObjectNotFoundError: Si la medida no existe.
    """
    for table in model.tables:
        measure = table.get_measure(measure_name)
        if measure is not None:
            table.measures.remove(measure)
            logger.info("Medida eliminada: %s[%s]", table.name, measure_name)
            return {"deleted": True, "table": table.name, "measure": measure_name}
    raise ObjectNotFoundError("La medida no existe.", details={"measure": measure_name})


def find_orphan_measures(model: SemanticModel) -> list[str]:
    """Detecta medidas potencialmente huérfanas (no referenciadas por otras).

    Heurística: una medida es candidata a "huérfana" si su nombre no aparece en
    la expresión de ninguna otra medida. (No analiza el uso en visuales, que se
    cubre en el módulo de análisis del reporte.)

    Args:
        model: Modelo semántico.

    Returns:
        Lista de nombres de medidas no referenciadas por otras medidas.
    """
    all_measures = [m for _, m in model.all_measures()]
    names = {m.name for m in all_measures}
    referenced: set[str] = set()
    for measure in all_measures:
        text = measure.expression_text
        for name in names:
            if name != measure.name and f"[{name}]" in text:
                referenced.add(name)
    return sorted(names - referenced)


__all__ = [
    "add_measure",
    "delete_measure",
    "find_orphan_measures",
    "update_measure",
]
