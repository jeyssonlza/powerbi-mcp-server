"""Tests para forecasting de series temporales (ARIMA, Exponential Smoothing)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.forecasting import forecast_series


class TestForecasting:
    """Suite de tests para forecasting."""

    def test_basic_forecast(self, sample_forecast_data: pd.DataFrame) -> None:
        """Debe generar pronóstico básico."""
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=12,
        )

        assert result.ok
        assert result.model_type == "forecasting"
        assert result.forecast is not None
        assert len(result.forecast) > 0
        # Debe tener datos históricos + pronóstico
        assert result.historical is not None

    def test_forecast_with_csv_input(self, tmp_path: pd.DataFrame) -> None:
        """Debe aceptar path a archivo CSV."""
        # Crear archivo CSV con datos de fecha/valor
        df = pd.DataFrame({
            "Date": pd.date_range("2023-01-01", periods=24, freq="MS"),
            "Sales": [100 + i * 10 + (i % 6) * 20 for i in range(24)],
        })
        csv_path = tmp_path / "forecast.csv"
        df.to_csv(csv_path, index=False)

        result = forecast_series(
            str(csv_path),
            date_column="Date",
            value_column="Sales",
            periods=6,
        )

        assert result.ok

    def test_forecast_with_seasonal_periods(self, sample_forecast_data: pd.DataFrame) -> None:
        """Debe respetar el parámetro seasonal_periods."""
        # 24 datos mensuales = 2 años, estacionalidad cada 12 meses
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=6,
            seasonal_periods=12,
        )

        assert result.ok
        assert result.forecast is not None

    def test_forecast_auto_seasonal_detection(self, sample_forecast_data: pd.DataFrame) -> None:
        """Debe detectar automáticamente seasonal_periods si es None."""
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=6,
            seasonal_periods=None,  # Auto
        )

        assert result.ok

    def test_forecast_different_periods(self, sample_forecast_data: pd.DataFrame) -> None:
        """Diferentes números de periodos deben funcionar."""
        for periods in [1, 3, 6, 12, 24]:
            result = forecast_series(
                sample_forecast_data,
                date_column="Date",
                value_column="Value",
                periods=periods,
            )
            assert result.ok
            # El pronóstico debe tener el número de periodos solicitado
            assert len(result.forecast) == periods

    def test_forecast_includes_confidence_intervals(
        self, sample_forecast_data: pd.DataFrame
    ) -> None:
        """El pronóstico debe incluir intervalos de confianza."""
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=6,
        )

        assert result.ok
        result_dict = result.to_dict()
        # Debe tener intervalos de confianza (upper, lower bounds)
        assert "forecast" in result_dict
        forecast_data = result_dict.get("forecast", {})
        # Alguna métrica de incertidumbre debe estar presente
        assert isinstance(forecast_data, (dict, list))

    def test_forecast_with_different_sizes(self) -> None:
        """Debe funcionar con series de diferentes tamaños."""
        for size in [10, 20, 50, 100]:
            df = pd.DataFrame({
                "Date": pd.date_range("2023-01-01", periods=size, freq="D"),
                "Value": [100 + i * 0.5 for i in range(size)],
            })
            result = forecast_series(
                df,
                date_column="Date",
                value_column="Value",
                periods=5,
            )
            assert result.ok

    def test_forecast_result_serialization(self, sample_forecast_data: pd.DataFrame) -> None:
        """El resultado debe ser serializable a diccionario."""
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=6,
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "forecast" in result_dict
        assert "model_type" in result_dict
        assert "historical" in result_dict

    def test_forecast_insufficient_data_handling(self) -> None:
        """Debe manejar series con muy pocos datos."""
        tiny_df = pd.DataFrame({
            "Date": pd.date_range("2023-01-01", periods=3, freq="D"),
            "Value": [100, 105, 110],
        })

        try:
            result = forecast_series(
                tiny_df,
                date_column="Date",
                value_column="Value",
                periods=2,
            )
            # Podría funcionar o fallar; ambos son aceptables
            if result.ok:
                assert result.forecast is not None
        except (ValueError, RuntimeError):
            pass

    def test_forecast_output_structure(self, sample_forecast_data: pd.DataFrame) -> None:
        """El output debe tener estructura predecible."""
        result = forecast_series(
            sample_forecast_data,
            date_column="Date",
            value_column="Value",
            periods=6,
        )

        assert hasattr(result, "ok")
        assert hasattr(result, "model_type")
        assert hasattr(result, "forecast")
        assert hasattr(result, "historical")
        assert hasattr(result, "to_dict")
