"""Tests para clasificación (Logistic, Random Forest).

Valida el contrato real de ``train_classification`` -> ``AIResult`` cuyo
``summary`` incluye ``metrics`` (``accuracy``, ``precision``, ``recall``,
``f1``), ``confusion_matrix`` y ``classes``, y cuyo ``table`` es la importancia
de variables.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.classification import VALID_ALGORITHMS, train_classification
from powerbi_mcp.core.exceptions import ValidationError


class TestClassification:
    """Suite de tests para clasificación."""

    def test_logistic_returns_metrics(self, sample_classification_data: pd.DataFrame) -> None:
        """La regresión logística debe clasificar y reportar métricas."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="logistic",
        )
        assert result.model_type == "classification"
        metrics = result.summary["metrics"]
        assert {"accuracy", "precision", "recall", "f1"} <= set(metrics)

    def test_metrics_in_valid_range(self, sample_classification_data: pd.DataFrame) -> None:
        """Las métricas deben estar entre 0 y 1."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="random_forest",
        )
        for key in ("accuracy", "precision", "recall", "f1"):
            assert 0.0 <= result.summary["metrics"][key] <= 1.0

    def test_classes_detected(self, sample_classification_data: pd.DataFrame) -> None:
        """Debe reportar las clases del objetivo (A y B)."""
        result = train_classification(
            sample_classification_data, target_column="Class", algorithm="random_forest"
        )
        assert set(result.summary["classes"]) == {"A", "B"}

    def test_confusion_matrix_present(self, sample_classification_data: pd.DataFrame) -> None:
        """El summary debe incluir una matriz de confusión cuadrada."""
        result = train_classification(
            sample_classification_data, target_column="Class", algorithm="random_forest"
        )
        cm = result.summary["confusion_matrix"]
        assert len(cm) == len(cm[0])  # cuadrada

    def test_feature_importance_table(self, sample_classification_data: pd.DataFrame) -> None:
        """El table debe tener una fila de importancia por feature."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="random_forest",
        )
        assert result.columns == ["feature", "importance"]
        assert len(result.table) == 4

    def test_auto_detect_features(self, sample_classification_data: pd.DataFrame) -> None:
        """Sin feature_columns, debe usar las demás columnas."""
        result = train_classification(
            sample_classification_data, target_column="Class", algorithm="logistic"
        )
        assert result.summary["n_samples"] == len(sample_classification_data)

    @pytest.mark.parametrize("algorithm", ["logistic", "random_forest"])
    def test_all_algorithms_work(
        self, sample_classification_data: pd.DataFrame, algorithm: str
    ) -> None:
        """Ambos algoritmos deben funcionar."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            algorithm=algorithm,
        )
        assert result.model_type == "classification"

    def test_invalid_algorithm_raises(self, sample_classification_data: pd.DataFrame) -> None:
        """Un algoritmo no soportado debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            train_classification(
                sample_classification_data, target_column="Class", algorithm="svm"
            )

    def test_single_class_raises(self) -> None:
        """Un objetivo con una sola clase debe lanzar ValidationError."""
        df = pd.DataFrame({
            "Feature1": list(range(20)),
            "Feature2": list(range(20, 40)),
            "Class": ["A"] * 20,
        })
        with pytest.raises(ValidationError):
            train_classification(df, target_column="Class", algorithm="logistic")

    def test_result_serializable(self, sample_classification_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario con métricas."""
        result = train_classification(
            sample_classification_data, target_column="Class", algorithm="logistic"
        )
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "classification"
        assert "metrics" in as_dict["metadata"]

    def test_valid_algorithms_constant(self) -> None:
        """La constante VALID_ALGORITHMS debe contener los dos algoritmos."""
        assert {"logistic", "random_forest"} == VALID_ALGORITHMS
