"""Tests para detección de anomalías (Isolation Forest, Z-Score, IQR).

Valida el contrato real de ``detect_anomalies`` -> ``AIResult`` con campos
``model_type``, ``summary``, ``table``, ``columns`` y ``metadata``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.anomaly import VALID_METHODS, detect_anomalies
from powerbi_mcp.core.exceptions import ValidationError


class TestAnomalyDetection:
    """Suite de tests para detección de anomalías."""

    def test_isolation_forest_returns_valid_result(
        self, sample_numeric_data: pd.DataFrame
    ) -> None:
        """Isolation Forest debe devolver un AIResult con el contrato esperado."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4", "Feature5"],
            method="isolation_forest",
            contamination=0.1,
        )

        assert result.model_type == "anomaly"
        assert result.summary["method"] == "isolation_forest"
        assert result.summary["total_rows"] == len(sample_numeric_data)
        assert result.summary["anomalies_detected"] >= 1
        assert "is_anomaly" in result.columns
        assert "anomaly_score" in result.columns
        assert len(result.table) == len(sample_numeric_data)

    def test_isolation_forest_detects_injected_outliers(
        self, sample_numeric_data: pd.DataFrame
    ) -> None:
        """Debe marcar como anómala al menos una fila con outliers (índice 0 o 5)."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4", "Feature5"],
            method="isolation_forest",
            contamination=0.1,
        )
        flags = [row["is_anomaly"] for row in result.table]
        # Las filas 0 (Feature1=500) y 5 (Feature3=-200) son outliers inyectados.
        assert flags[0] or flags[5]

    def test_zscore_detects_extreme_value(self, sample_numeric_data: pd.DataFrame) -> None:
        """Z-Score debe marcar el valor extremo 500 (z muy alto) como anomalía."""
        result = detect_anomalies(
            sample_numeric_data,
            method="zscore",
            zscore_threshold=3.0,
        )
        assert result.summary["method"] == "zscore"
        assert result.table[0]["is_anomaly"] is True  # Feature1[0] = 500

    def test_iqr_method_runs(self, sample_numeric_data: pd.DataFrame) -> None:
        """El método IQR debe ejecutarse y producir un resultado válido."""
        result = detect_anomalies(sample_numeric_data, method="iqr", iqr_factor=1.5)
        assert result.summary["method"] == "iqr"
        assert result.summary["anomalies_detected"] >= 1

    def test_anomaly_score_is_numeric(self, sample_numeric_data: pd.DataFrame) -> None:
        """Cada fila debe tener un anomaly_score numérico."""
        result = detect_anomalies(sample_numeric_data, method="zscore")
        for row in result.table:
            assert isinstance(row["anomaly_score"], (int, float))

    def test_anomaly_rate_in_summary(self, sample_numeric_data: pd.DataFrame) -> None:
        """El summary debe reportar una tasa de anomalías entre 0 y 1."""
        result = detect_anomalies(sample_numeric_data, method="iqr")
        assert 0.0 <= result.summary["anomaly_rate"] <= 1.0

    def test_invalid_method_raises(self, sample_numeric_data: pd.DataFrame) -> None:
        """Un método no soportado debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            detect_anomalies(sample_numeric_data, method="not_a_method")

    def test_auto_detect_numeric_columns(self, sample_numeric_data: pd.DataFrame) -> None:
        """Sin especificar columnas, debe autodetectar las numéricas."""
        result = detect_anomalies(sample_numeric_data, method="zscore")
        assert len(result.summary["columns_used"]) == 5

    def test_columns_used_reported(self, sample_numeric_data: pd.DataFrame) -> None:
        """Debe reportar las columnas usadas cuando se especifican."""
        result = detect_anomalies(
            sample_numeric_data, columns=["Feature1", "Feature2"], method="zscore"
        )
        assert result.summary["columns_used"] == ["Feature1", "Feature2"]

    def test_works_with_dict_input(self) -> None:
        """Debe aceptar un dict de columnas como entrada."""
        data = {"a": [1.0, 2, 3, 4, 5, 100], "b": [2.0, 3, 4, 5, 6, 7]}
        result = detect_anomalies(data, method="iqr")
        assert result.model_type == "anomaly"
        assert len(result.table) == 6

    def test_works_with_csv_input(self, sample_csv_file) -> None:
        """Debe aceptar una ruta a CSV como entrada."""
        result = detect_anomalies(
            str(sample_csv_file), columns=["Amount", "Quantity"], method="zscore"
        )
        assert result.model_type == "anomaly"

    def test_result_serializable(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario JSON-compatible."""
        result = detect_anomalies(sample_numeric_data, method="zscore")
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "anomaly"
        assert "table" in as_dict
        assert as_dict["row_count"] == len(sample_numeric_data)

    def test_valid_methods_constant(self) -> None:
        """La constante VALID_METHODS debe contener los tres métodos."""
        assert {"isolation_forest", "zscore", "iqr"} == VALID_METHODS
