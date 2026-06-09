"""Tests para regresión (lineal y random forest).

Valida el contrato real de ``train_regression`` -> ``AIResult`` cuyo ``summary``
incluye ``metrics`` (``r2``, ``mae``, ``rmse``) y ``feature_importance``, y cuyo
``table`` es la importancia/coeficientes por variable.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.regression import VALID_ALGORITHMS, train_regression
from powerbi_mcp.core.exceptions import ValidationError


class TestRegression:
    """Suite de tests para regresión."""

    def test_linear_returns_metrics(self, sample_numeric_data: pd.DataFrame) -> None:
        """La regresión lineal debe entrenar y reportar métricas r2/mae/rmse."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="linear",
        )
        assert result.model_type == "regression"
        metrics = result.summary["metrics"]
        assert "r2" in metrics
        assert "mae" in metrics
        assert "rmse" in metrics

    def test_metrics_non_negative(self, sample_numeric_data: pd.DataFrame) -> None:
        """MAE y RMSE deben ser no negativos."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="linear",
        )
        assert result.summary["metrics"]["mae"] >= 0
        assert result.summary["metrics"]["rmse"] >= 0

    def test_random_forest_works(self, sample_numeric_data: pd.DataFrame) -> None:
        """Random Forest debe entrenar correctamente."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3"],
            algorithm="random_forest",
        )
        assert result.summary["algorithm"] == "random_forest"

    def test_feature_importance_present(self, sample_numeric_data: pd.DataFrame) -> None:
        """Debe incluir una fila de importancia por feature."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="random_forest",
        )
        assert len(result.table) == 4
        for row in result.table:
            assert "feature" in row
            assert "value" in row

    def test_auto_detect_features(self, sample_numeric_data: pd.DataFrame) -> None:
        """Sin feature_columns, debe usar todas las demás columnas."""
        result = train_regression(
            sample_numeric_data, target_column="Feature5", algorithm="linear"
        )
        assert result.summary["n_features"] == 4

    def test_summary_reports_target_and_samples(self, sample_numeric_data: pd.DataFrame) -> None:
        """El summary debe reportar el objetivo y el número de muestras."""
        result = train_regression(
            sample_numeric_data, target_column="Feature5", algorithm="linear"
        )
        assert result.summary["target"] == "Feature5"
        assert result.summary["n_samples"] == len(sample_numeric_data)

    @pytest.mark.parametrize("algorithm", ["linear", "random_forest"])
    def test_all_algorithms_work(
        self, sample_numeric_data: pd.DataFrame, algorithm: str
    ) -> None:
        """Ambos algoritmos deben funcionar."""
        result = train_regression(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2"],
            algorithm=algorithm,
        )
        assert result.model_type == "regression"

    def test_invalid_algorithm_raises(self, sample_numeric_data: pd.DataFrame) -> None:
        """Un algoritmo no soportado debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            train_regression(sample_numeric_data, target_column="Feature5", algorithm="svm")

    def test_missing_target_raises(self, sample_numeric_data: pd.DataFrame) -> None:
        """Una columna objetivo inexistente debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            train_regression(sample_numeric_data, target_column="NoExiste", algorithm="linear")

    def test_result_serializable(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario con métricas."""
        result = train_regression(
            sample_numeric_data, target_column="Feature5", algorithm="linear"
        )
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "regression"
        assert "metrics" in as_dict["metadata"]

    def test_valid_algorithms_constant(self) -> None:
        """La constante VALID_ALGORITHMS debe contener los dos algoritmos."""
        assert {"linear", "random_forest"} == VALID_ALGORITHMS
