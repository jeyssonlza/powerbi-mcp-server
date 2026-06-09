"""Árbol de decisión explicativo (key influencers).

Entrena un árbol de decisión poco profundo para **explicar** qué variables
influyen en un objetivo (categórico o numérico) y devuelve:

- La importancia de cada variable.
- Las reglas del árbol en texto legible (similar a "key influencers").
- La precisión/score del modelo como referencia de confianza.

No busca máxima precisión sino interpretabilidad, por eso la profundidad es baja
por defecto.
"""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from powerbi_mcp.ai._base import AIResult, to_dataframe
from powerbi_mcp.core.exceptions import AIModelError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def decision_tree_explain(
    data: Any,
    *,
    target_column: str,
    feature_columns: list[str] | None = None,
    max_depth: int = 4,
    task: str = "auto",
) -> AIResult:
    """Entrena un árbol de decisión explicativo sobre el objetivo indicado.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        target_column: Columna objetivo a explicar.
        feature_columns: Variables explicativas. Si es ``None``, se usan todas
            las demás columnas.
        max_depth: Profundidad máxima del árbol (interpretabilidad).
        task: ``"classification"``, ``"regression"`` o ``"auto"`` (detecta según
            el tipo del objetivo).

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con la importancia de variables
        (``table``) y las reglas del árbol y métricas en ``summary``.

    Raises:
        ValidationError: Si faltan columnas o el objetivo es inválido.
        AIModelError: Si falla el entrenamiento.
    """
    df = to_dataframe(data)
    if target_column not in df.columns:
        raise ValidationError("Columna objetivo inexistente.", details={"column": target_column})

    features = feature_columns or [c for c in df.columns if c != target_column]
    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValidationError("Columnas explicativas inexistentes.", details={"missing": missing})

    X, feature_names = _encode_features(df[features])
    y = df[target_column]
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]
    if len(X) < 10:
        raise ValidationError("Se requieren al menos 10 filas válidas.", details={"rows": len(X)})

    resolved_task = _resolve_task(y) if task == "auto" else task
    tree, score, importances = _fit_tree(X, y, resolved_task, max_depth)
    rules = _export_rules(tree, feature_names, resolved_task)

    importance_rows = sorted(
        (
            {"feature": name, "importance": round(float(imp), 4)}
            for name, imp in zip(feature_names, importances, strict=False)
        ),
        key=lambda r: cast(float, r["importance"]),
        reverse=True,
    )

    summary = {
        "task": resolved_task,
        "target": target_column,
        "score": round(float(score), 4),
        "score_metric": "accuracy" if resolved_task == "classification" else "r2",
        "max_depth": max_depth,
        "top_influencers": importance_rows[:5],
        "rules": rules,
    }
    logger.info("Árbol de decisión (%s) sobre '%s': score=%.3f", resolved_task, target_column, score)

    return AIResult(
        model_type="decision_tree",
        summary=summary,
        table=importance_rows,
        columns=["feature", "importance"],
        metadata={"task": resolved_task, "target": target_column},
    )


def _encode_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Codifica variables categóricas con one-hot; devuelve ``(X, nombres)``."""
    encoded = pd.get_dummies(df, dummy_na=False)
    encoded = encoded.apply(pd.to_numeric, errors="coerce")
    return encoded, list(encoded.columns)


def _resolve_task(y: pd.Series) -> str:
    """Decide si el objetivo es de clasificación o regresión."""
    if y.dtype == object or y.dtype.name == "category":
        return "classification"
    # Numérico con pocos valores distintos -> clasificación.
    if y.nunique() <= max(10, int(0.05 * len(y))):
        return "classification"
    return "regression"


def _fit_tree(
    X: pd.DataFrame, y: pd.Series, task: str, max_depth: int
) -> tuple[Any, float, Any]:
    """Ajusta el árbol adecuado y devuelve ``(modelo, score, importancias)``."""
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("scikit-learn no está instalado.") from exc

    stratify = y if task == "classification" and y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify
    )

    if task == "classification":
        model = DecisionTreeClassifier(max_depth=max_depth, random_state=42, min_samples_leaf=5)
    else:
        model = DecisionTreeRegressor(max_depth=max_depth, random_state=42, min_samples_leaf=5)

    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    return model, score, model.feature_importances_


def _export_rules(tree: Any, feature_names: list[str], task: str) -> list[str]:
    """Exporta las reglas del árbol a texto legible."""
    try:
        from sklearn.tree import export_text
    except ImportError:  # pragma: no cover
        return []
    text = export_text(tree, feature_names=list(feature_names), max_depth=4)
    return [line for line in text.splitlines() if line.strip()]


__all__ = ["decision_tree_explain"]
