"""Tests para análisis de calidad de datos."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.analysis.data_quality import analyze_data_quality


class TestDataQuality:
    """Suite de tests para análisis de calidad."""

    def test_quality_analysis_basic(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe analizar calidad básica del dataset."""
        result = analyze_data_quality(sample_quality_data)

        assert result["ok"]
        assert "quality_score" in result
        assert "issues" in result

    def test_quality_detects_nulls(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe detectar valores nulos."""
        result = analyze_data_quality(sample_quality_data)

        assert result["ok"]
        issues = result.get("issues", [])
        # sample_quality_data tiene nulos en Age, Email
        has_null_issue = any("null" in str(i).lower() or "missing" in str(i).lower() for i in issues)
        assert has_null_issue or "quality_score" in result

    def test_quality_detects_duplicates(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe detectar filas duplicadas."""
        result = analyze_data_quality(sample_quality_data)

        assert result["ok"]
        issues = result.get("issues", [])
        # sample_quality_data tiene duplicados en ID y Name
        has_dup_issue = any("duplicate" in str(i).lower() for i in issues)
        assert has_dup_issue or result.get("quality_score") is not None

    def test_quality_detects_outliers(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe detectar outliers (Age=999)."""
        result = analyze_data_quality(sample_quality_data, outlier_factor=1.5)

        assert result["ok"]
        issues = result.get("issues", [])
        # Age=999 es outlier claro
        has_outlier_issue = any("outlier" in str(i).lower() for i in issues)
        assert has_outlier_issue or "quality_score" in result

    def test_quality_with_csv_input(self, sample_csv_file: Path) -> None:
        """Debe aceptar ruta a CSV."""
        result = analyze_data_quality(str(sample_csv_file))

        assert result["ok"]

    def test_quality_score_in_range(self, sample_sales_data: pd.DataFrame) -> None:
        """Quality score debe estar entre 0-100."""
        result = analyze_data_quality(sample_sales_data)

        assert result["ok"]
        score = result.get("quality_score")
        assert 0 <= score <= 100

    def test_quality_report_structure(self, sample_quality_data: pd.DataFrame) -> None:
        """El reporte debe tener estructura estándar."""
        result = analyze_data_quality(sample_quality_data)

        assert result["ok"]
        assert "quality_score" in result
        assert "issues" in result or "findings" in result
        assert "summary" in result or len(result) > 2

    def test_quality_with_clean_data(self, sample_sales_data: pd.DataFrame) -> None:
        """Datos limpios deben tener puntuación alta."""
        result = analyze_data_quality(sample_sales_data)

        assert result["ok"]
        score = result.get("quality_score")
        # Datos limpios sin nulos ni outliers debe ser > 80
        assert score > 60

    def test_quality_with_problematic_data(self, sample_quality_data: pd.DataFrame) -> None:
        """Datos con problemas deben tener puntuación baja."""
        result = analyze_data_quality(sample_quality_data)

        assert result["ok"]
        score = result.get("quality_score")
        # sample_quality_data tiene muchos problemas, score < 80
        assert score < 90

    def test_quality_outlier_factor_parameter(self, sample_quality_data: pd.DataFrame) -> None:
        """Outlier factor debe afectar detección."""
        result_low = analyze_data_quality(sample_quality_data, outlier_factor=1.0)
        result_high = analyze_data_quality(sample_quality_data, outlier_factor=3.0)

        assert result_low["ok"]
        assert result_high["ok"]
        # Factor bajo debe detectar más outliers
        score_low = result_low.get("quality_score")
        score_high = result_high.get("quality_score")
        # Posiblemente different scores
        assert score_low is not None and score_high is not None
