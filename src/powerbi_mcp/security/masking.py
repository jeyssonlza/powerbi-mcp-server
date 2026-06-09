"""Enmascaramiento de información personal identificable (PII).

Detecta y enmascara datos sensibles habituales (emails, teléfonos, documentos de
identidad, tarjetas de crédito, IBAN) tanto en valores sueltos como en columnas
completas de un conjunto de datos, con varias estrategias:

- ``partial``: muestra parcialmente (ej. ``j****@dominio.com``).
- ``full``: sustituye por una cadena fija de asteriscos.
- ``hash``: reemplaza por un hash corto (irreversible).

La detección automática usa expresiones regulares y heurísticas sobre el nombre
de la columna; siempre conviene revisar el resultado en datos críticos.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from powerbi_mcp.ai._base import to_dataframe
from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

VALID_STRATEGIES = frozenset({"partial", "full", "hash"})

# --- Patrones de detección de PII ------------------------------------------
_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$"),
    "phone": re.compile(r"^\+?[\d\s().-]{7,}$"),
    "credit_card": re.compile(r"^(?:\d[ -]?){13,19}$"),
    "iban": re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$"),
}

# --- Nombres de columna que sugieren PII -----------------------------------
_PII_COLUMN_HINTS: dict[str, tuple[str, ...]] = {
    "email": ("email", "correo", "mail", "e-mail"),
    "phone": ("phone", "telefono", "teléfono", "celular", "movil", "móvil", "tel"),
    "name": ("name", "nombre", "apellido", "fullname", "cliente"),
    "document": ("dni", "nif", "cedula", "cédula", "rut", "ssn", "passport", "pasaporte", "documento"),
    "credit_card": ("card", "tarjeta", "creditcard", "pan"),
    "address": ("address", "direccion", "dirección", "domicilio"),
}


def detect_pii_type(value: str, *, column_name: str | None = None) -> str | None:
    """Detecta el tipo de PII de un valor (y, si se da, el nombre de columna).

    Args:
        value: Valor a analizar.
        column_name: Nombre de la columna (refuerza la detección).

    Returns:
        El tipo de PII detectado (``"email"``, ``"phone"``...) o ``None``.
    """
    text = str(value).strip()
    for pii_type, pattern in _PATTERNS.items():
        if pattern.match(text):
            return pii_type
    if column_name:
        col_low = column_name.lower()
        for pii_type, hints in _PII_COLUMN_HINTS.items():
            if any(h in col_low for h in hints):
                return pii_type
    return None


def mask_value(value: Any, *, pii_type: str | None = None, strategy: str = "partial") -> str:
    """Enmascara un valor individual.

    Args:
        value: Valor a enmascarar.
        pii_type: Tipo de PII (afecta al modo ``partial``). Si es ``None``, se
            intenta detectar.
        strategy: ``"partial"``, ``"full"`` o ``"hash"``.

    Returns:
        El valor enmascarado.

    Raises:
        ValidationError: Si la estrategia no es válida.
    """
    if strategy not in VALID_STRATEGIES:
        raise ValidationError(
            "Estrategia de masking no válida.",
            details={"strategy": strategy, "valid": sorted(VALID_STRATEGIES)},
        )
    text = str(value)
    if not text:
        return text

    if strategy == "full":
        return "*" * max(len(text), 4)
    if strategy == "hash":
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]

    # strategy == "partial"
    resolved_type = pii_type or detect_pii_type(text)
    return _partial_mask(text, resolved_type)


def _partial_mask(text: str, pii_type: str | None) -> str:
    """Aplica enmascaramiento parcial según el tipo de PII."""
    if pii_type == "email" and "@" in text:
        local, _, domain = text.partition("@")
        shown = local[0] if local else "*"
        return f"{shown}{'*' * max(len(local) - 1, 1)}@{domain}"
    if pii_type in {"phone", "credit_card", "iban", "document"}:
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 4:
            return f"{'*' * (len(text) - 4)}{text[-4:]}"
    if pii_type == "name":
        parts = text.split()
        return " ".join(p[0] + "." for p in parts if p)
    # Genérico: muestra primero y último carácter.
    if len(text) <= 2:
        return "*" * len(text)
    return f"{text[0]}{'*' * (len(text) - 2)}{text[-1]}"


def mask_dataset(
    data: Any,
    *,
    columns: list[str] | None = None,
    strategy: str = "partial",
    auto_detect: bool = True,
) -> dict[str, Any]:
    """Enmascara columnas con PII en un conjunto de datos.

    Args:
        data: Datos de entrada (DataFrame, registros, dict o ruta).
        columns: Columnas a enmascarar explícitamente. Si es ``None`` y
            ``auto_detect`` es ``True``, se detectan automáticamente.
        strategy: Estrategia de enmascaramiento a aplicar.
        auto_detect: Si es ``True``, detecta columnas PII por nombre/contenido.

    Returns:
        Diccionario con la tabla enmascarada y las columnas afectadas.

    Raises:
        ValidationError: Si alguna columna indicada no existe.
    """
    df = to_dataframe(data)
    target_columns = list(columns) if columns else []

    if columns:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise ValidationError("Columnas inexistentes.", details={"missing": missing})

    detected: dict[str, str] = {}
    if auto_detect and not columns:
        for col in df.columns:
            sample = df[col].dropna().astype(str).head(20)
            pii_type = None
            for val in sample:
                pii_type = detect_pii_type(val, column_name=str(col))
                if pii_type:
                    break
            if pii_type:
                detected[col] = pii_type
                target_columns.append(col)

    def _mask_cell(value: Any, pii_type: str | None) -> Any:
        if value is None or str(value) == "nan":
            return value
        return mask_value(value, pii_type=pii_type, strategy=strategy)

    from functools import partial

    result = df.copy()
    for col in target_columns:
        pii_type = detected.get(col)
        result[col] = result[col].map(partial(_mask_cell, pii_type=pii_type))

    logger.info("Masking aplicado a %d columnas (%s)", len(target_columns), strategy)
    return {
        "strategy": strategy,
        "masked_columns": target_columns,
        "detected_types": detected,
        "table": result.to_dict(orient="records"),
    }


__all__ = [
    "VALID_STRATEGIES",
    "detect_pii_type",
    "mask_dataset",
    "mask_value",
]
