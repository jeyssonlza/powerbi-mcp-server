"""Detección de anomalías sobre datos del modelo Power BI.

Ofrece tres métodos complementarios:

- ``isolation_forest``: multivariante, basado en aislamiento (scikit-learn).
- ``zscore``: univariante/multivariante, marca puntos con |z| > umbral.
- ``iqr``: univariante, regla del rango intercuartílico (robusta a outliers).

El resultado incluye, por fila, una marca de anomalía y una puntuación, listo
para integrarse como tabla calculada o visualizarse resaltando los outliers.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from powerbi_mcp.ai._base import AIResult, select_numeric, standardize, to_dataframe
from powerbi_mcp.core.exceptions import AIModelError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

VALID_METHODS = frozenset({"isolation_forest", "zscore", "iqr"})


def detect_anomalies(
    data: Any,
    *,
    columns: list[str] | None = None,
    method: str = "isolation_forest",
    contamination: float = 0.05,
    zscore_threshold: float = 3.0,
    iqr_factor: float = 1.5,
) -> AIResult:
    """Detecta anomalías en un conjunto de datos.

    Args:
        data: Datos de entrada (DataFrame, registros, dict de columnas o ruta).
        columns: Columnas numéricas a usar. Si es ``None``, se autodetectan.
        method: ``"isolation_forest"``, ``"zscore"`` o ``"iqr"``.
        contamination: Proporción esperada de anomalías (solo isolation_forest).
        zscore_threshold: Umbral de |z| para marcar anomalía (solo zscore).
        iqr_factor: Factor del rango intercuartílico (solo iqr).

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con columnas originales más
        ``is_anomaly`` (bool) y ``anomaly_score`` (float).

    Raises:
        ValidationError: Si el método no es válido.
        AIModelError: Si falla el ajuste del modelo.
    """
    if method not in VALID_METHODS:
        raise ValidationError(
            "Método de detección no válido.",
            details={"method": method, "valid": sorted(VALID_METHODS)},
        )

    df = to_dataframe(data)
    numeric = select_numeric(df, columns)

    if method == "isolation_forest":
        flags, scores = _isolation_forest(numeric, contamination)
    elif method == "zscore":
        flags, scores = _zscore(numeric, zscore_threshold)
    else:  # iqr
        flags, scores = _iqr(numeric, iqr_factor)

    result_df = numeric.copy()
    result_df["is_anomaly"] = flags
    result_df["anomaly_score"] = np.round(scores, 6)

    n_anomalies = int(flags.sum())
    summary = {
        "method": method,
        "total_rows": len(result_df),
        "anomalies_detected": n_anomalies,
        "anomaly_rate": round(n_anomalies / len(result_df), 4) if len(result_df) else 0.0,
        "columns_used": list(numeric.columns),
    }
    logger.info("Anomalías detectadas: %d/%d (%s)", n_anomalies, len(result_df), method)

    return AIResult(
        model_type="anomaly",
        summary=summary,
        table=result_df.to_dict(orient="records"),
        columns=list(result_df.columns),
        metadata={
            "method": method,
            "contamination": contamination,
            "zscore_threshold": zscore_threshold,
            "iqr_factor": iqr_factor,
        },
    )


def _isolation_forest(numeric: Any, contamination: float) -> tuple[np.ndarray, np.ndarray]:
    """Ajusta un Isolation Forest y devuelve ``(flags, scores)``."""
    if not 0 < contamination < 0.5:
        raise ValidationError(
            "contamination debe estar en (0, 0.5).",
            details={"contamination": contamination},
        )
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("scikit-learn no está instalado.") from exc

    X = standardize(numeric)
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    pred = model.fit_predict(X)
    # decision_function: mayor = más normal; invertimos para que mayor = más anómalo.
    scores = -model.decision_function(X)
    flags = pred == -1
    return flags, scores


def _zscore(numeric: Any, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """Detección por z-score; ``score`` = |z| máximo por fila."""
    X = standardize(numeric)
    abs_z = np.abs(X)
    max_z = abs_z.max(axis=1)
    flags = max_z > threshold
    return flags, max_z


def _iqr(numeric: Any, factor: float) -> tuple[np.ndarray, np.ndarray]:
    """Detección por rango intercuartílico (IQR) sobre cualquier columna."""
    values = numeric.to_numpy(dtype=float)
    q1 = np.percentile(values, 25, axis=0)
    q3 = np.percentile(values, 75, axis=0)
    iqr = q3 - q1
    iqr[iqr == 0] = 1e-9
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    below = values < lower
    above = values > upper
    out_of_range = below | above
    flags = out_of_range.any(axis=1)
    # Score: distancia relativa máxima fuera de los límites.
    dist = np.maximum((lower - values) / iqr, (values - upper) / iqr)
    scores = np.clip(dist, 0, None).max(axis=1)
    return flags, scores


__all__ = ["VALID_METHODS", "detect_anomalies"]
