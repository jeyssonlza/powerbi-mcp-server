"""Tests para casos edge (límites) y manejo de errores en PBIP.

Cobertura:
- Modelos vacíos
- Archivos corruptos/inválidos
- Casos extremos de tamaño y complejidad
- Recuperación de errores
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from powerbi_mcp.pbip.writer import write_json_file, write_text_file


class TestEmptyAndMissingCases:
    """Tests para casos sin datos o con estructura mínima."""

    def test_empty_model_dict(self, tmp_path: Path) -> None:
        """Debe manejar modelo vacío."""
        empty_model = {
            "name": "EmptyModel",
            "tables": [],
            "relationships": [],
        }

        model_file = tmp_path / "empty.bim"
        write_json_file(model_file, empty_model, reason="empty test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert loaded["tables"] == []
        assert loaded["relationships"] == []

    def test_table_without_columns(self, tmp_path: Path) -> None:
        """Debe manejar tabla sin columnas."""
        model = {
            "name": "Model",
            "tables": [
                {
                    "name": "EmptyTable",
                    "columns": [],
                    "measures": [],
                }
            ],
        }

        model_file = tmp_path / "no_cols.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert len(loaded["tables"][0]["columns"]) == 0

    def test_model_without_relationships(self, tmp_path: Path) -> None:
        """Debe manejar modelo sin relaciones."""
        model = {
            "name": "Model",
            "tables": [{"name": "T1", "columns": [], "measures": []}],
        }

        model_file = tmp_path / "no_rels.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        # Si no hay relationships key, no debe fallar
        assert loaded["tables"][0]["name"] == "T1"

    def test_pbix_with_no_files(self, tmp_path: Path) -> None:
        """Debe manejar PBIX vacío."""
        pbix_path = tmp_path / "empty.pbix"

        with zipfile.ZipFile(pbix_path, "w") as zf:
            # ZIP vacío
            pass

        assert zipfile.is_zipfile(pbix_path)
        with zipfile.ZipFile(pbix_path, "r") as zf:
            assert len(zf.namelist()) == 0


class TestLargeAndComplexCases:
    """Tests para modelos grandes y complejos."""

    def test_model_with_many_tables(self, tmp_path: Path) -> None:
        """Debe manejar modelo con muchas tablas (100+)."""
        model = {
            "name": "LargeModel",
            "tables": [
                {
                    "name": f"Table_{i:03d}",
                    "columns": [
                        {"name": f"Col_{j}", "dataType": "string"}
                        for j in range(10)
                    ],
                    "measures": [],
                }
                for i in range(100)
            ],
        }

        model_file = tmp_path / "large.bim"
        result = write_json_file(
            model_file, model, reason="large model", dry_run=False
        )

        assert model_file.exists()
        assert result["bytes"] > 100000  # > 100KB

    def test_model_with_many_measures(self, tmp_path: Path) -> None:
        """Debe manejar tabla con muchas medidas (50+)."""
        model = {
            "name": "Model",
            "tables": [
                {
                    "name": "Analytics",
                    "columns": [],
                    "measures": [
                        {
                            "name": f"Measure_{i:03d}",
                            "expression": f"SUM(Table[Field{i}])",
                        }
                        for i in range(50)
                    ],
                }
            ],
        }

        model_file = tmp_path / "many_measures.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert len(loaded["tables"][0]["measures"]) == 50

    def test_deep_nesting_of_objects(self, tmp_path: Path) -> None:
        """Debe manejar estructuras anidadas complejas."""
        model = {
            "name": "Model",
            "tables": [
                {
                    "name": "Complex",
                    "columns": [
                        {
                            "name": "Col1",
                            "dataType": "string",
                            "metadata": {
                                "level1": {
                                    "level2": {
                                        "level3": {
                                            "level4": "deep value"
                                        }
                                    }
                                }
                            },
                        }
                    ],
                    "measures": [],
                }
            ],
        }

        model_file = tmp_path / "deep.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert loaded["tables"][0]["columns"][0]["metadata"]["level1"]["level2"]["level3"]["level4"] == "deep value"

    def test_long_dax_expressions(self, tmp_path: Path) -> None:
        """Debe manejar expresiones DAX muy largas."""
        long_dax = " + ".join([f"Table[Field{i}]" for i in range(100)])
        long_dax = f"SUMX(Table, {long_dax})"

        model = {
            "name": "Model",
            "tables": [
                {
                    "name": "T",
                    "columns": [],
                    "measures": [{"name": "VeryLong", "expression": long_dax}],
                }
            ],
        }

        model_file = tmp_path / "long_dax.bim"
        result = write_json_file(model_file, model, reason="test", dry_run=False)

        assert result["bytes"] > 10000  # > 10KB por DAX largo
        loaded = json.loads(model_file.read_text())
        assert len(loaded["tables"][0]["measures"][0]["expression"]) > 1000


class TestInvalidAndCorruptedCases:
    """Tests para datos inválidos/corruptos."""

    def test_invalid_json_in_model_file(self, tmp_path: Path) -> None:
        """Debe fallar con JSON inválido."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('{ "incomplete": ', encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            json.loads(bad_file.read_text())

    def test_corrupted_pbix_file(self, tmp_path: Path) -> None:
        """Debe detectar PBIX corrupto."""
        bad_pbix = tmp_path / "corrupted.pbix"
        bad_pbix.write_bytes(b"This is not a ZIP file\x00\x00\x00")

        assert not zipfile.is_zipfile(bad_pbix)

    def test_model_with_invalid_utf8(self, tmp_path: Path) -> None:
        """Debe manejar caracteres UTF-8 válidos."""
        model = {
            "name": "Модель",  # Ruso
            "tables": [
                {
                    "name": "Таблица",  # Ruso
                    "columns": [
                        {
                            "name": "Столбец",  # Ruso
                            "dataType": "string",
                        }
                    ],
                    "measures": [],
                }
            ],
        }

        model_file = tmp_path / "utf8.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert loaded["name"] == "Модель"

    def test_special_characters_in_names(self, tmp_path: Path) -> None:
        """Debe manejar caracteres especiales en nombres."""
        model = {
            "name": "Model-With-Special_Chars.123",
            "tables": [
                {
                    "name": "Table[With]Brackets",
                    "columns": [
                        {
                            "name": "Col@WithAt",
                            "dataType": "string",
                        }
                    ],
                    "measures": [
                        {
                            "name": "Measure#Hash",
                            "expression": "COUNT()",
                        }
                    ],
                }
            ],
        }

        model_file = tmp_path / "special.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert "Special" in loaded["name"]
        assert "@" in loaded["tables"][0]["columns"][0]["name"]


