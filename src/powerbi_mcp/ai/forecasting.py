"""Forecasting de series de tiempo sobre datos del modelo.

Usa suavizado exponencial (Holt-Winters / ETS) de ``statsmodels`` cuando hay
suficiente historia, con detección automática de estacionalidad. Si no es
posible, recurre a una regresión lineal de tendencia como respaldo robusto.

Devuelve la serie histórica más los puntos pronosticados con su intervalo de
confianza, listos para integrarse o graficarse.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from powerbi_mcp.ai._base import AIResult, to_dataframe
from powerbi_mcp.core.exceptions import AIModelError, InsufficientDataError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def forecast_series(
    data: Any,
    *,
    date_column: str,
    value_column: str,
    periods: int = 12,
    seasonal_periods: int | None = None,
    confidence: float = 0.95,
) -> AIResult:
    """Pronostica los próximos ``periods`` valores de una serie temporal.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        date_column: Columna de fecha/tiempo (se ordena por ella).
        value_column: Columna numérica a pronosticar.
        periods: Número de periodos futuros a pronosticar.
        seasonal_periods: Longitud del ciclo estacional (ej. 12=mensual anual).
            Si es ``None``, se intenta inferir; si no, se usa modelo no estacional.
        confidence: Nivel de confianza del intervalo (0-1).

    Returns:
        :class:`~powerbi_mcp.ai._base.AIResult` con columnas ``date``,
        ``value``, ``type`` (``history``/``forecast``), ``lower``, ``upper``.

    Raises:
        ValidationError: Si faltan columnas o parámetros inválidos.
        InsufficientDataError: Si hay muy pocos puntos.
    """
    df = to_dataframe(data)
    for col in (date_column, value_column):
        if col not in df.columns:
            raise ValidationError("Columna inexistente.", details={"column": col})
    if periods < 1:
        raise ValidationError("periods debe ser >= 1.", details={"periods": periods})

    series = _prepare_series(df, date_column, value_column)
    if len(series) < 4:
        raise InsufficientDataError(
            "Se requieren al menos 4 puntos para pronosticar.",
            details={"points": len(series)},
        )

    if seasonal_periods is None:
        seasonal_periods = _infer_seasonality(series)

    try:
        forecast, lower, upper, method = _ets_forecast(
            series, periods, seasonal_periods, confidence
        )
    except Exception as exc:
        logger.warning("ETS falló (%s); usando regresión lineal de respaldo.", exc)
        forecast, lower, upper, method = _linear_forecast(series, periods, confidence)

    table = _build_table(series, forecast, lower, upper)
    summary = {
        "method": method,
        "history_points": len(series),
        "forecast_periods": int(periods),
        "seasonal_periods": seasonal_periods,
        "confidence": confidence,
        "last_value": round(float(series.iloc[-1]), 4),
        "forecast_mean": round(float(np.mean(forecast)), 4),
    }
    logger.info("Forecast %s: %d periodos (%s)", value_column, periods, method)

    return AIResult(
        model_type="forecast",
        summary=summary,
        table=table,
        columns=["date", "value", "type", "lower", "upper"],
        metadata={"method": method, "date_column": date_column, "value_column": value_column},
    )


def _prepare_series(df: pd.DataFrame, date_column: str, value_column: str) -> pd.Series:
    """Ordena por fecha y devuelve una serie numérica limpia indexada por fecha."""
    work = df[[date_column, value_column]].copy()
    work[date_column] = pd.to_datetime(work[date_column], errors="coerce")
    work[value_column] = pd.to_numeric(work[value_column], errors="coerce")
    work = work.dropna().sort_values(date_column)
    series = pd.Series(work[value_column].to_numpy(), index=work[date_column])
    return series


def _infer_seasonality(series: pd.Series) -> int | None:
    """Intenta inferir la estacionalidad a partir de la frecuencia de fechas."""
    if len(series) < 24:
        return None
    freq = pd.infer_freq(series.index)
    if freq is None:
        return None
    mapping = {"M": 12, "MS": 12, "Q": 4, "QS": 4, "D": 7, "W": 52, "H": 24}
    for key, value in mapping.items():
        if freq.startswith(key) and len(series) >= 2 * value:
            return value
    return None


def _ets_forecast(
    series: pd.Series, periods: int, seasonal_periods: int | None, confidence: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Pronostica con suavizado exponencial (Holt-Winters)."""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
    except ImportError as exc:  # pragma: no cover
        raise AIModelError("statsmodels no está instalado.") from exc

    use_seasonal = bool(seasonal_periods and len(series) >= 2 * seasonal_periods)
    model = ExponentialSmoothing(
        series.to_numpy(dtype=float),
        trend="add",
        seasonal="add" if use_seasonal else None,
        seasonal_periods=seasonal_periods if use_seasonal else None,
        initialization_method="estimated",
    )
    fit = model.fit()
    forecast = np.asarray(fit.forecast(periods), dtype=float)

    # Intervalo de confianza aproximado a partir de los residuos.
    resid = np.asarray(fit.resid, dtype=float)
    sigma = np.nanstd(resid) if resid.size else 0.0
    z = _z_for_confidence(confidence)
    margin = z * sigma
    lower = forecast - margin
    upper = forecast + margin
    method = "holt_winters_seasonal" if use_seasonal else "holt_winters_trend"
    return forecast, lower, upper, method


def _linear_forecast(
    series: pd.Series, periods: int, confidence: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Pronóstico de respaldo por regresión lineal sobre el índice temporal."""
    y = series.to_numpy(dtype=float)
    x = np.arange(len(y))
    coeffs = np.polyfit(x, y, 1)
    trend = np.poly1d(coeffs)
    future_x = np.arange(len(y), len(y) + periods)
    forecast = trend(future_x)

    residuals = y - trend(x)
    sigma = float(np.std(residuals))
    z = _z_for_confidence(confidence)
    margin = z * sigma
    return forecast, forecast - margin, forecast + margin, "linear_trend"


def _z_for_confidence(confidence: float) -> float:
    """Devuelve el z-score aproximado para un nivel de confianza dado."""
    table = {0.80: 1.282, 0.90: 1.645, 0.95: 1.960, 0.975: 2.241, 0.99: 2.576}
    closest = min(table, key=lambda c: abs(c - confidence))
    return table[closest]


def _build_table(
    series: pd.Series, forecast: np.ndarray, lower: np.ndarray, upper: np.ndarray
) -> list[dict[str, Any]]:
    """Construye la tabla combinada de histórico + pronóstico."""
    rows: list[dict[str, Any]] = []
    for ts, val in series.items():
        rows.append(
            {
                "date": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "value": round(float(val), 4),
                "type": "history",
                "lower": None,
                "upper": None,
            }
        )

    # Fechas futuras: continúa con la frecuencia inferida o paso unitario.
    freq = pd.infer_freq(series.index)
    if freq:
        future_index = pd.date_range(series.index[-1], periods=len(forecast) + 1, freq=freq)[1:]
    else:
        step = series.index[-1] - series.index[-2] if len(series) > 1 else pd.Timedelta(days=1)
        future_index = [series.index[-1] + step * (i + 1) for i in range(len(forecast))]

    for ts, val, lo, up in zip(future_index, forecast, lower, upper, strict=False):
        rows.append(
            {
                "date": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "value": round(float(val), 4),
                "type": "forecast",
                "lower": round(float(lo), 4),
                "upper": round(float(up), 4),
            }
        )
    return rows


__all__ = ["forecast_series"]
