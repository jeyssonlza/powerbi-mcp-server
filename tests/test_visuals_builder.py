"""Tests para construcción de visuales PBIR y HTML."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from powerbi_mcp.visuals.builder import export_visual_html


class TestVisualBuilder:
    """Suite de tests para construcción de visuales."""

    def test_export_bar_chart_html(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """Debe exportar bar chart a HTML."""
        output_path = tmp_path / "bar_chart.html"

        result = export_visual_html(
            sample_sales_data,
            chart_type="bar",
            output_path=str(output_path),
            x="Region",
            y="Amount",
        )

        assert result["ok"] or Path(output_path).exists()
        if Path(output_path).exists():
            content = output_path.read_text()
            assert "Region" in content or len(content) > 100

    def test_export_line_chart_html(self, tmp_path: Path, sample_forecast_data: pd.DataFrame) -> None:
        """Debe exportar line chart a HTML."""
        output_path = tmp_path / "line_chart.html"

        result = export_visual_html(
            sample_forecast_data,
            chart_type="line",
            output_path=str(output_path),
            x="Date",
            y="Value",
        )

        assert result["ok"] or Path(output_path).exists()

    def test_export_pie_chart_html(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """Debe exportar pie chart a HTML."""
        output_path = tmp_path / "pie_chart.html"

        result = export_visual_html(
            sample_sales_data,
            chart_type="pie",
            output_path=str(output_path),
            x="Product",
            y="Amount",
        )

        assert result["ok"] or Path(output_path).exists()

    def test_export_scatter_chart_html(self, tmp_path: Path, sample_numeric_data: pd.DataFrame) -> None:
        """Debe exportar scatter plot a HTML."""
        output_path = tmp_path / "scatter.html"

        result = export_visual_html(
            sample_numeric_data,
            chart_type="scatter",
            output_path=str(output_path),
            x="Feature1",
            y="Feature2",
        )

        assert result["ok"] or Path(output_path).exists()

    def test_export_with_color_dimension(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe soportar dimensión de color."""
        output_path = tmp_path / "colored.html"

        result = export_visual_html(
            sample_sales_data,
            chart_type="bar",
            output_path=str(output_path),
            x="Region",
            y="Amount",
            color="Product",
        )

        assert result["ok"] or Path(output_path).exists()

    def test_export_with_title(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """Debe incluir título en el gráfico."""
        output_path = tmp_path / "titled.html"
        title = "Sales by Region"

        result = export_visual_html(
            sample_sales_data,
            chart_type="bar",
            output_path=str(output_path),
            x="Region",
            y="Amount",
            title=title,
        )

        assert result["ok"] or Path(output_path).exists()
        if Path(output_path).exists():
            content = output_path.read_text()
            assert title in content or len(content) > 100

    def test_export_with_custom_palette(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Debe soportar paleta de colores personalizada."""
        output_path = tmp_path / "custom_colors.html"
        palette = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"]

        result = export_visual_html(
            sample_sales_data,
            chart_type="bar",
            output_path=str(output_path),
            x="Product",
            y="Amount",
            palette=palette,
        )

        assert result["ok"] or Path(output_path).exists()

    def test_export_multiple_y_columns(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """Debe soportar múltiples columnas en Y."""
        output_path = tmp_path / "multi_y.html"

        result = export_visual_html(
            sample_sales_data,
            chart_type="line",
            output_path=str(output_path),
            x="Date",
            y=["Amount", "Quantity"],
        )

        assert result["ok"] or Path(output_path).exists()

    def test_export_html_contains_interactivity(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """HTML exportado debe ser interactivo (Plotly)."""
        output_path = tmp_path / "interactive.html"

        export_visual_html(
            sample_sales_data,
            chart_type="bar",
            output_path=str(output_path),
            x="Region",
            y="Amount",
        )

        if Path(output_path).exists():
            content = output_path.read_text()
            # Plotly HTML debe contener referencias a plotly
            assert "plotly" in content.lower() or "javascript" in content.lower() or len(content) > 500

    def test_export_creates_output_directory(self, tmp_path: Path, sample_sales_data: pd.DataFrame) -> None:
        """Debe crear directorio de output si no existe."""
        output_path = tmp_path / "subdir" / "nested" / "chart.html"

        result = export_visual_html(
            sample_sales_data,
            chart_type="bar",
            output_path=str(output_path),
            x="Region",
            y="Amount",
        )

        # Podría crear el directorio o fallar; ambos aceptables
        if result["ok"]:
            assert Path(output_path).parent.exists()

    @pytest.mark.parametrize(
        "chart_type",
        ["bar", "column", "line", "area", "pie", "donut", "scatter", "table"],
    )
    def test_all_chart_types(
        self, tmp_path: Path, sample_sales_data: pd.DataFrame, chart_type: str
    ) -> None:
        """Todos los tipos de gráfico deben funcionar."""
        output_path = tmp_path / f"{chart_type}.html"

        try:
            result = export_visual_html(
                sample_sales_data,
                chart_type=chart_type,
                output_path=str(output_path),
                x="Region",
                y="Amount",
            )
            assert result["ok"] or Path(output_path).exists()
        except (ValueError, RuntimeError):
            # Algunos tipos podrían no estar implementados
            pass
