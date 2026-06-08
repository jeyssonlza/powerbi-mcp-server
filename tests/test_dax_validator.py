"""Pruebas unitarias del validador DAX (no requieren dependencias pesadas)."""

from __future__ import annotations

from powerbi_mcp.model.dax_validator import validate_dax, validate_measure_name
from powerbi_mcp.pbip.models import Column, Measure, SemanticModel, Table


def _sample_model() -> SemanticModel:
    """Construye un modelo mínimo para validación semántica."""
    ventas = Table(
        name="Ventas",
        columns=[Column(name="Importe", dataType="double")],
        measures=[Measure(name="Total Ventas", expression="SUM(Ventas[Importe])")],
    )
    return SemanticModel(name="Demo", tables=[ventas])


def test_valid_expression_passes() -> None:
    result = validate_dax("SUM(Ventas[Importe])")
    assert result.is_valid
    assert not result.errors


def test_unbalanced_parentheses_detected() -> None:
    result = validate_dax("SUM(Ventas[Importe]")
    assert not result.is_valid
    assert any("cierre" in e for e in result.errors)


def test_unbalanced_brackets_detected() -> None:
    result = validate_dax("SUM(Ventas[Importe)")
    assert not result.is_valid


def test_empty_expression_invalid() -> None:
    result = validate_dax("   ")
    assert not result.is_valid


def test_division_best_practice_suggested() -> None:
    result = validate_dax("Ventas[A] / Ventas[B]")
    assert any("DIVIDE" in bp for bp in result.best_practices)


def test_divide_does_not_warn() -> None:
    result = validate_dax("DIVIDE(Ventas[A], Ventas[B])")
    assert not any("DIVIDE" in bp for bp in result.best_practices)


def test_column_reference_extraction() -> None:
    result = validate_dax("SUMX(Ventas, Ventas[Importe] * 2)")
    assert "Ventas[Importe]" in result.referenced_columns


def test_unknown_function_warns() -> None:
    result = validate_dax("SUMA(Ventas[Importe])")
    assert any("SUMA" in w for w in result.warnings)


def test_semantic_check_flags_missing_column() -> None:
    model = _sample_model()
    result = validate_dax("SUM(Ventas[NoExiste])", model=model)
    assert any("NoExiste" in w for w in result.warnings)


def test_semantic_check_accepts_existing_column() -> None:
    model = _sample_model()
    result = validate_dax("SUM(Ventas[Importe])", model=model)
    assert not any("Importe" in w for w in result.warnings)


def test_measure_name_uniqueness() -> None:
    model = _sample_model()
    report = validate_measure_name("Total Ventas", model)
    assert report.has_errors


def test_measure_name_unique_ok() -> None:
    model = _sample_model()
    report = validate_measure_name("Ventas Netas", model)
    assert not report.has_errors
