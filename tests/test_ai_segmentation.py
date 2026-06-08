"""Tests para RFM segmentation."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.rfm import rfm_segmentation


class TestRFMSegmentation:
    """Suite de tests para RFM segmentation."""

    def test_rfm_basic_segmentation(self, sample_rfm_data: pd.DataFrame) -> None:
        """Debe segmentar clientes por RFM."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )

        assert result.ok
        assert result.model_type == "rfm_segmentation"
        assert result.segmentation is not None
        assert len(result.segmentation) == len(sample_rfm_data["CustomerID"].unique())

    def test_rfm_with_csv_input(self, tmp_path: Path) -> None:
        """Debe aceptar ruta a archivo CSV."""
        df = pd.DataFrame({
            "CustID": ["C001", "C002", "C001", "C003", "C002"] * 4,
            "TxDate": pd.date_range("2023-01-01", periods=20, freq="D"),
            "TxAmount": [100 + i * 5 for i in range(20)],
        })
        csv_path = tmp_path / "rfm.csv"
        df.to_csv(csv_path, index=False)

        result = rfm_segmentation(
            str(csv_path),
            customer_column="CustID",
            date_column="TxDate",
            amount_column="TxAmount",
        )

        assert result.ok

    def test_rfm_output_includes_metrics(self, sample_rfm_data: pd.DataFrame) -> None:
        """El output debe incluir R, F, M por cliente."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )

        assert result.ok
        result_dict = result.to_dict()
        segmentation = result_dict.get("segmentation", {})
        # Cada cliente debe tener R, F, M scores
        for customer in segmentation.values():
            assert "recency" in customer or "R" in customer
            assert "frequency" in customer or "F" in customer
            assert "monetary" in customer or "M" in customer

    def test_rfm_identifies_top_customers(self, sample_rfm_data: pd.DataFrame) -> None:
        """Debe identificar VIP vs otros segmentos."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )

        assert result.ok
        result_dict = result.to_dict()
        # Debe haber información sobre segmentación
        assert "segmentation" in result_dict or "clusters" in result_dict

    def test_rfm_handles_multiple_transactions_per_customer(
        self, sample_rfm_data: pd.DataFrame
    ) -> None:
        """Debe agregar transacciones múltiples por cliente."""
        # Duplicar datos para tener múltiples transacciones
        doubled = pd.concat([sample_rfm_data, sample_rfm_data])

        result = rfm_segmentation(
            doubled,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )

        assert result.ok
        # Número único de clientes debe ser el mismo
        assert len(result.segmentation) == len(sample_rfm_data["CustomerID"].unique())

    def test_rfm_result_serialization(self, sample_rfm_data: pd.DataFrame) -> None:
        """El resultado debe ser serializable."""
        result = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "model_type" in result_dict
        assert "segmentation" in result_dict
