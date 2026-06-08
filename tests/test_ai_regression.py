"""Tests para regresión lineal y random forest."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.regression import train_regression


class TestRegression:
    """Suite de tests para regresión."""

    def test_linear_regression(self, sample_numeric_data: pd.DataFrame) -> None:
        """Linear regression debe entrenar y reportar métricas."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="linear",
        )

        assert result.ok
        assert result.model_type == "regression"
        assert result.metrics is not None
        assert "r2" in result.metrics or "r_squared" in result.metrics

    def test_random_forest_regression(self, sample_numeric_data: pd.DataFrame) -> None:
        """Random Forest regression debe funcionar."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3"],
            algorithm="random_forest",
        )

        assert result.ok
        assert result.model_type == "regression"

    def test_regression_with_csv_input(self, sample_csv_file: Path) -> None:
        """Debe aceptar ruta a CSV."""
        result = train_regression(
            str(sample_csv_file),
            target_column="Amount",
            feature_columns=["Quantity"],
            algorithm="linear",
        )

        assert result.ok

    def test_regression_auto_detect_features(self, sample_numeric_data: pd.DataFrame) -> None:
        """Debe autodetectar features si no se especifican."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=None,  # Auto
            algorithm="linear",
        )

        assert result.ok
        assert result.metrics is not None

    def test_regression_metrics_validity(self, sample_numeric_data: pd.DataFrame) -> None:
        """Las métricas deben estar en rango válido."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="linear",
        )

        assert result.ok
        metrics = result.metrics
        # R2 debe estar entre -inf y 1 (negativo es malo, pero posible)
        # MAE y RMSE deben ser >= 0
        r2 = metrics.get("r2") or metrics.get("r_squared")
        mae = metrics.get("mae") or metrics.get("mean_absolute_error")
        rmse = metrics.get("rmse") or metrics.get("root_mean_squared_error")

        assert mae is None or mae >= 0
        assert rmse is None or rmse >= 0

    def test_regression_feature_importance(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe incluir importancia de features."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="random_forest",
        )

        assert result.ok
        result_dict = result.to_dict()
        # Feature importance para random forest
        assert "feature_importance" in result_dict or "importance" in result_dict

    @pytest.mark.parametrize("algorithm", ["linear", "random_forest"])
    def test_all_algorithms_work(
        self, sample_numeric_data: pd.DataFrame, algorithm: str
    ) -> None:
        """Todos los algoritmos deben funcionar."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2"],
            algorithm=algorithm,
        )

        assert result.ok

    def test_regression_result_serialization(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe ser serializable."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2"],
            algorithm="linear",
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "model_type" in result_dict
        assert "metrics" in result_dict
