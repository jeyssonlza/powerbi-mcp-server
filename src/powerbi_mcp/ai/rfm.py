"""Segmentación RFM (Recency, Frequency, Monetary).

A partir de un detalle de transacciones (cliente, fecha, importe), calcula para
cada cliente:

- **Recency**: días desde su última compra (menos es mejor).
- **Frequency**: número de compras (más es mejor).
- **Monetary**: importe total gastado (más es mejor).

Asigna una puntuación 1-5 por dimensión (quintiles) y deriva un segmento de
negocio (``Champions``, ``Loyal``, ``At Risk``, ``Hibernating``...), listo para
integrarse al modelo y accionar campañas.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from powerbi_mcp.ai._base import AIResult, to_dataframe
from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def rfm_segmentation(
    data: Any,
    *,
    customer_column: str,
    date_column: str,
    amount_column: str,
    reference_date: str | None = None,
) -> AIResult:
    """Calcula RFM y segmenta clientes.

    Args:
        data: Detalle de transacciones (DataFrame, registros, dict o ruta).
        customer_column: Columna identificadora del cliente.
        date_column: Columna de fecha de la transacción.
        amount_column: Columna del importe de la transacción.
        reference_date: Fecha de referencia para la recencia (ISO). Si es
            ``None``, se usa la fecha máxima del dataset + 1 día.

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con una fila por cliente y las
        columnas RFM, sus puntuaciones y el segmento asignado.

    Raises:
        ValidationError: Si faltan columnas requeridas.
    """
    df = to_dataframe(data)
    for col in (customer_column, date_column, amount_column):
        if col not in df.columns:
            raise ValidationError("Columna inexistente.", details={"column": col})

    work = df[[customer_column, date_column, amount_column]].copy()
    work[date_column] = pd.to_datetime(work[date_column], errors="coerce")
    work[amount_column] = pd.to_numeric(work[amount_column], errors="coerce")
    work = work.dropna()
    if work.empty:
        raise ValidationError("No hay transacciones válidas tras limpiar datos.")

    ref = (
        pd.to_datetime(reference_date)
        if reference_date
        else work[date_column].max() + pd.Timedelta(days=1)
    )

    rfm = work.groupby(customer_column).agg(
        recency=(date_column, lambda s: (ref - s.max()).days),
        frequency=(date_column, "count"),
        monetary=(amount_column, "sum"),
    ).reset_index()

    rfm["R_score"] = _score(rfm["recency"], reverse=True)
    rfm["F_score"] = _score(rfm["frequency"], reverse=False)
    rfm["M_score"] = _score(rfm["monetary"], reverse=False)
    rfm["RFM_score"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]
    rfm["segment"] = rfm.apply(
        lambda row: _segment(row["R_score"], row["F_score"], row["M_score"]), axis=1
    )

    rfm["monetary"] = rfm["monetary"].round(2)
    summary = {
        "customers": len(rfm),
        "reference_date": ref.isoformat(),
        "segment_distribution": rfm["segment"].value_counts().to_dict(),
        "avg_recency": round(float(rfm["recency"].mean()), 2),
        "avg_frequency": round(float(rfm["frequency"].mean()), 2),
        "avg_monetary": round(float(rfm["monetary"].mean()), 2),
    }
    logger.info("RFM: %d clientes segmentados", len(rfm))

    return AIResult(
        model_type="rfm",
        summary=summary,
        table=rfm.to_dict(orient="records"),
        columns=list(rfm.columns),
        metadata={"reference_date": ref.isoformat()},
    )


def _score(series: pd.Series, *, reverse: bool) -> pd.Series:
    """Asigna puntuación 1-5 por quintiles. ``reverse`` invierte (menos=mejor)."""
    try:
        ranks = pd.qcut(series.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
        scores = ranks.astype(int)
    except ValueError:
        # Pocos valores distintos: usa rango normalizado.
        normalized = (series.rank(pct=True) * 4 + 1).round().astype(int)
        scores = normalized.clip(1, 5)
    if reverse:
        scores = 6 - scores
    return scores


def _segment(r: int, f: int, m: int) -> str:
    """Deriva un segmento de negocio a partir de las puntuaciones RFM."""
    if r >= 4 and f >= 4 and m >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 2:
        return "New Customers"
    if r >= 3 and m >= 4:
        return "Potential Loyalist"
    if r <= 2 and f >= 3 and m >= 3:
        return "At Risk"
    if r <= 2 and f >= 4 and m >= 4:
        return "Can't Lose Them"
    if r <= 2 and f <= 2:
        return "Hibernating"
    if r <= 1:
        return "Lost"
    return "Need Attention"


__all__ = ["rfm_segmentation"]
