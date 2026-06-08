"""Clustering (segmentación no supervisada) sobre datos del modelo.

Soporta:

- ``kmeans``: particional, rápido; permite elegir ``k`` o autodeterminarlo por
  el método del codo + silueta.
- ``hierarchical``: aglomerativo (jerárquico), útil cuando interesa la
  estructura anidada de los grupos.

Devuelve, por fila, la etiqueta de clúster asignada y un resumen con el perfil
(centro/medias) de cada grupo para su interpretación.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from powerbi_mcp.ai._base import AIResult, select_numeric, standardize, to_dataframe
from powerbi_mcp.core.exceptions import AIModelError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

VALID_ALGORITHMS = frozenset({"kmeans", "hierarchical"})


def run_clustering(
    data: Any,
    *,
    columns: list[str] | None = None,
    algorithm: str = "kmeans",
    n_clusters: int | None = None,
    max_k: int = 10,
) -> AIResult:
    """Agrupa las filas en clústeres y perfila cada grupo.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        columns: Columnas numéricas a usar. Si es ``None``, se autodetectan.
        algorithm: ``"kmeans"`` o ``"hierarchical"``.
        n_clusters: Número de clústeres. Si es ``None``, se determina
            automáticamente (silueta) entre 2 y ``max_k``.
        max_k: Máximo número de clústeres a evaluar en la autodeterminación.

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con la columna ``cluster`` y un
        ``summary`` que incluye el perfil de cada grupo.

    Raises:
        ValidationError: Si el algoritmo o los parámetros son inválidos.
        AIModelError: Si falla el ajuste.
    """
    if algorithm not in VALID_ALGORITHMS:
        raise ValidationError(
            "Algoritmo de clustering no válido.",
            details={"algorithm": algorithm, "valid": sorted(VALID_ALGORITHMS)},
        )

    df = to_dataframe(data)
    numeric = select_numeric(df, columns, min_rows=4)
    X = standardize(numeric)

    if n_clusters is None:
        n_clusters = _auto_select_k(X, max_k=min(max_k, len(X) - 1))

    if not 2 <= n_clusters <= len(X):
        raise ValidationError(
            "n_clusters fuera de rango.",
            details={"n_clusters": n_clusters, "rows": len(X)},
        )

    labels, silhouette = _fit(X, algorithm, n_clusters)

    result_df = numeric.copy()
    result_df["cluster"] = labels

    profiles = _profile_clusters(result_df, list(numeric.columns))
    summary = {
        "algorithm": algorithm,
        "n_clusters": int(n_clusters),
        "silhouette_score": round(float(silhouette), 4),
        "columns_used": list(numeric.columns),
        "cluster_sizes": result_df["cluster"].value_counts().sort_index().to_dict(),
        "profiles": profiles,
    }
    logger.info("Clustering %s con k=%d (silueta=%.3f)", algorithm, n_clusters, silhouette)

    return AIResult(
        model_type="clustering",
        summary=summary,
        table=result_df.to_dict(orient="records"),
        columns=list(result_df.columns),
        metadata={"algorithm": algorithm, "n_clusters": int(n_clusters)},
    )


def _auto_select_k(X: np.ndarray, *, max_k: int) -> int:
    """Selecciona el número de clústeres maximizando la silueta media."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("scikit-learn no está instalado.") from exc

    best_k, best_score = 2, -1.0
    upper = max(2, min(max_k, 10))
    for k in range(2, upper + 1):
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = model.fit_predict(X)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X, labels)
        if score > best_score:
            best_k, best_score = k, score
    return best_k


def _fit(X: np.ndarray, algorithm: str, n_clusters: int) -> tuple[np.ndarray, float]:
    """Ajusta el algoritmo elegido; devuelve ``(labels, silhouette)``."""
    try:
        from sklearn.cluster import AgglomerativeClustering, KMeans
        from sklearn.metrics import silhouette_score
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("scikit-learn no está instalado.") from exc

    if algorithm == "kmeans":
        model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    else:
        model = AgglomerativeClustering(n_clusters=n_clusters)

    labels = model.fit_predict(X)
    silhouette = silhouette_score(X, labels) if len(set(labels)) > 1 else 0.0
    return labels, float(silhouette)


def _profile_clusters(df: pd.DataFrame, feature_cols: list[str]) -> dict[str, Any]:
    """Calcula el perfil medio de cada clúster para su interpretación."""
    profiles: dict[str, Any] = {}
    for cluster_id, group in df.groupby("cluster"):
        profiles[str(int(cluster_id))] = {
            "size": len(group),
            "means": {col: round(float(group[col].mean()), 4) for col in feature_cols},
        }
    return profiles


__all__ = ["VALID_ALGORITHMS", "run_clustering"]
