"""Analizador de buenas prácticas (BPA) del modelo semántico.

Inspirado en el *Best Practice Analyzer* de Tabular Editor, evalúa el modelo
contra un conjunto de reglas agrupadas por categoría (nomenclatura, formato,
rendimiento, mantenibilidad) y devuelve las violaciones con su severidad y una
recomendación accionable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.core.validators import check_naming_convention
from powerbi_mcp.model.measures import find_orphan_measures
from powerbi_mcp.model.relationships import diagnose_relationships
from powerbi_mcp.pbip.models import SemanticModel

logger = get_logger(__name__)


@dataclass
class BPAViolation:
    """Una violación de una regla de buenas prácticas.

    Attributes:
        rule_id: Identificador de la regla (ej. ``"naming.measure_pascalcase"``).
        category: Categoría (``naming``, ``formatting``, ``performance``...).
        severity: ``"error"``, ``"warning"`` o ``"info"``.
        object_type: Tipo de objeto afectado (``measure``, ``column``...).
        object_name: Nombre del objeto afectado.
        message: Descripción del problema.
        recommendation: Acción recomendada para corregirlo.
    """

    rule_id: str
    category: str
    severity: str
    object_type: str
    object_name: str
    message: str
    recommendation: str

    def to_dict(self) -> dict[str, str]:
        """Serializa la violación a diccionario."""
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "object_type": self.object_type,
            "object_name": self.object_name,
            "message": self.message,
            "recommendation": self.recommendation,
        }


@dataclass
class _Collector:
    """Acumulador interno de violaciones."""

    violations: list[BPAViolation] = field(default_factory=list)

    def add(self, **kwargs: str) -> None:
        """Añade una violación."""
        self.violations.append(BPAViolation(**kwargs))


def run_best_practices(model: SemanticModel) -> dict[str, Any]:
    """Ejecuta todas las reglas de buenas prácticas sobre el modelo.

    Args:
        model: Modelo semántico a analizar.

    Returns:
        Diccionario con el resumen por severidad/categoría y la lista de
        violaciones detectadas.
    """
    collector = _Collector()
    rules: list[Callable[[SemanticModel, _Collector], None]] = [
        _rule_measure_naming,
        _rule_measure_format_string,
        _rule_hidden_foreign_keys,
        _rule_column_summarize_by,
        _rule_orphan_measures,
        _rule_relationship_health,
        _rule_calculated_columns,
        _rule_table_naming,
        _rule_measure_description,
    ]
    for rule in rules:
        try:
            rule(model, collector)
        except Exception as exc:
            logger.warning("Regla BPA %s falló: %s", rule.__name__, exc)

    violations = [v.to_dict() for v in collector.violations]
    by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
    by_category: dict[str, int] = {}
    for v in collector.violations:
        by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
        by_category[v.category] = by_category.get(v.category, 0) + 1

    logger.info("BPA: %d violaciones (%s)", len(violations), by_severity)
    return {
        "total_violations": len(violations),
        "by_severity": by_severity,
        "by_category": by_category,
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# Reglas individuales
# ---------------------------------------------------------------------------
def _rule_measure_naming(model: SemanticModel, c: _Collector) -> None:
    """Las medidas deben seguir la convención de nombres recomendada."""
    for _, measure in model.all_measures():
        report = check_naming_convention(measure.name, kind="measure")
        for issue in report.issues:
            c.add(
                rule_id="naming.measure",
                category="naming",
                severity=issue.level,
                object_type="measure",
                object_name=measure.name,
                message=issue.message,
                recommendation=issue.suggestion or "Revisa la convención de nombres de medidas.",
            )


def _rule_table_naming(model: SemanticModel, c: _Collector) -> None:
    """Las tablas deben seguir la convención de nombres recomendada."""
    for table in model.tables:
        report = check_naming_convention(table.name, kind="table")
        for issue in report.issues:
            c.add(
                rule_id="naming.table",
                category="naming",
                severity=issue.level,
                object_type="table",
                object_name=table.name,
                message=issue.message,
                recommendation=issue.suggestion or "Revisa la convención de nombres de tablas.",
            )


def _rule_measure_format_string(model: SemanticModel, c: _Collector) -> None:
    """Las medidas deberían tener una cadena de formato definida."""
    for table_name, measure in model.all_measures():
        if not measure.format_string:
            c.add(
                rule_id="formatting.measure_format_string",
                category="formatting",
                severity="warning",
                object_type="measure",
                object_name=f"{table_name}[{measure.name}]",
                message="La medida no tiene cadena de formato (formatString).",
                recommendation="Define un formato (ej. '#,0', '0.0%') para consistencia visual.",
            )


def _rule_hidden_foreign_keys(model: SemanticModel, c: _Collector) -> None:
    """Las columnas clave usadas en relaciones deberían estar ocultas."""
    fk_columns: set[str] = set()
    for rel in model.relationships:
        fk_columns.add(f"{rel.from_table}[{rel.from_column}]")
    for table in model.tables:
        for col in table.columns:
            ref = f"{table.name}[{col.name}]"
            if ref in fk_columns and not col.is_hidden:
                c.add(
                    rule_id="formatting.hide_foreign_keys",
                    category="formatting",
                    severity="info",
                    object_type="column",
                    object_name=ref,
                    message="Columna clave de relación visible para el usuario.",
                    recommendation="Oculta las claves foráneas para simplificar el modelo.",
                )


def _rule_column_summarize_by(model: SemanticModel, c: _Collector) -> None:
    """Las columnas clave/numéricas de ID no deberían agregarse por defecto."""
    for table in model.tables:
        for col in table.columns:
            name_low = col.name.lower()
            is_key = any(t in name_low for t in ("id", "key", "código", "codigo", "clave"))
            if is_key and col.data_type in {"int64", "double", "decimal"}:
                if col.summarize_by not in {"none", None} and col.summarize_by != "none":
                    c.add(
                        rule_id="formatting.key_summarize_none",
                        category="formatting",
                        severity="warning",
                        object_type="column",
                        object_name=f"{table.name}[{col.name}]",
                        message="Columna de tipo clave con agregación por defecto.",
                        recommendation="Configura summarizeBy='none' en columnas de ID/clave.",
                    )


def _rule_orphan_measures(model: SemanticModel, c: _Collector) -> None:
    """Detecta medidas no referenciadas por otras medidas (posibles huérfanas)."""
    for name in find_orphan_measures(model):
        c.add(
            rule_id="maintainability.orphan_measure",
            category="maintainability",
            severity="info",
            object_type="measure",
            object_name=name,
            message="Medida no referenciada por otras medidas.",
            recommendation="Verifica si se usa en visuales; si no, considera eliminarla.",
        )


def _rule_relationship_health(model: SemanticModel, c: _Collector) -> None:
    """Aplica el diagnóstico de relaciones como reglas BPA."""
    diag = diagnose_relationships(model)
    for broken in diag["broken_relationships"]:
        c.add(
            rule_id="performance.broken_relationship",
            category="performance",
            severity="error",
            object_type="relationship",
            object_name=broken,
            message="Relación con extremos inexistentes.",
            recommendation="Corrige o elimina la relación rota.",
        )
    for pair in diag["ambiguous_pairs"]:
        c.add(
            rule_id="performance.ambiguous_relationship",
            category="performance",
            severity="warning",
            object_type="relationship",
            object_name=pair,
            message="Múltiples relaciones activas entre el mismo par de tablas.",
            recommendation="Deja una sola relación activa; usa USERELATIONSHIP para las demás.",
        )
    for rel_name in diag["bidirectional"]:
        c.add(
            rule_id="performance.bidirectional_filter",
            category="performance",
            severity="info",
            object_type="relationship",
            object_name=rel_name,
            message="Relación con filtro bidireccional.",
            recommendation="Usa filtros bidireccionales solo cuando sea imprescindible.",
        )
    for table in diag["isolated_tables"]:
        c.add(
            rule_id="maintainability.isolated_table",
            category="maintainability",
            severity="info",
            object_type="table",
            object_name=table,
            message="Tabla sin ninguna relación.",
            recommendation="Conecta la tabla al modelo o verifica si es necesaria.",
        )


def _rule_calculated_columns(model: SemanticModel, c: _Collector) -> None:
    """Demasiadas columnas calculadas pueden indicar lógica que debería ir en M."""
    for table in model.tables:
        calc_cols = [col for col in table.columns if col.is_calculated]
        if len(calc_cols) > 5:
            c.add(
                rule_id="performance.too_many_calculated_columns",
                category="performance",
                severity="info",
                object_type="table",
                object_name=table.name,
                message=f"La tabla tiene {len(calc_cols)} columnas calculadas.",
                recommendation="Considera mover cálculos a Power Query (M) para reducir el modelo.",
            )


def _rule_measure_description(model: SemanticModel, c: _Collector) -> None:
    """Las medidas complejas deberían estar documentadas con una descripción."""
    for table_name, measure in model.all_measures():
        if len(measure.expression_text) > 200 and not measure.description:
            c.add(
                rule_id="maintainability.measure_description",
                category="maintainability",
                severity="info",
                object_type="measure",
                object_name=f"{table_name}[{measure.name}]",
                message="Medida compleja sin descripción.",
                recommendation="Documenta la medida con una descripción para mantenibilidad.",
            )


__all__ = ["BPAViolation", "run_best_practices"]
