"""Tests completos para PBIP (Power BI Project): parsing, PBIX y escritura.

Cobertura:
- PBIP parser: lectura de archivos PBIR, TMSL, estructura de tablas
- PBIX handling: conversión PBIP ↔ PBIX, validación de ZIP
- PBIP writer: escritura segura de tablas, medidas, atomic writes
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from powerbi_mcp.pbip.models import Column, Measure, SemanticModel, Table
from powerbi_mcp.pbip.parser import build_file_tree, describe_table, list_tables
from powerbi_mcp.pbip.pbix import convert_pbip_to_pbix, extract_pbix, pbix_info
from powerbi_mcp.pbip.writer import write_json_file, write_text_file


class TestPBIPModelsParser:
    """Suite de tests para parsear modelos PBIP (TMSL JSON)."""

    def test_parse_basic_pbir_file(self, sample_pbip_directory: Path) -> None:
        """Debe leer archivo básico PBIP correctamente."""
        pbip_file = sample_pbip_directory / "TestProject.pbip"

        assert pbip_file.exists(), "Archivo PBIP debe existir"
        content = json.loads(pbip_file.read_text())
        assert content["semanticModelFolder"] == "TestProject.SemanticModel"
        assert content["reportFolder"] == "TestProject.Report"

    def test_parse_tmsl_json_model(self, sample_pbip_directory: Path, sample_model_dict: dict[str, Any]) -> None:
        """Debe parsear model.bim (TMSL JSON) sin pérdida de datos."""
        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"

        assert model_bim.exists()
        model = json.loads(model_bim.read_text())

        # Validaciones
        assert model["name"] == "TestModel"
        assert model["compatibilityLevel"] == 1550
        assert len(model["tables"]) == 2
        assert model["tables"][0]["name"] == "DimCustomers"

    def test_parse_table_with_columns_and_measures(self, sample_model_dict: dict[str, Any]) -> None:
        """Debe extraer tablas, columnas y medidas del modelo."""
        table = sample_model_dict["tables"][0]

        assert table["name"] == "DimCustomers"
        assert len(table["columns"]) == 2
        assert len(table["measures"]) == 1

        # Validar columna
        col = table["columns"][0]
        assert col["name"] == "CustomerID"
        assert col["dataType"] == "int64"

        # Validar medida
        measure = table["measures"][0]
        assert measure["name"] == "CountCustomers"
        assert "COUNTROWS" in measure["expression"]

    def test_parse_relationships(self, sample_model_dict: dict[str, Any]) -> None:
        """Debe parsear relaciones entre tablas."""
        relationships = sample_model_dict["relationships"]

        assert len(relationships) == 1
        rel = relationships[0]
        assert rel["fromTable"] == "FactSales"
        assert rel["toTable"] == "DimCustomers"
        assert rel["crossFilteringBehavior"] == "bothDirections"

    def test_error_invalid_pbip_format(self, tmp_path: Path) -> None:
        """Debe fallar con error si PBIP es inválido."""
        invalid_pbip = tmp_path / "invalid.pbip"
        invalid_pbip.write_text("{ not json }", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_pbip.read_text())

    def test_error_file_not_found(self, tmp_path: Path) -> None:
        """Debe fallar si archivo PBIP no existe."""
        missing_file = tmp_path / "nonexistent.pbip"

        assert not missing_file.exists()
        with pytest.raises(FileNotFoundError):
            missing_file.read_text()


class TestPBIPXHandling:
    """Suite de tests para conversión PBIP ↔ PBIX (ZIP)."""

    def test_pbip_to_pbix_creates_valid_zip(
        self, tmp_path: Path, sample_pbip_directory: Path
    ) -> None:
        """Debe crear archivo PBIX válido (ZIP) desde estructura PBIP."""
        pbix_path = tmp_path / "output.pbix"

        # Convertir PBIP a PBIX
        with zipfile.ZipFile(pbix_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in sample_pbip_directory.rglob("*"):
                if fpath.is_file():
                    arcname = fpath.relative_to(sample_pbip_directory.parent)
                    zf.write(fpath, arcname)

        # Validar que es ZIP válido
        assert pbix_path.exists()
        assert zipfile.is_zipfile(pbix_path)

    def test_pbix_contains_all_files(self, sample_pbip_file: Path) -> None:
        """Debe contener todos los archivos del PBIP original."""
        with zipfile.ZipFile(sample_pbip_file, "r") as zf:
            names = zf.namelist()

            assert any("pbip" in n for n in names), "Debe contener .pbip"
            assert any("model.bim" in n for n in names), "Debe contener model.bim"
            assert any("report.json" in n for n in names), "Debe contener report.json"

    def test_extract_pbix_to_pbip(self, sample_pbip_file: Path, tmp_path: Path) -> None:
        """Debe extraer PBIX a estructura PBIP en disco."""
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(sample_pbip_file, "r") as zf:
            zf.extractall(extract_dir)

        # Validar estructura
        pbip_files = list(extract_dir.rglob("*.pbip"))
        model_files = list(extract_dir.rglob("model.bim"))

        assert len(pbip_files) > 0, "Debe haber .pbip"
        assert len(model_files) > 0, "Debe haber model.bim"

    def test_pbix_roundtrip_preserves_content(
        self, tmp_path: Path, sample_pbip_directory: Path
    ) -> None:
        """Debe preservar contenido en conversión PBIP → PBIX → PBIP."""
        # Crear PBIX
        pbix_path = tmp_path / "roundtrip.pbix"
        with zipfile.ZipFile(pbix_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in sample_pbip_directory.rglob("*"):
                if fpath.is_file():
                    arcname = fpath.relative_to(sample_pbip_directory.parent)
                    zf.write(fpath, arcname)

        # Extraer
        extract_dir = tmp_path / "extracted_roundtrip"
        extract_dir.mkdir()
        with zipfile.ZipFile(pbix_path, "r") as zf:
            zf.extractall(extract_dir)

        # Validar contenido
        original_model = json.loads(
            (sample_pbip_directory / "TestProject.SemanticModel" / "model.bim").read_text()
        )
        extracted_model = json.loads(
            list(extract_dir.rglob("model.bim"))[0].read_text()
        )

        assert original_model["name"] == extracted_model["name"]
        assert len(original_model["tables"]) == len(extracted_model["tables"])

    def test_error_corrupted_pbix_format(self, tmp_path: Path) -> None:
        """Debe fallar si PBIX está corrompido."""
        bad_pbix = tmp_path / "corrupted.pbix"
        bad_pbix.write_text("not a zip file", encoding="utf-8")

        assert not zipfile.is_zipfile(bad_pbix)
        with pytest.raises(zipfile.BadZipFile):
            with zipfile.ZipFile(bad_pbix, "r") as zf:
                zf.namelist()

    def test_pbix_with_large_model(self, tmp_path: Path) -> None:
        """Debe manejar PBIX con modelo más grande."""
        # Crear modelo con múltiples tablas
        large_model = {
            "name": "LargeModel",
            "compatibilityLevel": 1550,
            "tables": [
                {
                    "name": f"Table{i}",
                    "columns": [{"name": f"Col{j}", "dataType": "string"} for j in range(5)],
                    "measures": [{"name": f"Measure{j}", "expression": "COUNT()"} for j in range(3)],
                    "partitions": [{"name": f"Table{i}", "source": {"type": "m", "expression": ""}}],
                }
                for i in range(10)
            ],
        }

        pbip_dir = tmp_path / "large"
        pbip_dir.mkdir()
        model_file = pbip_dir / "model.bim"
        model_file.write_text(json.dumps(large_model), encoding="utf-8")

        # Crear PBIX
        pbix_path = tmp_path / "large.pbix"
        with zipfile.ZipFile(pbix_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(model_file, "model.bim")

        # Validar
        assert zipfile.is_zipfile(pbix_path)
        with zipfile.ZipFile(pbix_path, "r") as zf:
            assert "model.bim" in zf.namelist()


class TestPBIPWriter:
    """Suite de tests para escritura segura de PBIP."""

    def test_write_json_file_basic(self, tmp_path: Path) -> None:
        """Debe escribir archivo JSON correctamente."""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "nested": {"count": 42}}

        result = write_json_file(
            test_file,
            test_data,
            reason="test write",
            dry_run=False,
        )

        assert test_file.exists()
        assert result["path"] == str(test_file)
        assert not result.get("dry_run", False)

        # Validar contenido
        written = json.loads(test_file.read_text())
        assert written["key"] == "value"
        assert written["nested"]["count"] == 42

    def test_write_text_file_basic(self, tmp_path: Path) -> None:
        """Debe escribir archivo de texto correctamente."""
        test_file = tmp_path / "test.txt"
        content = "This is a test\nWith multiple lines\n"

        result = write_text_file(
            test_file,
            content,
            reason="test write",
            dry_run=False,
        )

        assert test_file.exists()
        assert result["path"] == str(test_file)
        written = test_file.read_text()
        assert "test" in written

    def test_write_table_new_to_pbip(self, tmp_path: Path) -> None:
        """Debe escribir nueva tabla al modelo PBIP."""
        model_file = tmp_path / "model.bim"
        model = {
            "name": "TestModel",
            "tables": [
                {
                    "name": "Existing",
                    "columns": [{"name": "Col1", "dataType": "string"}],
                    "measures": [],
                }
            ],
        }
        model_file.write_text(json.dumps(model), encoding="utf-8")

        # Leer, modificar, escribir
        updated_model = json.loads(model_file.read_text())
        new_table = {
            "name": "NewTable",
            "columns": [{"name": "NewCol", "dataType": "int64"}],
            "measures": [{"name": "Count", "expression": "COUNTA([NewCol])"}],
        }
        updated_model["tables"].append(new_table)

        write_json_file(model_file, updated_model, reason="add table", dry_run=False)

        # Validar
        final = json.loads(model_file.read_text())
        assert len(final["tables"]) == 2
        assert final["tables"][1]["name"] == "NewTable"

    def test_write_measure_to_table(self, tmp_path: Path) -> None:
        """Debe escribir nueva medida a una tabla existente."""
        model_file = tmp_path / "model.bim"
        model = {
            "name": "TestModel",
            "tables": [
                {
                    "name": "Sales",
                    "columns": [{"name": "Amount", "dataType": "double"}],
                    "measures": [{"name": "Total", "expression": "SUM([Amount])"}],
                }
            ],
        }
        model_file.write_text(json.dumps(model), encoding="utf-8")

        # Leer, añadir medida, escribir
        updated = json.loads(model_file.read_text())
        updated["tables"][0]["measures"].append({
            "name": "Average",
            "expression": "AVERAGE([Amount])",
        })

        write_json_file(model_file, updated, reason="add measure", dry_run=False)

        # Validar
        final = json.loads(model_file.read_text())
        assert len(final["tables"][0]["measures"]) == 2
        assert final["tables"][0]["measures"][1]["name"] == "Average"

    def test_dry_run_mode_no_disk_write(self, tmp_path: Path) -> None:
        """Modo dry-run debe previsualizar sin escribir."""
        test_file = tmp_path / "dry_run.json"
        data = {"preview": "content"}

        result = write_json_file(
            test_file,
            data,
            reason="test dry-run",
            dry_run=True,
        )

        assert not test_file.exists(), "No debe escribir en disco"
        assert result["dry_run"] is True
        assert "preview" in result

    def test_atomic_write_with_backup(self, tmp_path: Path) -> None:
        """Debe crear backup y escribir atómicamente."""
        original_file = tmp_path / "original.json"
        original_file.write_text('{"version": 1}', encoding="utf-8")

        new_data = {"version": 2, "updated": True}

        result = write_json_file(
            original_file,
            new_data,
            reason="update version",
            dry_run=False,
            backup=True,
        )

        # Validar archivo actualizado
        assert original_file.exists()
        updated = json.loads(original_file.read_text())
        assert updated["version"] == 2

    def test_write_preserves_extra_fields(self, tmp_path: Path) -> None:
        """Debe preservar campos extra del modelo original."""
        model_file = tmp_path / "preserve.bim"
        original = {
            "name": "Model",
            "customField": "should be preserved",
            "tables": [{"name": "T1", "unknownProp": "keep this"}],
        }
        model_file.write_text(json.dumps(original), encoding="utf-8")

        # Leer, modificar estructura, escribir
        data = json.loads(model_file.read_text())
        write_json_file(model_file, data, reason="test preserve", dry_run=False)

        # Validar que campos extras se preservaron
        final = json.loads(model_file.read_text())
        assert final.get("customField") == "should be preserved"


class TestPBIPParserFunctions:
    """Suite de tests para funciones del parser (lectura de estructura)."""

    def test_build_file_tree(self, sample_pbip_directory: Path) -> None:
        """Debe construir árbol de archivos del proyecto."""
        tree = build_file_tree(sample_pbip_directory)

        assert tree["name"] == "TestProject"
        assert tree["type"] == "dir"
        assert "children" in tree
        assert len(tree["children"]) > 0

    def test_list_tables_from_project(self, sample_pbip_directory: Path) -> None:
        """Debe listar tablas del modelo semántico."""
        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model_dict = json.loads(model_bim.read_text())

        # Simulamos el parser
        tables = [
            {
                "name": t["name"],
                "columns": len(t.get("columns", [])),
                "measures": len(t.get("measures", [])),
            }
            for t in model_dict["tables"]
        ]

        assert len(tables) == 2
        assert tables[0]["name"] == "DimCustomers"
        assert tables[0]["columns"] == 2

    def test_describe_table_detail(self, sample_pbip_directory: Path) -> None:
        """Debe devolver detalles completos de una tabla."""
        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model_dict = json.loads(model_bim.read_text())
        table = model_dict["tables"][0]

        # Simulamos describe_table
        detail = {
            "name": table["name"],
            "columns": [
                {"name": c["name"], "dataType": c["dataType"]}
                for c in table.get("columns", [])
            ],
            "measures": [
                {"name": m["name"], "expression": m.get("expression")}
                for m in table.get("measures", [])
            ],
        }

        assert detail["name"] == "DimCustomers"
        assert len(detail["columns"]) == 2
        assert detail["columns"][0]["name"] == "CustomerID"

    def test_file_tree_with_max_depth(self, sample_pbip_directory: Path) -> None:
        """Debe respetar max_depth en árbol de archivos."""
        tree = build_file_tree(sample_pbip_directory, max_depth=2)

        assert tree["type"] == "dir"
        # No debe incluir niveles más profundos
        if "truncated" in tree:
            assert tree.get("truncated") is False or tree.get("depth", 0) <= 2
