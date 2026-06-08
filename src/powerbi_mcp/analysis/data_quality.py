"""Análisis de calidad de datos sobre conjuntos tabulares.

Evalúa, por columna y a nivel de tabla:

- **Completitud**: conteo y porcentaje de nulos.
- **Unicidad**: duplicados de fila y cardinalidad por columna.
- **Validez**: outliers numéricos (IQR), valores constantes.
- **Consistencia**: tipos mixtos, espacios sobrantes en texto.

Produce un informe accionable con una puntuación global de calidad (0-100).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from powerbi_mcp.ai._base import to_dataframe
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def analyze_data_quality(data: Any, *, outlier_factor: float = 1.5) -> dict[str, Any]:
    """Ejecuta un análisis completo de calidad de datos.

    Args:
        data: Datos de entrada (DataFrame, registros, dict de columnas o ruta).
        outlier_factor: Factor IQR para marcar outliers numéricos.

    Returns:
        Diccionario con métricas a nivel de tabla y por columna, hallazgos y una
        ``quality_score`` global (0-100).
    """
    df = to_dataframe(data)
    n_rows = len(df)
    n_cols = int(df.shape[1])

    duplicated_rows = int(df.duplicated().sum())
    columns_report = [_analyze_column(df[col], n_rows, outlier_factor) for col in df.columns]

    total_nulls = sum(c["null_count"] for c in columns_report)
    total_cells = max(n_rows * n_cols, 1)
    completeness = 1 - (total_nulls / total_cells)
    uniqueness = 1 - (duplicated_rows / n_rows) if n_rows else 1.0

    findings = _collect_findings(columns_report, duplicated_rows, n_rows)
    quality_score = _quality_score(completeness, uniqueness, columns_report)

    report = {
        "rows": n_rows,
        "columns": n_cols,
        "duplicated_rows": duplicated_rows,
        "completeness_pct": round(completeness * 100, 2),
        "uniqueness_pct": round(uniqueness * 100, 2),
        "quality_score": quality_score,
        "findings": findings,
        "columns_detail": columns_report,
    }
    logger.info("Calidad de datos: score=%.1f (%d filas, %d cols)", quality_score, n_rows, n_cols)
    return report


def _analyze_column(series: pd.Series, n_rows: int, outlier_factor: float) -> dict[str, Any]:
    """Analiza la calidad de una columna individual."""
    null_count = int(series.isna().sum())
    non_null = series.dropna()
    distinct = int(non_null.nunique())
    cardinality_ratio = round(distinct / n_rows, 4) if n_rows else 0.0

    detail: dict[str, Any] = {
        "name": str(series.name),
        "dtype": str(series.dtype),
        "null_count": null_count,
        "null_pct": round(null_count / n_rows * 100, 2) if n_rows else 0.0,
        "distinct_count": distinct,
        "cardinality_ratio": cardinality_ratio,
        "is_constant": distinct <= 1,
        "is_unique_key": distinct == n_rows and null_count == 0 and n_rows > 0,
    }

    if pd.api.types.is_numeric_dtype(series) and not non_null.empty:
        detail.update(_numeric_stats(non_null, outlier_factor))
    elif not non_null.empty:
        detail.update(_text_stats(non_null))

    return detail


def _numeric_stats(non_null: pd.Series, outlier_factor: float) -> dict[str, Any]:
    """Calcula estadísticas y outliers de una columna numérica."""
    values = non_null.to_numpy(dtype=float)
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    lower, upper = q1 - outlier_factor * iqr, q3 + outlier_factor * iqr
    outliers = int(((values < lower) | (values > upper)).sum())
    return {
        "min": round(float(values.min()), 4),
        "max": round(float(values.max()), 4),
        "mean": round(float(values.mean()), 4),
        "std": round(float(values.std()), 4),
        "outlier_count": outliers,
        "outlier_pct": round(outliers / len(values) * 100, 2),
    }


def _text_stats(non_null: pd.Series) -> dict[str, Any]:
    """Calcula estadísticas de una columna de texto."""
    as_str = non_null.astype(str)
    has_whitespace = int((as_str != as_str.str.strip()).sum())
    lengths = as_str.str.len()
    return {
        "min_length": int(lengths.min()),
        "max_length": int(lengths.max()),
        "leading_trailing_spaces": has_whitespace,
    }


def _collect_findings(
    columns_report: list[dict[str, Any]], duplicated_rows: int, n_rows: int
) -> list[dict[str, str]]:
    """Genera hallazgos accionables a partir del detalle por columna."""
    findings: list[dict[str, str]] = []
    if duplicated_rows:
        findings.append(
            {
                "level": "warning",
                "message": f"Hay {duplicated_rows} filas duplicadas "
                f"({round(duplicated_rows / n_rows * 100, 1)}%).",
            }
        )
    for col in columns_report:
        if col["null_pct"] >= 20:
            findings.append(
                {"level": "warning", "message": f"Columna '{col['name']}' tiene {col['null_pct']}% de nulos."}
            )
        if col["is_constant"]:
            findings.append(
                {"level": "info", "message": f"Columna '{col['name']}' es constante (sin variación)."}
            )
        if col.get("outlier_pct", 0) >= 5:
            findings.append(
                {"level": "info", "message": f"Columna '{col['name']}' tiene {col['outlier_pct']}% de outliers."}
            )
        if col.get("leading_trailing_spaces", 0):
            findings.append(
                {
                    "level": "info",
                    "message": f"Columna '{col['name']}' tiene valores con espacios sobrantes.",
                }
            )
    return findings


def _quality_score(
    completeness: float, uniqueness: float, columns_report: list[dict[str, Any]]
) -> float:
    """Calcula una puntuación global de calidad (0-100)."""
    constant_penalty = sum(1 for c in columns_report if c["is_constant"])
    constant_factor = 1 - (constant_penalty / max(len(columns_report), 1)) * 0.3
    score = (completeness * 0.5 + uniqueness * 0.3 + constant_factor * 0.2) * 100
    return round(max(0.0, min(100.0, score)), 1)


__all__ = ["analyze_data_quality"]
