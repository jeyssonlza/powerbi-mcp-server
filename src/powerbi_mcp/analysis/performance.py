"""Análisis de rendimiento del modelo semántico y optimización de DAX.

Sin necesidad de ejecutar el motor, detecta patrones que suelen impactar el
rendimiento y el tamaño del modelo (alta cardinalidad, tipos pesados, columnas
auto-fecha, medidas con anti-patrones DAX) y propone optimizaciones concretas.

Para análisis con métricas reales (tiempos, tamaño VertiPaq), se requiere una
conexión a Analysis Services; este módulo cubre el análisis estático.
"""

from __future__ import annotations

import re
from typing import Any

from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import SemanticModel

logger = get_logger(__name__)

#: Anti-patrones DAX habituales: (regex, severidad, mensaje, recomendación).
_DAX_ANTIPATTERNS: list[tuple[str, str, str, str]] = [
    (
        r"\bFILTER\s*\(\s*'?\w[\w ]*'?\s*,",
        "warning",
        "Uso de FILTER sobre una tabla completa dentro de CALCULATE.",
        "Si la condición es simple, usa un predicado directo en CALCULATE.",
    ),
    (
        r"[\w\])]\s*/\s*[\w('\[]",
        "warning",
        "División con '/' sin protección de división por cero.",
        "Usa DIVIDE(numerador, denominador, alternativa).",
    ),
    (
        r"\bSUMX\s*\(\s*'?\w[\w ]*'?\s*,\s*[\w'\[\] .]+\)",
        "info",
        "SUMX simple que podría ser una agregación nativa.",
        "Si iteras solo una columna, SUM(Tabla[Col]) es más eficiente.",
    ),
    (
        r"\bCALCULATE\s*\(\s*CALCULATE\b",
        "info",
        "CALCULATE anidado.",
        "Revisa si el anidamiento de CALCULATE es necesario.",
    ),
    (
        r"\bEARLIER\b",
        "info",
        "Uso de EARLIER (patrón antiguo).",
        "Considera variables (VAR) para mayor claridad y rendimiento.",
    ),
]


def analyze_performance(model: SemanticModel) -> dict[str, Any]:
    """Analiza el modelo en busca de problemas de rendimiento (estático).

    Args:
        model: Modelo semántico a analizar.

    Returns:
        Diccionario con hallazgos por categoría y una lista priorizada de
        recomendaciones de optimización.
    """
    findings: list[dict[str, Any]] = []

    findings.extend(_check_auto_date_columns(model))
    findings.extend(_check_data_types(model))
    findings.extend(_check_calculated_columns(model))
    findings.extend(_check_dax_antipatterns(model))
    findings.extend(_check_bidirectional(model))

    severity_order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 3))

    summary: dict[str, int] = {}
    for f in findings:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1

    logger.info("Análisis de rendimiento: %d hallazgos", len(findings))
    return {
        "total_findings": len(findings),
        "by_severity": summary,
        "findings": findings,
    }


def optimize_dax(expression: str) -> dict[str, Any]:
    """Analiza una expresión DAX y sugiere optimizaciones.

    Args:
        expression: Expresión DAX a revisar.

    Returns:
        Diccionario con la lista de sugerencias de optimización detectadas.
    """
    suggestions: list[dict[str, str]] = []
    upper_expr = expression
    for pattern, severity, message, recommendation in _DAX_ANTIPATTERNS:
        flags = re.IGNORECASE
        if re.search(pattern, upper_expr, flags) and not _is_false_positive(pattern, expression):
            suggestions.append(
                {"severity": severity, "message": message, "recommendation": recommendation}
            )
    return {"suggestions": suggestions, "suggestion_count": len(suggestions)}


def _is_false_positive(pattern: str, expression: str) -> bool:
    """Evita marcar DIVIDE como división insegura."""
    if "/" in pattern and "DIVIDE" in expression.upper():
        return True
    return False


# ---------------------------------------------------------------------------
# Comprobaciones de modelo
# ---------------------------------------------------------------------------
def _check_auto_date_columns(model: SemanticModel) -> list[dict[str, Any]]:
    """Detecta posibles jerarquías de fecha automáticas (impacto de tamaño)."""
    findings: list[dict[str, Any]] = []
    for table in model.tables:
        if table.name.lower().startswith("localdatetable") or "datetemplate" in table.name.lower():
            findings.append(
                {
                    "category": "model_size",
                    "severity": "warning",
                    "object": table.name,
                    "message": "Tabla de fecha automática detectada.",
                    "recommendation": "Desactiva 'Auto fecha/hora' y usa una tabla de fechas propia.",
                }
            )
    return findings


def _check_data_types(model: SemanticModel) -> list[dict[str, Any]]:
    """Detecta tipos de datos potencialmente pesados o mejorables."""
    findings: list[dict[str, Any]] = []
    for table in model.tables:
        for col in table.columns:
            if col.data_type == "double" and any(
                t in col.name.lower() for t in ("id", "key", "code", "año", "year")
            ):
                findings.append(
                    {
                        "category": "data_type",
                        "severity": "info",
                        "object": f"{table.name}[{col.name}]",
                        "message": "Columna de tipo double que parece un entero/clave.",
                        "recommendation": "Usa int64 para reducir tamaño y mejorar compresión.",
                    }
                )
    return findings


def _check_calculated_columns(model: SemanticModel) -> list[dict[str, Any]]:
    """Marca columnas calculadas (no se comprimen tan bien como las de datos)."""
    findings: list[dict[str, Any]] = []
    for table in model.tables:
        calc = [c.name for c in table.columns if c.is_calculated]
        if calc:
            findings.append(
                {
                    "category": "model_size",
                    "severity": "info",
                    "object": table.name,
                    "message": f"{len(calc)} columna(s) calculada(s): {', '.join(calc[:5])}.",
                    "recommendation": "Cuando sea posible, calcula en Power Query (M) o en el origen.",
                }
            )
    return findings


def _check_dax_antipatterns(model: SemanticModel) -> list[dict[str, Any]]:
    """Aplica el análisis de anti-patrones DAX a todas las medidas."""
    findings: list[dict[str, Any]] = []
    for table_name, measure in model.all_measures():
        result = optimize_dax(measure.expression_text)
        for sug in result["suggestions"]:
            findings.append(
                {
                    "category": "dax",
                    "severity": sug["severity"],
                    "object": f"{table_name}[{measure.name}]",
                    "message": sug["message"],
                    "recommendation": sug["recommendation"],
                }
            )
    return findings


def _check_bidirectional(model: SemanticModel) -> list[dict[str, Any]]:
    """Marca relaciones bidireccionales por su impacto de rendimiento."""
    findings: list[dict[str, Any]] = []
    for rel in model.relationships:
        if rel.is_bidirectional:
            findings.append(
                {
                    "category": "relationship",
                    "severity": "info",
                    "object": rel.name or f"{rel.from_table}->{rel.to_table}",
                    "message": "Relación con filtro cruzado bidireccional.",
                    "recommendation": "Limita el filtrado bidireccional; suele penalizar el rendimiento.",
                }
            )
    return findings


__all__ = ["analyze_performance", "optimize_dax"]