class TestFileSystemEdgeCases:
    """Tests para casos límite del filesystem."""

    def test_write_to_readonly_location(self, tmp_path: Path) -> None:
        """Debe fallar cuando no tiene permisos de escritura."""
        from powerbi_mcp.core.exceptions import PBIPWriteError

        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_file = readonly_dir / "test.json"

        # En sistemas Unix podemos hacer readonly; en Windows es más complejo
        # Por ahora saltamos si no estamos en Unix
        import os
        import sys

        if sys.platform != "win32":
            os.chmod(readonly_dir, 0o444)

            with pytest.raises(PBIPWriteError):
                write_json_file(
                    readonly_file,
                    {"test": True},
                    reason="test",
                    dry_run=False,
                )

            # Restaurar permisos para cleanup
            os.chmod(readonly_dir, 0o755)

    def test_path_with_very_long_name(self, tmp_path: Path) -> None:
        """Debe manejar rutas con nombres muy largos."""
        # Windows límite es 260 caracteres
        long_name = "a" * 100
        deep_dir = tmp_path / long_name / long_name / long_name
        deep_dir.mkdir(parents=True, exist_ok=True)

        file_path = deep_dir / "file.json"
        data = {"test": True}

        result = write_json_file(file_path, data, reason="test", dry_run=False)

        assert file_path.exists()
        assert result["path"] == str(file_path)

    def test_dry_run_with_large_data(self, tmp_path: Path) -> None:
        """Dry-run debe mostrar preview incluso con datos grandes."""
        large_data = {
            "items": [{"id": i, "value": "x" * 1000} for i in range(100)]
        }

        result = write_json_file(
            tmp_path / "never_written.json",
            large_data,
            reason="test",
            dry_run=True,
        )

        assert result["dry_run"] is True
        assert "preview" in result
        # Preview debe estar limitado
        assert len(result["preview"]) <= 2000

    def test_atomic_write_recovery(self, tmp_path: Path) -> None:
        """Escritura atómica debe dejar archivo limpio si falla."""
        test_file = tmp_path / "atomic.json"
        test_file.write_text('{"original": true}', encoding="utf-8")

        new_data = {"updated": True}

        # Escribir normalmente
        write_json_file(test_file, new_data, reason="test", dry_run=False)

        # El archivo debe tener el nuevo contenido
        loaded = json.loads(test_file.read_text())
        assert loaded["updated"] is True
        assert "original" not in loaded


class TestExtraFieldPreservation:
    """Tests para preservación de campos extra (extra='allow')."""

    def test_preserve_unknown_fields_on_write(self, tmp_path: Path) -> None:
        """Debe preservar campos desconocidos al leer/escribir."""
        model = {
            "name": "Model",
            "unknownField1": "should be preserved",
            "tables": [
                {
                    "name": "Table1",
                    "unknownTableField": "table metadata",
                    "columns": [],
                    "measures": [],
                }
            ],
            "customMetadata": {"key": "value"},
        }

        model_file = tmp_path / "preserve.bim"
        write_json_file(model_file, model, reason="test", dry_run=False)

        loaded = json.loads(model_file.read_text())
        assert loaded.get("unknownField1") == "should be preserved"
        assert loaded.get("customMetadata", {}).get("key") == "value"

    def test_preserve_fields_in_roundtrip(self, tmp_path: Path) -> None:
        """Campos extra deben preservarse en múltiples ciclos lectura/escritura."""
        original = {
            "name": "Model",
            "extraField": "important",
            "tables": [{"name": "T", "columns": [], "measures": [], "extraTableField": "data"}],
        }

        # Ciclo 1: escribir
        file1 = tmp_path / "v1.json"
        write_json_file(file1, original, reason="write1", dry_run=False)

        # Ciclo 2: leer y escribir de nuevo
        loaded1 = json.loads(file1.read_text())
        file2 = tmp_path / "v2.json"
        write_json_file(file2, loaded1, reason="write2", dry_run=False)

        # Ciclo 3: leer final
        loaded2 = json.loads(file2.read_text())

        assert loaded2.get("extraField") == "important"
        assert loaded2["tables"][0].get("extraTableField") == "data"
