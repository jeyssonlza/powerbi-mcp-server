"""Tests para enmascaramiento de datos sensibles (PII masking).

Valida el contrato real de ``mask_dataset`` -> dict con ``strategy``,
``masked_columns``, ``detected_types`` y ``table`` (lista de registros).
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.security.masking import (
    VALID_STRATEGIES,
    detect_pii_type,
    mask_dataset,
    mask_value,
)


class TestDataMasking:
    """Suite de tests para masking de datasets."""

    def test_result_structure(self, sample_quality_data: pd.DataFrame) -> None:
        """El resultado debe contener las claves del contrato."""
        result = mask_dataset(
            sample_quality_data, columns=["Email"], strategy="partial", auto_detect=False
        )
        for key in ("strategy", "masked_columns", "detected_types", "table"):
            assert key in result
        assert result["strategy"] == "partial"
        assert result["masked_columns"] == ["Email"]

    def test_partial_email_keeps_domain(self, sample_quality_data: pd.DataFrame) -> None:
        """El enmascaramiento parcial de email debe conservar el dominio y ocultar parte."""
        result = mask_dataset(
            sample_quality_data, columns=["Email"], strategy="partial", auto_detect=False
        )
        masked = pd.DataFrame(result["table"])["Email"].dropna()
        emails = [e for e in masked if "@" in str(e)]
        assert emails
        assert any("*" in str(e) for e in emails)

    def test_full_masking_replaces_value(self, sample_quality_data: pd.DataFrame) -> None:
        """El enmascaramiento full debe reemplazar el valor por asteriscos."""
        result = mask_dataset(
            sample_quality_data, columns=["Email"], strategy="full", auto_detect=False
        )
        masked = pd.DataFrame(result["table"])["Email"].dropna()
        assert all(set(str(v)) == {"*"} for v in masked)

    def test_hash_masking_is_deterministic(self) -> None:
        """El hash del mismo valor debe ser idéntico (determinista)."""
        df = pd.DataFrame({"Email": ["a@x.com", "a@x.com", "b@x.com"]})
        result = mask_dataset(df, columns=["Email"], strategy="hash", auto_detect=False)
        masked = pd.DataFrame(result["table"])["Email"].tolist()
        assert masked[0] == masked[1]  # mismo input -> mismo hash
        assert masked[0] != masked[2]  # input distinto -> hash distinto

    def test_auto_detect_pii(self, sample_quality_data: pd.DataFrame) -> None:
        """Con auto_detect debe identificar columnas PII (Email/Name)."""
        result = mask_dataset(sample_quality_data, strategy="partial", auto_detect=True)
        assert len(result["masked_columns"]) > 0
        assert len(result["detected_types"]) > 0

    def test_mask_multiple_columns(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe enmascarar varias columnas indicadas."""
        result = mask_dataset(
            sample_quality_data, columns=["Email", "Name"], strategy="partial", auto_detect=False
        )
        assert result["masked_columns"] == ["Email", "Name"]

    def test_preserves_row_count(self, sample_quality_data: pd.DataFrame) -> None:
        """El enmascaramiento no debe cambiar el número de filas."""
        result = mask_dataset(
            sample_quality_data, columns=["Email"], strategy="partial", auto_detect=False
        )
        assert len(result["table"]) == len(sample_quality_data)

    def test_invalid_column_raises(self, sample_quality_data: pd.DataFrame) -> None:
        """Una columna inexistente debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            mask_dataset(sample_quality_data, columns=["NoExiste"], auto_detect=False)

    def test_invalid_strategy_raises(self, sample_quality_data: pd.DataFrame) -> None:
        """Una estrategia no soportada debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            mask_dataset(
                sample_quality_data, columns=["Email"], strategy="rot13", auto_detect=False
            )

    def test_works_with_csv_input(self, sample_csv_file) -> None:
        """Debe aceptar una ruta a CSV como entrada."""
        result = mask_dataset(
            str(sample_csv_file), columns=["Region"], strategy="partial", auto_detect=False
        )
        assert result["strategy"] == "partial"

    def test_detect_pii_type_email(self) -> None:
        """detect_pii_type debe reconocer un email por su patrón."""
        assert detect_pii_type("john@example.com") == "email"

    def test_mask_value_partial_email(self) -> None:
        """mask_value debe enmascarar parcialmente un email manteniendo el dominio."""
        masked = mask_value("john@example.com", pii_type="email", strategy="partial")
        assert masked.endswith("@example.com")
        assert "*" in masked

    def test_valid_strategies_constant(self) -> None:
        """La constante VALID_STRATEGIES debe contener las tres estrategias."""
        assert {"partial", "full", "hash"} == VALID_STRATEGIES
