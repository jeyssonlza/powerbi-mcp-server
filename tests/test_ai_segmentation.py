"""Tests para segmentación RFM (Recency, Frequency, Monetary).

Valida el contrato real de ``rfm_segmentation`` -> ``AIResult`` con una fila por
cliente que incluye ``recency``, ``frequency``, ``monetary``, sus puntuaciones
(``R_score``, ``F_score``, ``M_score``) y el ``segment`` asignado.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.rfm import rfm_segmentation
from powerbi_mcp.core.exceptions import ValidationError


class TestRFMSegmentation:
    """Suite de tests para segmentación RFM."""

    def test_basic_segmentation(self, sample_rfm_data: pd.DataFrame) -> None:
        """Debe producir una fila por cliente único."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        assert result.model_type == "rfm"
        n_customers = sample_rfm_data["CustomerID"].nunique()
        assert len(result.table) == n_customers
        assert result.summary["customers"] == n_customers

    def test_rows_have_rfm_components(self, sample_rfm_data: pd.DataFrame) -> None:
        """Cada cliente debe tener recency, frequency, monetary y scores."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        row = result.table[0]
        for key in ("recency", "frequency", "monetary", "R_score", "F_score", "M_score", "segment"):
            assert key in row

    def test_scores_in_range(self, sample_rfm_data: pd.DataFrame) -> None:
        """Las puntuaciones R/F/M deben estar entre 1 y 5."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        for row in result.table:
            assert 1 <= row["R_score"] <= 5
            assert 1 <= row["F_score"] <= 5
            assert 1 <= row["M_score"] <= 5

    def test_segment_distribution_in_summary(self, sample_rfm_data: pd.DataFrame) -> None:
        """El summary debe incluir la distribución de segmentos."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        dist = result.summary["segment_distribution"]
        assert sum(dist.values()) == result.summary["customers"]

    def test_averages_in_summary(self, sample_rfm_data: pd.DataFrame) -> None:
        """El summary debe reportar promedios de recency/frequency/monetary."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        assert "avg_recency" in result.summary
        assert "avg_frequency" in result.summary
        assert "avg_monetary" in result.summary

    def test_aggregates_multiple_transactions(self, sample_rfm_data: pd.DataFrame) -> None:
        """Duplicar transacciones no debe cambiar el número de clientes."""
        doubled = pd.concat([sample_rfm_data, sample_rfm_data], ignore_index=True)
        result = rfm_segmentation(
            doubled,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        assert len(result.table) == sample_rfm_data["CustomerID"].nunique()

    def test_reference_date_override(self, sample_rfm_data: pd.DataFrame) -> None:
        """Una fecha de referencia explícita debe reflejarse en el summary."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
            reference_date="2024-01-01",
        )
        assert result.summary["reference_date"].startswith("2024-01-01")

    def test_missing_column_raises(self, sample_rfm_data: pd.DataFrame) -> None:
        """Una columna inexistente debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            rfm_segmentation(
                sample_rfm_data,
                customer_column="NoExiste",
                date_column="TransactionDate",
                amount_column="Amount",
            )

    def test_result_serializable(self, sample_rfm_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "rfm"
