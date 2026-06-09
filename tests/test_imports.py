"""Tests rápidos para verificar que todos los imports funcionan sin errores circulares."""

from __future__ import annotations


class TestImports:
    """Verificar que los módulos se cargan correctamente."""

    def test_core_imports(self) -> None:
        """Core modules debe cargarse."""
        from powerbi_mcp.core.exceptions import PowerBIMCPError
        from powerbi_mcp.core.logger import get_logger

        assert PowerBIMCPError is not None
        assert get_logger is not None

    def test_auth_imports(self) -> None:
        """Auth module debe cargarse sin imports circulares."""
        from powerbi_mcp.powerbi_api.auth import PowerBIAuth

        assert PowerBIAuth is not None

    def test_archive_imports(self) -> None:
        """Archive module debe cargarse."""
        from powerbi_mcp.core.archive import safe_extract_zip, validate_zip_members

        assert safe_extract_zip is not None
        assert validate_zip_members is not None

    def test_ai_imports(self) -> None:
        """AI modules deben cargarse."""
        from powerbi_mcp.ai.anomaly import detect_anomalies
        from powerbi_mcp.ai.clustering import run_clustering
        from powerbi_mcp.ai.forecasting import forecast_series

        assert detect_anomalies is not None
        assert run_clustering is not None
        assert forecast_series is not None

    def test_visuals_imports(self) -> None:
        """Visuals modules deben cargarse."""
        from powerbi_mcp.visuals.builder import export_visual_html

        assert export_visual_html is not None

    def test_analysis_imports(self) -> None:
        """Analysis modules deben cargarse."""
        from powerbi_mcp.analysis.data_quality import analyze_data_quality

        assert analyze_data_quality is not None

    def test_security_imports(self) -> None:
        """Security modules deben cargarse."""
        from powerbi_mcp.security.masking import mask_dataset

        assert mask_dataset is not None

    def test_server_imports(self) -> None:
        """Server module debe cargarse sin imports circulares."""
        from powerbi_mcp.server import _tool, mcp

        assert mcp is not None
        assert _tool is not None
