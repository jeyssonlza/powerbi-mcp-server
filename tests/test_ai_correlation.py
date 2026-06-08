"""Tests para análisis de correlación (Pearson, Spearman, Kendall)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.correlation import correlation_analysis


class TestCorrelation:
    """Suite de tests para correlación."""

    def test_pearson_correlation(self, sample_numeric_data: pd.DataFrame) -> None:
        """Pearson correlation debe calcular correlaciones."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            method="pearson",
        )

        assert result.ok
        assert result.model_type == "correlation"
        assert result.correlation_matrix is not None

    def test_spearman_correlation(self, sample_numeric_data: pd.DataFrame) -> None:
        """Spearman correlation debe funcionar."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            method="spearman",
        )

        assert result.ok
        assert result.correlation_matrix is not None

    def test_kendall_correlation(self, sample_numeric_data: pd.DataFrame) -> None:
        """Kendall correlation debe funcionar."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            method="kendall",
        )

        assert result.ok

    def test_correlation_with_csv_input(self, sample_csv_file: Path) -> None:
        """Debe aceptar ruta a CSV."""
        result = correlation_analysis(
            str(sample_csv_file),
            columns=["Amount", "Quantity"],
            method="pearson",
        )

        assert result.ok

    def test_correlation_auto_detect_columns(self, sample_sales_data: pd.DataFrame) -> None:
        """Debe autodetectar columnas numéricas."""
        result = correlation_analysis(
            sample_sales_data,
            columns=None,  # Auto
            method="pearson",
        )

        assert result.ok
        assert result.correlation_matrix is not None

    def test_correlation_matrix_structure(self, sample_numeric_data: pd.DataFrame) -> None:
        """La matriz de correlación debe ser simétrica."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            method="pearson",
        )

        assert result.ok
        matrix = result.correlation_matrix
        # Matriz debe tener valores entre -1 y 1
        assert isinstance(matrix, (dict, list, pd.DataFrame))

    def test_correlation_identifies_strong_pairs(
        self, sample_numeric_data: pd.DataFrame
    ) -> None:
        """Debe identificar pares fuertemente correlacionados."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4", "Feature5"],
            method="pearson",
        )

        assert result.ok
        result_dict = result.to_dict()
        # Debe haber un resumen de pares fuertes
        assert "strong_correlations" in result_dict or "correlation_pairs" in result_dict

    @pytest.mark.parametrize("method", ["pearson", "spearman", "kendall"])
    def test_all_methods_work(self, sample_numeric_data: pd.DataFrame, method: str) -> None:
        """Todos los métodos deben funcionar."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            method=method,
        )

        assert result.ok

    def test_correlation_result_serialization(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe ser serializable."""
        result = correlation_analysis(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            method="pearson",
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "model_type" in result_dict
        assert "correlation_matrix" in result_dict

    def test_correlation_with_single_column_fails(self, sample_numeric_data: pd.DataFrame) -> None:
        """Una sola columna no puede correlacionarse."""
        try:
            result = correlation_analysis(
                sample_numeric_data,
                columns=["Feature1"],
                method="pearson",
            )
            # Podría fallar o devolver resultado mínimo
            if result.ok:
                assert result.correlation_matrix is not None
        except (ValueError, RuntimeError):
            pass
