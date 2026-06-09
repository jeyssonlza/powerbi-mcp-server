"""Tests para construcción de visuales HTML interactivos (Plotly).

Valida el contrato real de ``export_visual_html`` -> dict con ``chart_type``,
``html`` y ``path`` (cuando se indica ``output_path``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.visuals.builder import export_visual_html
from powerbi_mcp.visuals.html_visuals import CHART_TYPES


class TestVisualBuilder:
    """Suite de tests para construcción de visuales HTML."""

    def test_export_bar_chart_creates_file(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe exportar un bar chart a un archivo HTML existente."""
        output_path = tmp_path / "bar_chart.html"
        result = export_visual_html(
            sample_sales_data, "bar", output_path=str(output_path), x="Region", y="Amount"
        )
        assert result["chart_type"] == "bar"
        assert "html" in result
        assert Path(result["path"]).exists()

    def test_export_line_chart(
        self, tmp_path: Path, sample_forecast_data: pd.DataFrame
    ) -> None:
        """Debe exportar un line chart a HTML."""
        output_path = tmp_path / "line_chart.html"
        result = export_visual_html(
            sample_forecast_data, "line", output_path=str(output_path), x="Date", y="Value"
        )
        assert Path(result["path"]).exists()

    def test_export_pie_chart(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """Debe exportar un pie chart a HTML."""
        output_path = tmp_path / "pie_chart.html"
        result = export_visual_html(
            sample_sales_data, "pie", output_path=str(output_path), x="Product", y="Amount"
        )
        assert Path(result["path"]).exists()

    def test_export_scatter_chart(
        self, tmp_path: Path, sample_numeric_data: pd.DataFrame
    ) -> None:
        """Debe exportar un scatter plot a HTML."""
        output_path = tmp_path / "scatter.html"
        result = export_visual_html(
            sample_numeric_data, "scatter", output_path=str(output_path),
            x="Feature1", y="Feature2",
        )
        assert Path(result["path"]).exists()

    def test_export_with_color_dimension(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe soportar una dimensión de color."""
        output_path = tmp_path / "colored.html"
        result = export_visual_html(
            sample_sales_data, "bar", output_path=str(output_path),
            x="Region", y="Amount", color="Product",
        )
        assert Path(result["path"]).exists()

    def test_export_with_title_embeds_title(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """El título debe quedar embebido en el HTML generado."""
        output_path = tmp_path / "titled.html"
        title = "Sales by Region"
        result = export_visual_html(
            sample_sales_data, "bar", output_path=str(output_path),
            x="Region", y="Amount", title=title,
        )
        content = Path(result["path"]).read_text(encoding="utf-8")
        assert title in content

    def test_export_with_custom_palette(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe aceptar una paleta de colores personalizada."""
        output_path = tmp_path / "custom_colors.html"
        palette = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]
        result = export_visual_html(
            sample_sales_data, "bar", output_path=str(output_path),
            x="Product", y="Amount", palette=palette,
        )
        assert Path(result["path"]).exists()

    def test_export_multiple_y_columns(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe soportar múltiples columnas en el eje Y."""
        output_path = tmp_path / "multi_y.html"
        result = export_visual_html(
            sample_sales_data, "line", output_path=str(output_path),
            x="Date", y=["Amount", "Quantity"],
        )
        assert Path(result["path"]).exists()

    def test_html_is_interactive_plotly(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """El HTML exportado debe contener Plotly (interactivo)."""
        output_path = tmp_path / "interactive.html"
        result = export_visual_html(
            sample_sales_data, "bar", output_path=str(output_path), x="Region", y="Amount"
        )
        content = Path(result["path"]).read_text(encoding="utf-8")
        assert "plotly" in content.lower()

    def test_creates_nested_output_directory(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe crear los directorios intermedios del output si no existen."""
        output_path = tmp_path / "subdir" / "nested" / "chart.html"
        result = export_visual_html(
            sample_sales_data, "bar", output_path=str(output_path), x="Region", y="Amount"
        )
        assert Path(result["path"]).parent.exists()
        assert Path(result["path"]).exists()

    def test_invalid_chart_type_raises(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Un tipo de gráfico no válido debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            export_visual_html(
                sample_sales_data, "not_a_chart",
                output_path=str(tmp_path / "x.html"), x="Region", y="Amount",
            )

    @pytest.mark.parametrize(
        "chart_type",
        ["bar", "column", "line", "area", "pie", "donut", "scatter", "table"],
    )
    def test_common_chart_types(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame, chart_type: str
    ) -> None:
        """Los tipos de gráfico habituales deben generar un HTML válido."""
        output_path = tmp_path / f"{chart_type}.html"
        result = export_visual_html(
            sample_sales_data, chart_type, output_path=str(output_path),
            x="Region", y="Amount",
        )
        assert result["chart_type"] == chart_type
        assert Path(result["path"]).exists()

    def test_chart_types_constant_covers_common(self) -> None:
        """La constante CHART_TYPES debe incluir los tipos habituales."""
        assert {"bar", "line", "pie", "scatter", "table"} <= CHART_TYPES
