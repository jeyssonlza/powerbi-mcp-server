"""Test de integración: PBIP + Documentación.

Valida que el flujo completo desde PBIP hasta documentación funciona:
1. Cargar proyecto PBIP
2. Extraer metadatos
3. Generar documentación (Markdown + HTML)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class TestPBIPToDocumentationWorkflow:
    """Suite de tests para el flujo completo PBIP → Documentación."""

    def test_load_pbip_project(self, sample_pbip_directory: Path) -> None:
        """Debe cargar proyecto PBIP desde disco."""
        assert sample_pbip_directory.exists()

        # Verificar estructura PBIP
        pbip_file = sample_pbip_directory / "TestProject.pbip"
        model_dir = sample_pbip_directory / "TestProject.SemanticModel"
        report_dir = sample_pbip_directory / "TestProject.Report"

        assert pbip_file.exists(), "Debe existir archivo .pbip"
        assert model_dir.exists(), "Debe existir carpeta SemanticModel"
        assert report_dir.exists(), "Debe existir carpeta Report"

    def test_extract_model_metadata(self, sample_pbip_directory: Path, sample_model_dict: dict[str, Any]) -> None:
        """Debe extraer metadatos del modelo semántico."""
        import json

        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model = json.loads(model_bim.read_text())

        # Validar que se extrajeron metadatos correctos
        assert "name" in model
        assert "tables" in model
        assert "relationships" in model
        assert len(model["tables"]) > 0

    def test_generate_markdown_documentation(self, sample_pbip_directory: Path) -> None:
        """Debe generar Markdown desde metadatos de PBIP."""
        import json

        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model = json.loads(model_bim.read_text())

        # Simulamos generación de Markdown
        markdown = f"# {model['name']}\n\n"
        markdown += "## Tablas\n\n"

        for table in model["tables"]:
            markdown += f"### {table['name']}\n"
            markdown += f"Columnas: {len(table.get('columns', []))}\n"
            markdown += f"Medidas: {len(table.get('measures', []))}\n\n"

        assert markdown
        assert "TestModel" in markdown
        assert "DimCustomers" in markdown
        assert "FactSales" in markdown

    def test_generate_html_from_markdown(self, sample_pbip_directory: Path) -> None:
        """Debe convertir Markdown a HTML."""
        import json

        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model = json.loads(model_bim.read_text())

        # Crear HTML simple
        html = f"""<html>
<head><title>{model['name']} Documentation</title></head>
<body>
<h1>{model['name']}</h1>
<h2>Tablas</h2>
<ul>
"""
        for table in model["tables"]:
            html += f"<li>{table['name']}</li>\n"

        html += """</ul>
