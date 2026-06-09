"""Tests para árboles de decisión explicativos (key influencers).

Valida el contrato real de ``decision_tree_explain`` -> ``AIResult`` cuyo
``summary`` incluye ``task``, ``score``, ``top_influencers`` y ``rules``, y cuyo
``table`` es la importancia de variables.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.decision_tree import decision_tree_explain
from powerbi_mcp.core.exceptions import ValidationError


class TestDecisionTree:
    """Suite de tests para árboles de decisión."""

    def test_classification_task(self, sample_classification_data: pd.DataFrame) -> None:
        """Con objetivo categórico debe resolver una tarea de clasificación."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )
        assert result.model_type == "decision_tree"
        assert result.summary["task"] == "classification"
        assert result.summary["score_metric"] == "accuracy"

    def test_feature_importance_table(self, sample_classification_data: pd.DataFrame) -> None:
        """El table debe tener importancia por feature."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )
        assert result.columns == ["feature", "importance"]
        assert len(result.table) >= 1

    def test_rules_generated(self, sample_classification_data: pd.DataFrame) -> None:
        """El summary debe incluir reglas legibles del árbol."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            max_depth=2,
        )
        assert isinstance(result.summary["rules"], list)
        assert len(result.summary["rules"]) >= 1

    def test_top_influencers_present(self, sample_classification_data: pd.DataFrame) -> None:
        """El summary debe incluir los principales influenciadores."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )
        assert len(result.summary["top_influencers"]) <= 5
        assert len(result.summary["top_influencers"]) >= 1

    def test_numeric_target_is_regression(self, sample_numeric_data: pd.DataFrame) -> None:
        """Un objetivo numérico continuo debe resolverse como regresión."""
        result = decision_tree_explain(
            sample_numeric_data,
            target_column="Feature5",
            feature_columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            max_depth=3,
        )
        assert result.summary["task"] == "regression"
        assert result.summary["score_metric"] == "r2"

    @pytest.mark.parametrize("depth", [1, 2, 3, 5])
    def test_different_depths(
        self, sample_classification_data: pd.DataFrame, depth: int
    ) -> None:
        """Diferentes profundidades deben funcionar."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2", "Feature3"],
            max_depth=depth,
        )
        assert result.summary["max_depth"] == depth

    def test_missing_target_raises(self, sample_classification_data: pd.DataFrame) -> None:
        """Una columna objetivo inexistente debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            decision_tree_explain(sample_classification_data, target_column="NoExiste")

    def test_result_serializable(self, sample_classification_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario."""
        result = decision_tree_explain(
            sample_classification_data,
            target_column="Class",
            feature_columns=["Feature1", "Feature2"],
            max_depth=2,
        )
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "decision_tree"
