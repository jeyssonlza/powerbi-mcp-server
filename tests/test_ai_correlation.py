"""Tests para análisis de correlación (Pearson, Spearman, Kendall).

Valida el contrato real de ``correlation_analysis`` -> ``AIResult`` cuyo
``table`` es la matriz en formato largo (``var1``, ``var2``, ``correlation``) y
cuyo ``summary`` incluye ``strong_pairs`` y ``multicollinearity_warning``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.correlation import VALID_METHODS, correlation_analysis
from powerbi_mcp.core.exceptions import ValidationError


class TestCorrelation:
    """Suite de tests para correlación."""

    def test_pearson_returns_valid_result(self, sample_numeric_data: pd.DataFrame) -> None:
        """Pearson debe devolver la matriz en formato largo."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            method="pearson",
        )
        assert result.model_type == "correlation"
        assert result.summary["method"] == "pearson"
        assert result.columns == ["var1", "var2", "correlation"]
        # 3 variables -> 3x3 = 9 pares (incluida la diagonal).
        assert len(result.table) == 9

    def test_correlation_values_in_range(self, sample_numeric_data: pd.DataFrame) -> None:
        """Todos los valores de correlación deben estar entre -1 y 1."""
        result = correlation_analysis(
            sample_numeric_data, columns=["Feature1", "Feature2", "Feature3"], method="pearson"
        )
        for row in result.table:
            assert -1.0 <= row["correlation"] <= 1.0

    def test_diagonal_is_one(self, sample_numeric_data: pd.DataFrame) -> None:
        """La correlación de una variable consigo misma debe ser 1."""
        result = correlation_analysis(
            sample_numeric_data, columns=["Feature1", "Feature2"], method="pearson"
        )
        for row in result.table:
            if row["var1"] == row["var2"]:
                assert row["correlation"] == pytest.approx(1.0)

    def test_detects_strong_correlation(self) -> None:
        """Debe detectar un par fuertemente correlacionado y advertir colinealidad."""
        # y = 2x => correlación perfecta.
        data = {"x": list(range(20)), "y": [2 * i for i in range(20)], "z": [i % 3 for i in range(20)]}
        result = correlation_analysis(data, method="pearson", strong_threshold=0.7)
        assert result.summary["multicollinearity_warning"] is True
        assert len(result.summary["strong_pairs"]) >= 1

    @pytest.mark.parametrize("method", ["pearson", "spearman", "kendall"])
    def test_all_methods_work(self, sample_numeric_data: pd.DataFrame, method: str) -> None:
        """Los tres métodos deben funcionar."""
        result = correlation_analysis(
            sample_numeric_data, columns=["Feature1", "Feature2"], method=method
        )
        assert result.summary["method"] == method

    def test_invalid_method_raises(self, sample_numeric_data: pd.DataFrame) -> None:
        """Un método no soportado debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            correlation_analysis(sample_numeric_data, method="invalid")

    def test_auto_detect_columns(self, sample_numeric_data: pd.DataFrame) -> None:
        """Sin columnas, debe autodetectar las 5 numéricas."""
        result = correlation_analysis(sample_numeric_data, method="pearson")
        assert len(result.summary["variables"]) == 5

    def test_works_with_csv_input(self, sample_csv_file) -> None:
        """Debe aceptar una ruta a CSV como entrada."""
        result = correlation_analysis(
            str(sample_csv_file), columns=["Amount", "Quantity"], method="pearson"
        )
        assert result.model_type == "correlation"

    def test_strong_pairs_sorted(self) -> None:
        """Los pares fuertes deben venir ordenados por |correlación| descendente."""
        data = {
            "a": list(range(30)),
            "b": [2 * i for i in range(30)],
            "c": [-i for i in range(30)],
        }
        result = correlation_analysis(data, method="pearson", strong_threshold=0.5)
        corrs = [abs(p["correlation"]) for p in result.summary["strong_pairs"]]
        assert corrs == sorted(corrs, reverse=True)

    def test_result_serializable(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario."""
        result = correlation_analysis(
            sample_numeric_data, columns=["Feature1", "Feature2"], method="pearson"
        )
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "correlation"

    def test_valid_methods_constant(self) -> None:
        """La constante VALID_METHODS debe contener los tres métodos."""
        assert {"pearson", "spearman", "kendall"} == VALID_METHODS
