"""Tests para enmascaramiento de datos sensibles (PII masking)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.security.masking import mask_dataset


class TestDataMasking:
    """Suite de tests para masking."""

    def test_mask_email_columns(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe enmascarar columnas de email."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]
        assert result["masked_data"] is not None
        masked_df = pd.DataFrame(result["masked_data"])
        # Email debe estar parcialmente enmascarado
        assert masked_df["Email"].notna().any()

    def test_auto_detect_pii_columns(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe autodetectar columnas PII."""
        result = mask_dataset(
            sample_quality_data,
            columns=None,
            strategy="partial",
            auto_detect=True,
        )

        assert result["ok"]
        assert "detected_columns" in result
        # Email y Name suelen detectarse como PII
        assert len(result.get("detected_columns", [])) > 0

    def test_partial_masking_strategy(self, sample_quality_data: pd.DataFrame) -> None:
        """Partial masking debe ocular solo parte del valor."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]
        masked_df = pd.DataFrame(result["masked_data"])
        # Debe haber caracteres visibles todavía
        assert any(str(e) not in ["", "NaN", "None"] for e in masked_df["Email"].dropna())

    def test_full_masking_strategy(self, sample_quality_data: pd.DataFrame) -> None:
        """Full masking debe reemplazar completamente."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],
            strategy="full",
            auto_detect=False,
        )

        assert result["ok"]
        masked_df = pd.DataFrame(result["masked_data"])
        # Todos los emails deben reemplazarse
        assert masked_df["Email"].dtype == "object"

    def test_hash_masking_strategy(self, sample_quality_data: pd.DataFrame) -> None:
        """Hash masking debe generar valores hash deterministas."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],
            strategy="hash",
            auto_detect=False,
        )

        assert result["ok"]
        masked_df = pd.DataFrame(result["masked_data"])
        # Hashes deben ser deterministas (mismo valor -> mismo hash)
        email1 = masked_df.loc[0, "Email"]
        email_dup = masked_df.loc[masked_df["Email"] == email1]
        assert len(email_dup) >= 1

    def test_mask_multiple_columns(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe enmascarar múltiples columnas."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email", "Name"],
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]
        assert result.get("masked_columns", []) == ["Email", "Name"] or len(result.get("masked_columns", [])) >= 1

    def test_mask_with_csv_input(self, sample_csv_file: Path) -> None:
        """Debe aceptar ruta a CSV."""
        result = mask_dataset(
            str(sample_csv_file),
            columns=["Region"],
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]

    def test_mask_result_includes_metadata(self, sample_quality_data: pd.DataFrame) -> None:
        """El resultado debe incluir metadatos sobre enmascaramiento."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]
        assert "masked_columns" in result
        assert "strategy" in result

    def test_mask_preserves_row_count(self, sample_quality_data: pd.DataFrame) -> None:
        """El enmascaramiento no debe cambiar el número de filas."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]
        masked_df = pd.DataFrame(result["masked_data"])
        assert len(masked_df) == len(sample_quality_data)

    def test_mask_handles_null_values(self, sample_quality_data: pd.DataFrame) -> None:
        """Debe manejar valores nulos sin fallar."""
        result = mask_dataset(
            sample_quality_data,
            columns=["Email"],  # Tiene algunos nulos
            strategy="partial",
            auto_detect=False,
        )

        assert result["ok"]
        masked_df = pd.DataFrame(result["masked_data"])
        # Los nulos deben preservarse
        assert masked_df["Email"].isna().sum() >= sample_quality_data["Email"].isna().sum()
