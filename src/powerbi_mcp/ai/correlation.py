"""Análisis de correlaciones entre variables numéricas del modelo.

Calcula la matriz de correlación (Pearson o Spearman), identifica los pares de
variables más correlacionados y advierte de posible **multicolinealidad** (útil
antes de construir modelos de regresión).
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.ai._base import AIResult, select_numeric, to_dataframe
from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

VALID_METHODS = frozenset({"pearson", "spearman", "kendall"})


def correlation_analysis(
    data: Any,
    *,
    columns: list[str] | None = None,
    method: str = "pearson",
    strong_threshold: float = 0.7,
) -> AIResult:
    """Calcula correlaciones y detecta relaciones fuertes.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        columns: Columnas numéricas a usar. Si es ``None``, se autodetectan.
        method: ``"pearson"``, ``"spearman"`` o ``"kendall"``.
        strong_threshold: Umbral de |correlación| para considerarla "fuerte".

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` cuyo ``table`` es la matriz de
        correlación (formato largo: ``var1``, ``var2``, ``correlation``) y cuyo
        ``summary`` lista los pares fuertes y la advertencia de colinealidad.

    Raises:
        ValidationError: Si el método no es válido.
    """
    if method not in VALID_METHODS:
        raise ValidationError(
            "Método de correlación no válido.",
            details={"method": method, "valid": sorted(VALID_METHODS)},
        )

    df = to_dataframe(data)
    numeric = select_numeric(df, columns, min_rows=3)
    corr = numeric.corr(method=method)

    # Formato largo para integrar/visualizar (heatmap).
    long_rows: list[dict[str, Any]] = []
    cols = list(corr.columns)
    for var1 in cols:
        for var2 in cols:
            long_rows.append(
                {
                    "var1": var1,
                    "var2": var2,
                    "correlation": round(float(corr.loc[var1, var2]), 4),
                }
            )

    strong_pairs = []
    for i, var1 in enumerate(cols):
        for var2 in cols[i + 1 :]:
            value = float(corr.loc[var1, var2])
            if abs(value) >= strong_threshold:
                strong_pairs.append(
                    {"var1": var1, "var2": var2, "correlation": round(value, 4)}
                )
    strong_pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)

    summary = {
        "method": method,
        "variables": cols,
        "strong_threshold": strong_threshold,
        "strong_pairs": strong_pairs,
        "multicollinearity_warning": bool(strong_pairs),
    }
    logger.info("Correlación (%s): %d pares fuertes", method, len(strong_pairs))

    return AIResult(
        model_type="correlation",
        summary=summary,
        table=long_rows,
        columns=["var1", "var2", "correlation"],
        metadata={"method": method},
    )


__all__ = ["VALID_METHODS", "correlation_analysis"]
