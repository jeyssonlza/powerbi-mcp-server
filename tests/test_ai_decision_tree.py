"""Tests para decision trees (explicabilidad, feature importance)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.decision_tree import decision_tree_explain


class TestDecisionTree:
    """Suite de tests para decision trees."""

    def test_basic_decision_tree(self, sample_classification_data: pd.DataFrame) -> None:
        """Decision tree debe entrenar y explicar."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )

        assert result.ok
        assert result.model_type == "decision_tree"
        assert result.feature_importance is not None

    def test_decision_tree_with_csv_input(self, tmp_path: Path) -> None:
        """Debe aceptar ruta a CSV."""
        df = pd.DataFrame({
            "Feature1": [1, 2, 3, 4, 5] * 4,
            "Feature2": [10, 20, 30, 40, 50] * 4,
            "Target": ["A", "B", "A", "B", "A"] * 4,
        })
        csv_path = tmp_path / "tree.csv"
        df.to_csv(csv_path, index=False)

        result = decision_tree_explain(
            str(csv_path),
            target_column="Target",
            feature_columns=["Feature1", "Feature2"],
            max_depth=2,
        )

        assert result.ok

    def test_decision_tree_feature_importance(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Debe reportar importancia de features."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )

        assert result.ok
        importance = result.feature_importance
        # Cada feature debe tener un score
        assert len(importance) > 0

    def test_decision_tree_rules_generation(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Debe extraer reglas del árbol."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            max_depth=2,
        )

        assert result.ok
        result_dict = result.to_dict()
        # Debe tener reglas/paths
        assert "rules" in result_dict or "paths" in result_dict or "tree" in result_dict

    def test_decision_tree_auto_features(self, sample_classification_data: pd.DataFrame) -> None:
        """Debe autodetectar features."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=None,  # Auto
            max_depth=3,
        )

        assert result.ok

    def test_decision_tree_depth_parameter(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """Diferentes profundidades deben funcionar."""
        for depth in [1, 2, 3, 5]:
            result = decision_tree_explain(
                sample_classification_data,
                target_column="Class",
                feature_columns=["Feature1", "Feature2", "Feature3"],
                max_depth=depth,
            )
            assert result.ok

    def test_decision_tree_numeric_target(self, sample_numeric_data: pd.DataFrame) -> None:
        """Debe funcionar con targets numéricos (regresión)."""
        result = decision_tree_explain(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )

        assert result.ok

    def test_decision_tree_result_serialization(
        self, sample_classification_data: pd.DataFrame
    ) -> None:
        """El resultado debe ser serializable."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            max_depth=2,
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "model_type" in result_dict
        assert "feature_importance" in result_dict
