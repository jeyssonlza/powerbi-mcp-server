"""Tests para detección de anomalías (Isolation Forest, Z-Score, IQR)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.anomaly import detect_anomalies


class TestAnomalyDetection:
    """Suite de tests para detección de anomalías."""

    def test_isolation_forest_detects_outliers(self, sample_numeric_data: pd.DataFrame) -> None:
        """Isolation Forest debe detectar outliers inyectados.

        El dataset tiene outliers en Feature1[0]=500 y Feature3[5]=-200.
        """
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4", "Feature5"],
            method="isolation_forest",
            contamination=0.1,
        )

        assert result.ok
        assert result.model_type == "anomaly_detection"
        assert result.anomalies is not None
        # Los índices 0 y 5 deben estar marcados como anomalías
        assert 0 in result.anomalies.get("anomaly_indices", [])
        assert 5 in result.anomalies.get("anomaly_indices", [])

    def test_isolation_forest_with_csv_path(
        self, sample_csv_file: pd.DataFrame
    ) -> None:
        """Debe aceptar path a archivo CSV."""
        result = detect_anomalies(
            str(sample_csv_file),
            columns=["Amount", "Quantity"],
            method="isolation_forest",
        )
        assert result.ok
        assert result.model_type == "anomaly_detection"

    def test_zscore_method_detects_outliers(self, sample_numeric_data: pd.DataFrame) -> None:
        """Z-Score debe detectar puntos fuera de ±3σ."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1"],
            method="zscore",
        )
        assert result.ok
        assert result.anomalies is not None
        # Feature1[0]=500 está muy fuera de la distribución
        assert len(result.anomalies.get("anomaly_indices", [])) > 0

    def test_iqr_method_detects_outliers(self, sample_numeric_data: pd.DataFrame) -> None:
        """IQR (Interquartile Range) debe detectar outliers."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            method="iqr",
        )
        assert result.ok
        assert result.anomalies is not None

    def test_autodetect_numeric_columns(self, sample_sales_data: pd.DataFrame) -> None:
        """Debe autodetectar columnas numéricas sin especificar."""
        result = detect_anomalies(
            sample_sales_data,
            columns=None,  # Autodetectar
            method="isolation_forest",
        )
        assert result.ok
        # Debe detectar Amount y Quantity como numéricas
        assert result.anomalies is not None

    def test_contamination_parameter_affects_detection(
        self, sample_numeric_data: pd.DataFrame
    ) -> None:
        """Contamination mayor debe detectar más anomalías."""
        result_low = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1"],
            method="isolation_forest",
            contamination=0.05,
        )
        result_high = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1"],
            method="isolation_forest",
            contamination=0.2,
        )

        count_low = len(result_low.anomalies.get("anomaly_indices", []))
        count_high = len(result_high.anomalies.get("anomaly_indices", []))
        assert count_high >= count_low

    @pytest.mark.parametrize("method", ["isolation_forest", "zscore", "iqr"])
    def test_all_methods_return_valid_result(
        self, sample_numeric_data: pd.DataFrame, method: str
    ) -> None:
        """Todos los métodos deben devolver resultados válidos."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            method=method,
        )
        assert result.ok
        assert result.model_type == "anomaly_detection"
        assert hasattr(result, "anomalies")
        assert hasattr(result, "to_dict")

    def test_empty_dataframe_handling(self) -> None:
        """Debe manejar DataFrames vacías sin fallar críticamente."""
        empty_df = pd.DataFrame({"A": [], "B": []})
        # Podría fallar o devolver resultado vacío, ambos son aceptables
        try:
            result = detect_anomalies(empty_df, method="isolation_forest")
            assert result is not None
        except (ValueError, RuntimeError):
            # Excepción esperada para input vacío
            pass

    def test_single_column_detection(self, sample_numeric_data: pd.DataFrame) -> None:
        """Debe funcionar con una sola columna."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1"],
            method="zscore",
        )
        assert result.ok

    def test_result_serialization(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe ser serializable a diccionario."""
        result = detect_anomalies(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            method="isolation_forest",
        )
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "anomalies" in result_dict
        assert "model_type" in result_dict
