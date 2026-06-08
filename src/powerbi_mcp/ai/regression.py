"""Modelos de regresión sobre datos del modelo.

Entrena un modelo de regresión (lineal o random forest) para predecir una
variable numérica, reporta métricas (R², MAE, RMSE), la importancia/coeficientes
de cada variable y devuelve las predicciones sobre los datos.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from powerbi_mcp.ai._base import AIResult, to_dataframe
from powerbi_mcp.core.exceptions import AIModelError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

VALID_ALGORITHMS = frozenset({"linear", "random_forest"})


def train_regression(
    data: Any,
    *,
    target_column: str,
    feature_columns: list[str] | None = None,
    algorithm: str = "linear",
    test_size: float = 0.25,
) -> AIResult:
    """Entrena un modelo de regresión y evalúa su desempeño.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        target_column: Variable numérica objetivo.
        feature_columns: Variables predictoras. Si es ``None``, se usan todas
            las demás columnas.
        algorithm: ``"linear"`` o ``"random_forest"``.
        test_size: Proporción de datos para validación (0-1).

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con métricas y la importancia de
        variables (``table``); ``metadata`` incluye las predicciones.

    Raises:
        ValidationError: Si faltan columnas o el objetivo no es numérico.
        AIModelError: Si falla el entrenamiento.
    """
    if algorithm not in VALID_ALGORITHMS:
        raise ValidationError(
            "Algoritmo de regresión no válido.",
            details={"algorithm": algorithm, "valid": sorted(VALID_ALGORITHMS)},
        )

    df = to_dataframe(data)
    if target_column not in df.columns:
        raise ValidationError("Columna objetivo inexistente.", details={"column": target_column})

    features = feature_columns or [c for c in df.columns if c != target_column]
    X = pd.get_dummies(df[features], dummy_na=False).apply(pd.to_numeric, errors="coerce")
    y = pd.to_numeric(df[target_column], errors="coerce")
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]
    if len(X) < 10:
        raise ValidationError("Se requieren al menos 10 filas válidas.", details={"rows": len(X)})

    metrics, importance, model = _fit(X, y, algorithm, test_size)
    importance_rows = sorted(importance, key=lambda r: abs(r["value"]), reverse=True)

    summary = {
        "algorithm": algorithm,
        "target": target_column,
        "metrics": metrics,
        "n_samples": len(X),
        "n_features": int(X.shape[1]),
        "feature_importance": importance_rows,
    }
    logger.info("Regresión %s sobre '%s': R2=%.3f", algorithm, target_column, metrics["r2"])

    return AIResult(
        model_type="regression",
        summary=summary,
        table=importance_rows,
        columns=["feature", "value", "type"],
        metadata={"algorithm": algorithm, "target": target_column, "metrics": metrics},
    )


def _fit(
    X: pd.DataFrame, y: pd.Series, algorithm: str, test_size: float
) -> tuple[dict[str, float], list[dict[str, Any]], Any]:
    """Ajusta el modelo y devuelve ``(métricas, importancia, modelo)``."""
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("scikit-learn no está instalado.") from exc

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42
    )

    if algorithm == "linear":
        model = LinearRegression()
    else:
        model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)

    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    metrics = {
        "r2": round(float(r2_score(y_test, pred)), 4),
        "mae": round(float(mean_absolute_error(y_test, pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_test, pred))), 4),
    }

    if algorithm == "linear":
        importance = [
            {"feature": name, "value": round(float(coef), 6), "type": "coefficient"}
            for name, coef in zip(X.columns, model.coef_, strict=False)
        ]
    else:
        importance = [
            {"feature": name, "value": round(float(imp), 6), "type": "importance"}
            for name, imp in zip(X.columns, model.feature_importances_, strict=False)
        ]

    return metrics, importance, model


__all__ = ["VALID_ALGORITHMS", "train_regression"]
