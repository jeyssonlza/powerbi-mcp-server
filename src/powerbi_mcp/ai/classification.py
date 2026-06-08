"""Modelos de clasificación sobre datos del modelo.

Entrena un clasificador (regresión logística o random forest) para predecir una
variable categórica, reporta métricas (accuracy, precision, recall, F1), la
importancia de variables y la matriz de confusión.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from powerbi_mcp.ai._base import AIResult, to_dataframe
from powerbi_mcp.core.exceptions import AIModelError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

VALID_ALGORITHMS = frozenset({"logistic", "random_forest"})


def train_classification(
    data: Any,
    *,
    target_column: str,
    feature_columns: list[str] | None = None,
    algorithm: str = "random_forest",
    test_size: float = 0.25,
) -> AIResult:
    """Entrena un clasificador y evalúa su desempeño.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        target_column: Variable categórica objetivo.
        feature_columns: Variables predictoras. Si es ``None``, se usan todas
            las demás columnas.
        algorithm: ``"logistic"`` o ``"random_forest"``.
        test_size: Proporción de datos para validación (0-1).

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con la importancia de variables
        (``table``) y métricas + matriz de confusión en ``summary``.

    Raises:
        ValidationError: Si faltan columnas o hay muy pocas clases/filas.
        AIModelError: Si falla el entrenamiento.
    """
    if algorithm not in VALID_ALGORITHMS:
        raise ValidationError(
            "Algoritmo de clasificación no válido.",
            details={"algorithm": algorithm, "valid": sorted(VALID_ALGORITHMS)},
        )

    df = to_dataframe(data)
    if target_column not in df.columns:
        raise ValidationError("Columna objetivo inexistente.", details={"column": target_column})

    features = feature_columns or [c for c in df.columns if c != target_column]
    X = pd.get_dummies(df[features], dummy_na=False).apply(pd.to_numeric, errors="coerce")
    y = df[target_column].astype("category")
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]

    if y.nunique() < 2:
        raise ValidationError("El objetivo debe tener al menos 2 clases.")
    if len(X) < 10:
        raise ValidationError("Se requieren al menos 10 filas válidas.", details={"rows": len(X)})

    metrics, importance, confusion, labels = _fit(X, y, algorithm, test_size)
    importance_rows = sorted(importance, key=lambda r: r["importance"], reverse=True)

    summary = {
        "algorithm": algorithm,
        "target": target_column,
        "classes": [str(c) for c in labels],
        "metrics": metrics,
        "confusion_matrix": confusion,
        "n_samples": len(X),
        "feature_importance": importance_rows,
    }
    logger.info(
        "Clasificación %s sobre '%s': accuracy=%.3f",
        algorithm,
        target_column,
        metrics["accuracy"],
    )

    return AIResult(
        model_type="classification",
        summary=summary,
        table=importance_rows,
        columns=["feature", "importance"],
        metadata={"algorithm": algorithm, "target": target_column, "metrics": metrics},
    )


def _fit(
    X: pd.DataFrame, y: pd.Series, algorithm: str, test_size: float
) -> tuple[dict[str, float], list[dict[str, Any]], list[list[int]], list[Any]]:
    """Ajusta el clasificador; devuelve métricas, importancia y confusión."""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.inspection import permutation_importance
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import (
            accuracy_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
        )
        from sklearn.model_selection import train_test_split
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("scikit-learn no está instalado.") from exc

    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )

    if algorithm == "logistic":
        model = LogisticRegression(max_iter=1000, n_jobs=-1)
    else:
        model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)

    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    # 'binary' solo es válido con etiquetas 0/1; para binario no numérico
    # (p. ej. 'Norte'/'Sur') usamos 'weighted', que da el mismo resultado útil.
    unique_labels = set(y.cat.categories) if hasattr(y, "cat") else set(y.unique())
    is_numeric_binary = y.nunique() == 2 and unique_labels <= {0, 1}
    avg = "binary" if is_numeric_binary else "weighted"
    metrics = {
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "precision": round(float(precision_score(y_test, pred, average=avg, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, pred, average=avg, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, pred, average=avg, zero_division=0)), 4),
    }

    if algorithm == "random_forest":
        importances = model.feature_importances_
    else:
        perm = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=42)
        importances = perm.importances_mean
    importance = [
        {"feature": name, "importance": round(float(imp), 6)}
        for name, imp in zip(X.columns, importances, strict=False)
    ]

    labels = list(model.classes_)
    confusion = confusion_matrix(y_test, pred, labels=labels).tolist()
    return metrics, importance, confusion, labels


__all__ = ["VALID_ALGORITHMS", "train_classification"]
