"""Perfilado automático de tablas y columnas.

Genera un perfil estadístico detallado de un conjunto de datos (similar a un
"data profiling" ligero), con distribución, estadísticas descriptivas, valores
más frecuentes y detección del tipo semántico de cada columna (id, categórica,
numérica, fecha, booleana, texto libre).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from powerbi_mcp.ai._base import to_dataframe
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def profile_dataset(data: Any, *, top_n: int = 5) -> dict[str, Any]:
    """Perfila un conjunto de datos completo.

    Args:
        data: Datos de entrada (DataFrame, registros, dict de columnas o ruta).
        top_n: Número de valores más frecuentes a reportar por columna.

    Returns:
        Diccionario con un resumen general y el perfil de cada columna.
    """
    df = to_dataframe(data)
    columns = [_profile_column(df[col], len(df), top_n) for col in df.columns]

    semantic_counts: dict[str, int] = {}
    for col in columns:
        semantic_counts[col["semantic_type"]] = semantic_counts.get(col["semantic_type"], 0) + 1

    summary = {
        "rows": len(df),
        "columns": int(df.shape[1]),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
        "semantic_type_distribution": semantic_counts,
    }
    logger.info("Perfilado: %d filas, %d columnas", summary["rows"], summary["columns"])
    return {"summary": summary, "columns": columns}


def _profile_column(series: pd.Series, n_rows: int, top_n: int) -> dict[str, Any]:
    """Perfila una columna individual."""
    non_null = series.dropna()
    distinct = int(non_null.nunique())

    profile: dict[str, Any] = {
        "name": str(series.name),
        "dtype": str(series.dtype),
        "semantic_type": _infer_semantic_type(series, distinct, n_rows),
        "count": int(non_null.shape[0]),
        "null_count": int(series.isna().sum()),
        "distinct_count": distinct,
        "distinct_pct": round(distinct / n_rows * 100, 2) if n_rows else 0.0,
    }

    # Valores más frecuentes.
    if not non_null.empty:
        top = non_null.value_counts().head(top_n)
        profile["top_values"] = [
            {"value": _coerce(v), "count": int(c)} for v, c in top.items()
        ]

    if pd.api.types.is_numeric_dtype(series) and not non_null.empty:
        desc = non_null.describe()
        profile["statistics"] = {
            "min": round(float(desc["min"]), 4),
            "q1": round(float(desc["25%"]), 4),
            "median": round(float(desc["50%"]), 4),
            "q3": round(float(desc["75%"]), 4),
            "max": round(float(desc["max"]), 4),
            "mean": round(float(desc["mean"]), 4),
            "std": round(float(desc["std"]), 4) if not pd.isna(desc["std"]) else 0.0,
        }
    elif pd.api.types.is_datetime64_any_dtype(series) and not non_null.empty:
        profile["statistics"] = {
            "min": str(non_null.min()),
            "max": str(non_null.max()),
            "range_days": int((non_null.max() - non_null.min()).days),
        }

    return profile


def _infer_semantic_type(series: pd.Series, distinct: int, n_rows: int) -> str:
    """Infiere el tipo semántico de una columna."""
    name = str(series.name).lower()
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if distinct == n_rows and n_rows > 0:
        return "identifier"
    if (
        any(token in name for token in ("id", "key", "code", "codigo", "clave"))
        and distinct / max(n_rows, 1) > 0.9
    ):
        return "identifier"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if distinct <= max(20, int(0.05 * n_rows)):
        return "categorical"
    return "free_text"


def _coerce(value: Any) -> Any:
    """Convierte un valor a un tipo JSON-serializable."""
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            return str(value)
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


__all__ = ["profile_dataset"]
