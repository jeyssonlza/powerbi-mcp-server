"""Pruebas unitarias de operaciones sobre el modelo semántico."""

from __future__ import annotations

import pytest

from powerbi_mcp.core.exceptions import DuplicateObjectError, ObjectNotFoundError
from powerbi_mcp.model.measures import add_measure, delete_measure, find_orphan_measures
from powerbi_mcp.model.relationships import add_relationship, classify_schema
from powerbi_mcp.model.tables import add_calculated_table, add_table, rename_table
from powerbi_mcp.pbip.models import Column, SemanticModel, Table


def _model() -> SemanticModel:
    return SemanticModel(
        name="Demo",
        tables=[
            Table(
                name="Ventas",
                columns=[
                    Column(name="Importe", dataType="double"),
                    Column(name="ProductoID", dataType="int64"),
                ],
            ),
            Table(
                name="Producto",
                columns=[Column(name="ProductoID", dataType="int64")],
            ),
        ],
    )


def test_add_measure() -> None:
    model = _model()
    result = add_measure(model, "Ventas", "Total", "SUM(Ventas[Importe])")
    assert result["created"]
    assert model.find_measure("Total") is not None


def test_add_duplicate_measure_raises() -> None:
    model = _model()
    add_measure(model, "Ventas", "Total", "SUM(Ventas[Importe])")
    with pytest.raises(DuplicateObjectError):
        add_measure(model, "Ventas", "Total", "SUM(Ventas[Importe])")


def test_delete_measure() -> None:
    model = _model()
    add_measure(model, "Ventas", "Total", "SUM(Ventas[Importe])")
    delete_measure(model, "Total")
    assert model.find_measure("Total") is None


def test_delete_missing_measure_raises() -> None:
    model = _model()
    with pytest.raises(ObjectNotFoundError):
        delete_measure(model, "NoExiste")


def test_add_table() -> None:
    model = _model()
    add_table(model, "Cliente", m_expression="let Source = ... in Source")
    assert model.get_table("Cliente") is not None


def test_add_calculated_table() -> None:
    model = _model()
    add_calculated_table(model, "Calendario", "CALENDARAUTO()")
    table = model.get_table("Calendario")
    assert table is not None
    assert table.is_calculated_table


def test_rename_table_updates_relationships() -> None:
    model = _model()
    add_relationship(model, "Ventas", "ProductoID", "Producto", "ProductoID")
    rename_table(model, "Producto", "Productos")
    assert model.get_table("Productos") is not None
    assert all(r.to_table != "Producto" for r in model.relationships)


def test_classify_schema_star() -> None:
    model = _model()
    model.tables.append(
        Table(name="Tiempo", columns=[Column(name="FechaID", dataType="int64")])
    )
    model.tables[0].columns.append(Column(name="FechaID", dataType="int64"))
    add_relationship(model, "Ventas", "ProductoID", "Producto", "ProductoID")
    add_relationship(model, "Ventas", "FechaID", "Tiempo", "FechaID")
    result = classify_schema(model)
    assert result["schema_type"] in {"star", "snowflake"}
    assert "Ventas" in result["fact_tables"]


def test_find_orphan_measures() -> None:
    model = _model()
    add_measure(model, "Ventas", "Base", "SUM(Ventas[Importe])")
    add_measure(model, "Ventas", "Doble", "[Base] * 2")
    orphans = find_orphan_measures(model)
    assert "Doble" in orphans  # nadie referencia a Doble
    assert "Base" not in orphans  # Doble referencia a Base