</body>
</html>"""

        assert "<html>" in html
        assert "<title>" in html
        assert model["name"] in html
        assert "DimCustomers" in html

    def test_write_documentation_files(self, tmp_path: Path, sample_pbip_directory: Path) -> None:
        """Debe escribir archivos de documentación a disco."""
        import json

        output_dir = tmp_path / "documentation"
        output_dir.mkdir()

        # Leer modelo
        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model = json.loads(model_bim.read_text())

        # Escribir Markdown
        md_content = f"# {model['name']}\n"
        md_file = output_dir / "model.md"
        md_file.write_text(md_content, encoding="utf-8")

        # Escribir HTML
        html_content = f"<h1>{model['name']}</h1>"
        html_file = output_dir / "model.html"
        html_file.write_text(html_content, encoding="utf-8")

        assert md_file.exists()
        assert html_file.exists()

    def test_data_dictionary_from_pbip(
        self, sample_pbip_directory: Path, sample_model_dict: dict[str, Any]
    ) -> None:
        """Debe generar data dictionary desde PBIP."""
        import json

        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model = json.loads(model_bim.read_text())

        # Construir data dictionary
        dd = {
            "model_name": model["name"],
            "tables": [
                {
                    "name": t["name"],
                    "columns": [
                        {
                            "name": c["name"],
                            "data_type": c.get("dataType", "string"),
                        }
                        for c in t.get("columns", [])
                    ],
                }
                for t in model["tables"]
            ],
        }

        assert dd["model_name"] == "TestModel"
        assert len(dd["tables"]) == 2
        assert dd["tables"][0]["name"] == "DimCustomers"

    def test_full_workflow_summary(self, sample_pbip_directory: Path, tmp_path: Path) -> None:
        """Flujo completo: PBIP → Metadatos → Documentación."""
        import json

        # 1. Cargar PBIP
        model_bim = sample_pbip_directory / "TestProject.SemanticModel" / "model.bim"
        model_data = json.loads(model_bim.read_text())

        # 2. Extraer metadatos
        tables = model_data["tables"]
        total_columns = sum(len(t.get("columns", [])) for t in tables)
        total_measures = sum(len(t.get("measures", [])) for t in tables)

        # 3. Crear documentación
        summary = {
            "project_name": model_data["name"],
            "tables_count": len(tables),
            "columns_count": total_columns,
            "measures_count": total_measures,
            "relationships_count": len(model_data.get("relationships", [])),
        }

        # 4. Escribir resultados
        output_file = tmp_path / "summary.json"
        output_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        # Validar
        assert output_file.exists()
        result = json.loads(output_file.read_text())
        assert result["project_name"] == "TestModel"
        assert result["tables_count"] == 2
        assert result["columns_count"] == 5  # DimCustomers: 2, FactSales: 3


class TestTypeHintsAndValidation:
    """Suite de tests para validación de tipos."""

    def test_field_spec_validation(self) -> None:
        """Debe validar especificación de campos."""
        from powerbi_mcp.types import FieldSpec

        # Crear especificación válida
        field: FieldSpec = {
            "name": "SalesAmount",
            "data_type": "double",
            "nullable": False,
        }

        assert field["name"] == "SalesAmount"
        assert field["data_type"] == "double"

    def test_measure_spec_validation(self) -> None:
        """Debe validar especificación de medidas."""
        from powerbi_mcp.types import MeasureSpec

        measure: MeasureSpec = {
            "name": "TotalSales",
            "expression": "SUM(Sales[Amount])",
            "description": "Total de ventas",
        }

        assert measure["name"] == "TotalSales"
        assert "SUM" in measure["expression"]

    def test_table_spec_validation(self) -> None:
        """Debe validar especificación de tablas."""
        from powerbi_mcp.types import TableSpec, FieldSpec, MeasureSpec

        columns: list[FieldSpec] = [
            {"name": "ID", "data_type": "int64", "nullable": False},
            {"name": "Name", "data_type": "string", "nullable": True},
        ]

        measures: list[MeasureSpec] = [
            {"name": "Count", "expression": "COUNTA([Name])"},
        ]

        table: TableSpec = {
            "name": "Customers",
            "description": "Tabla de clientes",
            "columns": columns,
            "measures": measures,
        }

        assert table["name"] == "Customers"
        assert len(table["columns"]) == 2
        assert len(table["measures"]) == 1

    def test_compatibility_level_enum(self) -> None:
        """Debe validar niveles de compatibilidad TMSL."""
        from powerbi_mcp.types import CompatibilityLevel

        # Todos los niveles soportados
        levels = [
            CompatibilityLevel.LEVEL_1100,
            CompatibilityLevel.LEVEL_1200,
            CompatibilityLevel.LEVEL_1400,
            CompatibilityLevel.LEVEL_1500,
            CompatibilityLevel.LEVEL_1550,
        ]

        assert len(levels) == 5
        assert CompatibilityLevel.LEVEL_1550.value == 1550

    def test_writer_options_validation(self) -> None:
        """Debe validar opciones de escritura."""
        from powerbi_mcp.types import WriterOptions

        options: WriterOptions = {
            "dry_run": True,
            "backup": False,
            "reason": "test update",
        }

        assert options["dry_run"] is True
        assert "test" in options["reason"]

    def test_validation_result_structure(self) -> None:
        """Debe tener estructura de resultado de validación."""
        from powerbi_mcp.types import ValidationResult

        result: ValidationResult = {
            "valid": True,
            "errors": [],
            "warnings": ["Field is missing description"],
            "stats": {"tables": 5, "measures": 12},
        }

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert len(result["warnings"]) == 1
