"""Tests para análisis de calidad de datos.

Valida el contrato real de ``analyze_data_quality`` -> dict con ``quality_score``
(0-100), ``findings`` accionables y ``columns_detail`` por columna.
"""

from __future__ import annotations

import pandas as pd

from powerbi_mcp.analysis.data_quality import analyze_data_quality


class TestDataQuality:
    """Suite de tests para análisis de calidad."""

    def test_report_structure(self, sample_quality_data: pd.DataFrame) -> None:
        """El reporte debe contener las claves estándar."""
        result = analyze_data_quality(sample_quality_data)
        for key in (
            "rows",
            "columns",
            "duplicated_rows",
            "completeness_pct",
            "uniqueness_pct",
            "quality_score",
            "findings",
            "columns_detail",
        ):
            assert key in result

    def test_quality_score_in_range(self, sample_sales_data: pd.DataFrame) -> None:
        """La puntuación de calidad debe estar entre 0 y 100."""
        result = analyze_data_quality(sample_sales_data)
        assert 0 <= result["quality_score"] <= 100

    def test_row_and_column_counts(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe reportar el número correcto de filas y columnas."""
        result = analyze_data_quality(sample_quality_data)
        assert result["rows"] == len(sample_quality_data)
        assert result["columns"] == sample_quality_data.shape[1]

    def test_detects_age_outlier(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe detectar el outlier Age=999 en el detalle de columnas."""
        result = analyze_data_quality(sample_quality_data, outlier_factor=1.5)
        age_detail = next(c for c in result["columns_detail"] if c["name"] == "Age")
        assert age_detail["outlier_count"] >= 1

    def test_detects_nulls_in_column_detail(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe contabilizar nulos por columna."""
        result = analyze_data_quality(sample_quality_data)
        age_detail = next(c for c in result["columns_detail"] if c["name"] == "Age")
        assert age_detail["null_count"] >= 1

    def test_findings_generated_for_problematic_data(
        self, sample_quality_data: pd.DataFrame
    ) -> None:
        """Datos problemáticos deben generar al menos un hallazgo."""
        result = analyze_data_quality(sample_quality_data)
        assert isinstance(result["findings"], list)
        assert len(result["findings"]) >= 1

    def test_clean_data_scores_higher_than_problematic(
        self, sample_sales_data: pd.DataFrame, sample_quality_data: pd.DataFrame
    ) -> None:
        """Datos limpios deben puntuar más alto que datos problemáticos."""
        clean = analyze_data_quality(sample_sales_data)["quality_score"]
        dirty = analyze_data_quality(sample_quality_data)["quality_score"]
        assert clean >= dirty

    def test_completeness_for_clean_data(self, sample_sales_data: pd.DataFrame) -> None:
        """Datos sin nulos deben tener completitud cercana al 100%."""
        result = analyze_data_quality(sample_sales_data)
        assert result["completeness_pct"] == 100.0

    def test_works_with_csv_input(self, sample_csv_file) -> None:
        """Debe aceptar una ruta a CSV como entrada."""
        result = analyze_data_quality(str(sample_csv_file))
        assert "quality_score" in result

    def test_outlier_factor_parameter(self, sample_quality_data: pd.DataFrame) -> None:
        """Un outlier_factor más bajo debe detectar al menos tantos outliers."""
        strict = analyze_data_quality(sample_quality_data, outlier_factor=1.0)
        lax = analyze_data_quality(sample_quality_data, outlier_factor=3.0)
        age_strict = next(c for c in strict["columns_detail"] if c["name"] == "Age")
        age_lax = next(c for c in lax["columns_detail"] if c["name"] == "Age")
        assert age_strict["outlier_count"] >= age_lax["outlier_count"]
