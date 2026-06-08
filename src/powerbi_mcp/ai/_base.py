"""Utilidades compartidas por los modelos de IA.

Centraliza la preparación de datos (carga a ``pandas``, selección de columnas
numéricas, imputación básica, escalado) y la estructura de resultado común, para
que cada modelo (anomalías, clustering, forecasting...) se enfoque solo en su
lógica específica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import pandas as pd

from powerbi_mcp.core.exceptions import InsufficientDataError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AIResult:
    """Resultado estándar de un modelo de IA.

    Attributes:
        model_type: Identificador del modelo (``"anomaly"``, ``"clustering"``...).
        summary: Métricas y descripción legible del resultado.
        table: Filas resultantes (lista de dicts) listas para integrarse como
            tabla calculada o exportarse. Puede estar vacío.
        columns: Nombres de columnas de ``table`` (orden estable).
        metadata: Información adicional (parámetros, modelo, advertencias).
    """

    model_type: str
    summary: dict[str, Any] = field(default_factory=dict)
    table: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializa el resultado a diccionario JSON-serializable."""
        return {
            "model_type": self.model_type,
            "summary": self.summary,
            "columns": self.columns,
            "row_count": len(self.table),
            "table": self.table,
            "metadata": self.metadata,
        }


def to_dataframe(data: Any) -> pd.DataFrame:
    """Convierte distintas entradas a un :class:`pandas.DataFrame`.

    Acepta:
    - un ``DataFrame`` (se devuelve tal cual),
    - una lista de diccionarios (registros),
    - un diccionario de columnas (``{col: [valores]}``),
    - una ruta a un archivo ``.csv``/``.parquet``/``.xlsx``.

    Args:
        data: La fuente de datos.

    Returns:
        El DataFrame resultante.

    Raises:
        ValidationError: Si el formato no se reconoce o el archivo no se lee.
    """
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, list):
        return pd.DataFrame.from_records(data)
    if isinstance(data, dict):
        return pd.DataFrame(data)
    if isinstance(data, str):
        return _read_file(data)
    raise ValidationError(
        "Formato de datos no reconocido para IA.",
        details={"type": type(data).__name__},
    )


def _read_file(path: str) -> pd.DataFrame:
    """Lee un archivo tabular según su extensión."""
    lower = path.lower()
    try:
        if lower.endswith(".csv"):
            return pd.read_csv(path)
        if lower.endswith(".parquet"):
            return pd.read_parquet(path)
        if lower.endswith((".xlsx", ".xls")):
            return pd.read_excel(path)
    except (OSError, ValueError) as exc:
        raise ValidationError(
            "No se pudo leer el archivo de datos.",
            details={"path": path, "error": str(exc)},
        ) from exc
    raise ValidationError("Extensión de archivo no soportada.", details={"path": path})


def select_numeric(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    *,
    min_rows: int = 5,
) -> pd.DataFrame:
    """Selecciona y limpia columnas numéricas para el modelado.

    Args:
        df: DataFrame de entrada.
        columns: Columnas a usar. Si es ``None``, se autodetectan las numéricas.
        min_rows: Mínimo de filas válidas requeridas tras limpiar.

    Returns:
        DataFrame solo con las columnas numéricas seleccionadas, sin NaN.

    Raises:
        ValidationError: Si alguna columna pedida no existe o no es numérica.
        InsufficientDataError: Si quedan menos de ``min_rows`` filas.
    """
    if columns is not None:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValidationError("Columnas inexistentes.", details={"missing": missing})
        subset = df[columns].apply(pd.to_numeric, errors="coerce")
    else:
        subset = df.select_dtypes(include=[np.number])

    subset = subset.dropna()
    if subset.shape[0] < min_rows:
        raise InsufficientDataError(
            "Datos numéricos insuficientes tras limpiar valores nulos.",
            details={"rows": int(subset.shape[0]), "min_rows": min_rows},
        )
    if subset.shape[1] == 0:
        raise ValidationError("No hay columnas numéricas utilizables.")
    return subset


def standardize(df: pd.DataFrame) -> np.ndarray:
    """Estandariza (z-score) las columnas de un DataFrame numérico.

    Args:
        df: DataFrame numérico.

    Returns:
        Array NumPy estandarizado (media 0, desviación 1 por columna).
    """
    values = df.to_numpy(dtype=float)
    mean = values.mean(axis=0)
    std = values.std(axis=0)
    std[std == 0] = 1.0  # evita división por cero en columnas constantes
    return cast(np.ndarray, (values - mean) / std)


__all__ = [
    "AIResult",
    "select_numeric",
    "standardize",
    "to_dataframe",
]
