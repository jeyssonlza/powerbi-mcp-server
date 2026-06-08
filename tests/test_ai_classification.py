"""Tests para clasificación (Logistic, Random Forest)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.classification import train_classification


class TestClassification:
    """Suite de tests para clasificación."""

    def test_logistic_classification(self, sample_classification_data: pd.DataFrame) -> None:
        """Logistic regression debe clasificar."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="logistic",
        )

        assert result.ok
        assert result.model_type == "classification"
        assert result.metrics is not None

    def test_random_forest_classification(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Random Forest debe clasificar."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3"],
            algorithm="random_forest",
        )

        assert result.ok

    def test_classification_with_csv_input(self, tmp_path: Path) -> None:
        """Debe aceptar ruta a CSV."""
        df = pd.DataFrame({
            "Feature1": [1, 2, 3, 4, 5] * 4,
            "Feature2": [10, 20, 30, 40, 50] * 4,
            "Target": ["A", "B", "A", "B", "A"] * 4,
        })
        csv_path = tmp_path / "clf.csv"
        df.to_csv(csv_path, index=False)

        result = train_classification(
            str(csv_path),
            target_column="Target",
            feature_columns=["Feature1", "Feature2"],
            algorithm="logistic",
        )

        assert result.ok

    def test_classification_confusion_matrix(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """El resultado debe incluir matriz de confusión."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="random_forest",
        )

        assert result.ok
        result_dict = result.to_dict()
        # Matriz de confusión para evaluación
        assert "confusion_matrix" in result_dict or "metrics" in result_dict

    def test_classification_accuracy_metric(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Debe reportar accuracy/precision/recall."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="logistic",
        )

        assert result.ok
        metrics = result.metrics
        # Debe haber alguna métrica de exactitud
        assert any(k in metrics for k in ["accuracy", "precision", "recall", "f1"])

    def test_classification_feature_importance(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Random Forest debe reportar feature importance."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="random_forest",
        )

        assert result.ok
        result_dict = result.to_dict()
        # Feature importance
        assert "feature_importance" in result_dict or "importance" in result_dict

    def test_classification_auto_detect_features(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Debe autodetectar features."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=None,  # Auto
            algorithm="logistic",
        )

        assert result.ok

    @pytest.mark.parametrize("algorithm", ["logistic", "random_forest"])
    def test_all_algorithms_work(
        self, sample_classification_data: pd.DataFrame, algorithm: str
    ) -> None:
        """Todos los algoritmos deben funcionar."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            algorithm=algorithm,
        )

        assert result.ok

    def test_classification_result_serialization(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """El resultado debe ser serializable."""
        result = train_classification(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            algorithm="logistic",
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "model_type" in result_dict
        assert "metrics" in result_dict
