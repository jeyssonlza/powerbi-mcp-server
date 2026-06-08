"""Generación de claves subrogadas (surrogate keys) para datos sensibles.

Permite sustituir identificadores reales (cédulas, emails, números de cliente)
por claves subrogadas, en dos modalidades:

- **Determinista** (HMAC-SHA256 + salt secreto): el mismo valor de entrada
  produce siempre la misma clave, preservando *joins* y relaciones entre tablas
  sin exponer el valor original. Es seudonimización reversible solo con la tabla
  de mapeo (que debe protegerse).
- **Secuencial**: asigna enteros incrementales (1, 2, 3...) con una tabla de
  mapeo, útil como clave técnica compacta para modelos en estrella.

El salt determinista se toma de ``settings.surrogate_salt``.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import pandas as pd

from powerbi_mcp.ai._base import to_dataframe
from powerbi_mcp.config import get_settings
from powerbi_mcp.core.exceptions import SecurityError, ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def deterministic_key(value: Any, *, salt: str | None = None, length: int = 16) -> str:
    """Genera una clave subrogada determinista para un valor.

    Args:
        value: Valor de entrada (se normaliza a texto).
        salt: Salt secreto. Si es ``None``, se usa ``settings.surrogate_salt``.
        length: Longitud de la clave hexadecimal resultante (máx. 64).

    Returns:
        Clave hexadecimal determinista.

    Raises:
        SecurityError: Si no hay salt configurado.
        ValidationError: Si ``length`` está fuera de rango.
    """
    resolved_salt = salt or get_settings().surrogate_salt
    if not resolved_salt:
        raise SecurityError(
            "No hay salt para claves subrogadas. Define PBIMCP_SURROGATE_SALT "
            "o pásalo explícitamente."
        )
    if not 1 <= length <= 64:
        raise ValidationError("length debe estar entre 1 y 64.", details={"length": length})

    digest = hmac.new(
        resolved_salt.encode("utf-8"),
        str(value).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:length]


def generate_surrogate_keys(
    data: Any,
    column: str,
    *,
    method: str = "deterministic",
    new_column: str | None = None,
    salt: str | None = None,
    key_length: int = 16,
) -> dict[str, Any]:
    """Genera claves subrogadas para una columna de un conjunto de datos.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        column: Columna cuyos valores se sustituirán por claves subrogadas.
        method: ``"deterministic"`` (HMAC) o ``"sequential"`` (enteros).
        new_column: Nombre de la columna de clave. Por defecto ``<column>_sk``.
        salt: Salt para el método determinista.
        key_length: Longitud de la clave determinista.

    Returns:
        Diccionario con la tabla resultante (``table``), la tabla de mapeo
        (``mapping``) y metadatos.

    Raises:
        ValidationError: Si la columna no existe o el método no es válido.
    """
    if method not in {"deterministic", "sequential"}:
        raise ValidationError(
            "Método no válido (usa 'deterministic' o 'sequential').",
            details={"method": method},
        )

    df = to_dataframe(data)
    if column not in df.columns:
        raise ValidationError("Columna inexistente.", details={"column": column})

    sk_column = new_column or f"{column}_sk"
    result = df.copy()

    if method == "deterministic":
        result[sk_column] = result[column].map(
            lambda v: deterministic_key(v, salt=salt, length=key_length)
        )
    else:
        unique_values = result[column].dropna().unique()
        mapping_seq = {val: idx + 1 for idx, val in enumerate(unique_values)}
        result[sk_column] = result[column].map(mapping_seq)

    # Tabla de mapeo (valor original -> clave subrogada), sin duplicados.
    mapping_df = (
        result[[column, sk_column]].drop_duplicates().reset_index(drop=True)
    )

    logger.info(
        "Claves subrogadas (%s) generadas para '%s': %d valores únicos",
        method,
        column,
        len(mapping_df),
    )
    return {
        "method": method,
        "source_column": column,
        "key_column": sk_column,
        "unique_values": len(mapping_df),
        "table": result.to_dict(orient="records"),
        "mapping": mapping_df.to_dict(orient="records"),
    }


def build_dimension_with_keys(
    data: Any,
    column: str,
    *,
    method: str = "sequential",
    salt: str | None = None,
) -> dict[str, Any]:
    """Crea una tabla de dimensión con clave subrogada a partir de una columna.

    Genera una tabla de dimensión deduplicada (una fila por valor distinto) con
    su clave subrogada, ideal para esquemas en estrella.

    Args:
        data: Datos de entrada.
        column: Columna que se convierte en dimensión.
        method: ``"sequential"`` o ``"deterministic"``.
        salt: Salt para el método determinista.

    Returns:
        Diccionario con la tabla de dimensión y su nombre de clave.
    """
    result = generate_surrogate_keys(data, column, method=method, salt=salt)
    dimension = pd.DataFrame(result["mapping"]).reset_index(drop=True)
    return {
        "dimension_table": dimension.to_dict(orient="records"),
        "key_column": result["key_column"],
        "source_column": column,
        "rows": len(dimension),
    }


__all__ = [
    "build_dimension_with_keys",
    "deterministic_key",
    "generate_surrogate_keys",
]
