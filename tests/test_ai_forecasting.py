"""Tests para forecasting de series temporales (Holt-Winters / regresión).

Valida el contrato real de ``forecast_series`` -> ``AIResult`` con ``model_type``
``"forecast"``, un ``table`` que combina filas ``history`` y ``forecast`` con
columnas ``date``, ``value``, ``type``, ``lower``, ``upper``.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.forecasting import forecast_series
from powerbi_mcp.core.exceptions import InsufficientDataError, ValidationError


def _forecast_rows(result) -> list[dict]:
    return [r for r in result.table if r["type"] == "forecast"]


def _history_rows(result) -> list[dict]:
    return [r for r in result.table if r["type"] == "history"]


class TestForecasting:
    """Suite de tests para forecasting."""

    def test_basic_forecast(self, sample_forecast_data: pd.DataFrame) -> None:
        """Debe generar un pronóstico con histórico + futuro."""
        result = forecast_series(
            sample_forecast_data, date_column="Date", value_column="Value", periods=12
        )
        assert result.model_type == "forecast"
        assert len(_forecast_rows(result)) == 12
        assert len(_history_rows(result)) == len(sample_forecast_data)

    def test_forecast_columns_present(self, sample_forecast_data: pd.DataFrame) -> None:
        """El resultado debe exponer las columnas esperadas."""
        result = forecast_series(
            sample_forecast_data, date_column="Date", value_column="Value", periods=6
        )
        assert result.columns == ["date", "value", "type", "lower", "upper"]

    def test_forecast_rows_have_confidence_interval(
        self, sample_forecast_data: pd.DataFrame
    ) -> None:
        """Las filas de pronóstico deben incluir límites de confianza."""
        result = forecast_series(
            sample_forecast_data, date_column="Date", value_column="Value", periods=6
        )
        for row in _forecast_rows(result):
            assert row["lower"] is not None
            assert row["upper"] is not None
            assert row["lower"] <= row["upper"]

    def test_seasonal_periods_respected(self, sample_forecast_data: pd.DataFrame) -> None:
        """Con seasonal_periods=12 debe ejecutarse correctamente."""
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=6,
            seasonal_periods=12,
        )
        assert result.summary["forecast_periods"] == 6

    def test_summary_metrics(self, sample_forecast_data: pd.DataFrame) -> None:
        """El summary debe reportar puntos de historia y media pronosticada."""
        result = forecast_series(
            sample_forecast_data, date_column="Date", value_column="Value", periods=6
        )
        assert result.summary["history_points"] == len(sample_forecast_data)
        assert "forecast_mean" in result.summary
        assert "method" in result.summary

    @pytest.mark.parametrize("periods", [1, 3, 6, 12])
    def test_different_period_counts(
        self, sample_forecast_data: pd.DataFrame, periods: int
    ) -> None:
        """El número de filas de pronóstico debe igualar los periodos pedidos."""
        result = forecast_series(
            sample_forecast_data, date_column="Date", value_column="Value", periods=periods
        )
        assert len(_forecast_rows(result)) == periods

    def test_works_with_csv_input(self, tmp_path) -> None:
        """Debe aceptar una ruta a CSV como entrada."""
        df = pd.DataFrame({
            "Date": pd.date_range("2023-01-01", periods=24, freq="MS"),
            "Sales": [100 + i * 10 + (i % 6) * 20 for i in range(24)],
        })
        csv_path = tmp_path / "forecast.csv"
        df.to_csv(csv_path, index=False)
        result = forecast_series(
            str(csv_path), date_column="Date", value_column="Sales", periods=6
        )
        assert result.model_type == "forecast"

    def test_missing_column_raises(self, sample_forecast_data: pd.DataFrame) -> None:
        """Una columna inexistente debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            forecast_series(
                sample_forecast_data, date_column="Date", value_column="NoExiste", periods=6
            )

    def test_invalid_periods_raises(self, sample_forecast_data: pd.DataFrame) -> None:
        """periods < 1 debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            forecast_series(
                sample_forecast_data, date_column="Date", value_column="Value", periods=0
            )

    def test_insufficient_data_raises(self) -> None:
        """Menos de 4 puntos debe lanzar InsufficientDataError."""
        tiny = pd.DataFrame({
            "Date": pd.date_range("2023-01-01", periods=3, freq="D"),
            "Value": [100, 105, 110],
        })
        with pytest.raises(InsufficientDataError):
            forecast_series(tiny, date_column="Date", value_column="Value", periods=2)

    def test_result_serializable(self, sample_forecast_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario."""
        result = forecast_series(
            sample_forecast_data, date_column="Date", value_column="Value", periods=6
        )
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "forecast"
        assert "table" in as_dict
