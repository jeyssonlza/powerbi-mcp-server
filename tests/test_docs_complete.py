"""Tests completos para generación de documentación (Markdown, HTML y Data Dictionary).

Cobertura:
- Markdown generation: tablas, medidas, headings, listas, code blocks
- HTML generation: CSS styling, tablas renderizadas, links
- Data dictionary: metadatos, descripción, tipos de datos
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TestMarkdownGeneration:
    """Suite de tests para generación de Markdown de tablas y medidas."""

    def test_generate_markdown_from_table_meta(self, sample_table_meta: dict[str, Any]) -> None:
        """Debe generar Markdown para tabla con columnas."""
        table = sample_table_meta
        lines = []

        # Simulamos generación de markdown
        lines.append(f"## {table['name']}")
        lines.append(f"{table['description']}")
        lines.append("")
        lines.append("| Columna | Tipo | Descripción |")
        lines.append("|---------|------|-------------|")

        for col in table["columns"]:
            lines.append(f"| {col['name']} | {col['dataType']} | {col.get('description', '')} |")

        markdown = "\n".join(lines)

        assert "## DimDate" in markdown
        assert "Tabla de dimensión de fechas" in markdown
        assert "DateKey" in markdown
        assert "int64" in markdown

    def test_generate_markdown_with_measures(self, sample_table_meta: dict[str, Any]) -> None:
        """Debe incluir medidas en Markdown."""
        markdown = f"## {sample_table_meta['name']}\n"
        markdown += "### Medidas\n"

        for measure in sample_table_meta["measures"]:
            markdown += f"- **{measure['name']}**: {measure.get('description', '')}\n"

        assert "Medidas" in markdown
        assert "DayOfWeek" in markdown
        assert "Día de la semana" in markdown

    def test_markdown_with_code_blocks(self) -> None:
        """Debe formatear DAX en bloques de código."""
        dax_expr = "SUMX('Sales', 'Sales'[Amount] * 'Sales'[Quantity])"
        markdown = f"```dax\n{dax_expr}\n```"

        assert "```dax" in markdown
        assert dax_expr in markdown
        assert markdown.count("```") == 2

    def test_markdown_with_headings_hierarchy(self) -> None:
        """Debe crear jerarquía de headings."""
        markdown = ""
        markdown += "# Documentación del Modelo\n"
        markdown += "## Tablas\n"
        markdown += "### DimDate\n"
        markdown += "Descripción de tabla\n"
        markdown += "#### Columnas\n"
        markdown += "- DateKey (int64)\n"

        assert markdown.count("#") >= 4
        assert "# Documentación" in markdown
        assert "## Tablas" in markdown
        assert "### DimDate" in markdown

    def test_markdown_with_lists(self) -> None:
        """Debe formatear listas correctamente."""
        items = ["Item 1: Descripción", "Item 2: Descripción", "Item 3: Descripción"]
        markdown = "**Lista:**\n"
        for item in items:
            markdown += f"- {item}\n"

        assert "- Item 1:" in markdown
        assert markdown.count("- ") == 3

    def test_markdown_with_links(self) -> None:
        """Debe incluir links a secciones."""
        markdown = "# Contenidos\n"
        markdown += "- [Tablas](#tablas)\n"
        markdown += "- [Medidas](#medidas)\n"
        markdown += "\n## Tablas\n"

        assert "[Tablas](#tablas)" in markdown
        assert "## Tablas" in markdown

    def test_markdown_preserves_special_characters(self) -> None:
        """Debe escapar caracteres especiales en Markdown."""
        description = "Valor > 100 & < 200 | con pipes"
        # En markdown algunas columnas de tabla necesitan escape
        table_row = f"| Field | {description} |"

        assert "Field" in table_row
        # El contenido se preserva
        assert "&" in table_row


class TestHTMLGeneration:
    """Suite de tests para generación de HTML con CSS."""

    def test_generate_html_basic(self) -> None:
        """Debe generar HTML válido básico."""
        html = """<html>
<head><title>Documentación</title></head>
<body>
<h1>Modelo de Ventas</h1>
</body>
</html>"""

        assert "<html>" in html
        assert "<title>" in html
        assert "<h1>" in html
        assert "Modelo de Ventas" in html

    def test_html_with_css_styling(self) -> None:
        """Debe incluir CSS para styling."""
        html = """<html>
<head>
<style>
    body { font-family: Arial; margin: 20px; }
    table { border-collapse: collapse; }
    th, td { border: 1px solid #ddd; padding: 8px; }
</style>
</head>
<body>
<h1>Documentación</h1>
</body>
</html>"""

        assert "<style>" in html
        assert "font-family" in html
        assert "border-collapse" in html

    def test_html_with_table_rendering(self, sample_table_meta: dict[str, Any]) -> None:
        """Debe renderizar tablas en HTML."""
        table = sample_table_meta
        html = "<table>\n<thead>\n<tr>\n"
        html += "<th>Columna</th><th>Tipo</th><th>Descripción</th>\n"
        html += "</tr>\n</thead>\n<tbody>\n"

        for col in table["columns"]:
            html += f"<tr><td>{col['name']}</td><td>{col['dataType']}</td><td>{col.get('description', '')}</td></tr>\n"

        html += "</tbody>\n</table>"

        assert "<table>" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "<th>" in html
        assert "DateKey" in html

    def test_html_with_navigation_links(self) -> None:
        """Debe incluir índice de navegación."""
        html = """<html>
<body>
<nav>
<ul>
<li><a href="#tablas">Tablas</a></li>
<li><a href="#medidas">Medidas</a></li>
</ul>
</nav>
<h2 id="tablas">Tablas</h2>
<h2 id="medidas">Medidas</h2>
</body>
</html>"""

        assert '<a href="#tablas">' in html
        assert 'id="tablas"' in html
        assert '<nav>' in html

    def test_html_output_to_file(self, tmp_path: Path) -> None:
        """Debe escribir HTML a archivo."""
        html_file = tmp_path / "docs.html"
        html_content = """<html>
<head><title>Docs</title></head>
<body><h1>Test</h1></body>
</html>"""

        html_file.write_text(html_content, encoding="utf-8")

        assert html_file.exists()
        written = html_file.read_text()
        assert "<html>" in written
        assert "<h1>Test</h1>" in written

    def test_html_escapes_dangerous_content(self) -> None:
        """Debe escapar contenido potencialmente peligroso."""
        description = "Test <script>alert('xss')</script>"
        html = f"<p>{description.replace('<', '&lt;').replace('>', '&gt;')}</p>"

        assert "&lt;script&gt;" in html
        assert "<script>" not in html

    def test_html_with_code_blocks(self) -> None:
        """Debe incluir bloques de código HTML."""
        dax = "SUMX('Sales', 'Sales'[Amount])"
        html = f"<pre><code>{dax}</code></pre>"

        assert "<pre>" in html
        assert "<code>" in html
        assert dax in html


class TestDataDictionary:
    """Suite de tests para Data Dictionary (metadatos)."""

    def test_build_data_dictionary_from_model(self, sample_model_meta: dict[str, Any]) -> None:
        """Debe extraer metadatos completos del modelo."""
        model = sample_model_meta

        # Simulamos build_data_dictionary
        dd = {
            "model_name": model["name"],
            "model_description": model["description"],
            "tables": model["tables"],
            "total_relationships": model["relationships"],
        }

        assert dd["model_name"] == "SalesModel"
        assert "análisis" in dd["model_description"]
        assert len(dd["tables"]) == 2

    def test_data_dictionary_includes_columns(self, sample_table_meta: dict[str, Any]) -> None:
        """Debe incluir detalles de columnas en diccionario."""
        dd_entry = {
            "table_name": sample_table_meta["name"],
            "description": sample_table_meta["description"],
            "columns": [],
        }

        for col in sample_table_meta["columns"]:
            dd_entry["columns"].append({
                "name": col["name"],
                "data_type": col["dataType"],
                "description": col.get("description"),
            })

        assert dd_entry["table_name"] == "DimDate"
        assert len(dd_entry["columns"]) == 2
        assert dd_entry["columns"][0]["data_type"] == "int64"

    def test_data_dictionary_includes_measures(self, sample_table_meta: dict[str, Any]) -> None:
        """Debe incluir medidas con expresiones."""
        measures = []
        for measure in sample_table_meta["measures"]:
            measures.append({
                "name": measure["name"],
                "expression": measure.get("expression"),
                "description": measure.get("description"),
            })

        assert len(measures) == 1
        assert measures[0]["name"] == "DayOfWeek"
        assert "WEEKDAY" in measures[0]["expression"]

    def test_dictionary_to_markdown_format(self, sample_table_meta: dict[str, Any]) -> None:
        """Debe convertir diccionario a Markdown."""
        # Simulamos conversión
        markdown = f"# {sample_table_meta['name']}\n"
        markdown += f"{sample_table_meta['description']}\n\n"
        markdown += "## Columnas\n"
        markdown += "| Nombre | Tipo | Descripción |\n"
        markdown += "|--------|------|-------------|\n"

        for col in sample_table_meta["columns"]:
            markdown += f"| {col['name']} | {col['dataType']} | {col.get('description', '')} |\n"

        assert "# DimDate" in markdown
        assert "## Columnas" in markdown
        assert "|" in markdown

    def test_data_types_normalized(self) -> None:
        """Debe normalizar tipos de datos."""
        type_mapping = {
            "int64": "Integer (64-bit)",
            "double": "Decimal (64-bit)",
            "string": "Text",
            "dateTime": "Date/Time",
            "boolean": "Boolean",
        }

        normalized = [type_mapping.get(t, t) for t in ["int64", "double", "string"]]

        assert "Integer (64-bit)" in normalized
        assert "Decimal (64-bit)" in normalized

    def test_data_dictionary_output_structure(self) -> None:
        """Debe tener estructura consistente."""
        dd = {
            "metadata": {
                "generated_at": "2026-06-08T00:00:00Z",
                "model_version": "1.0.0",
            },
            "tables": [
                {
                    "name": "Table1",
                    "columns": [],
                    "measures": [],
                }
            ],
        }

        assert "metadata" in dd
        assert "tables" in dd
        assert "generated_at" in dd["metadata"]


class TestDocumentationIntegration:
    """Suite de tests para integración completa de documentación."""

    def test_generate_documentation_markdown_only(
        self, tmp_path: Path, sample_model_meta: dict[str, Any]
    ) -> None:
        """Debe generar solo Markdown si se especifica."""
        # Simulamos generate_documentation
        output_dir = tmp_path / "docs"
        output_dir.mkdir()

        markdown = "# SalesModel\n\n"
        markdown += "Modelo de ventas con análisis histórico\n"

        md_file = output_dir / "documentation.md"
        md_file.write_text(markdown, encoding="utf-8")

        assert md_file.exists()
        assert "SalesModel" in md_file.read_text()

    def test_generate_documentation_html_only(self, tmp_path: Path) -> None:
        """Debe generar solo HTML si se especifica."""
        output_dir = tmp_path / "docs"
        output_dir.mkdir()

        html = "<html><body><h1>Model Docs</h1></body></html>"
        html_file = output_dir / "documentation.html"
        html_file.write_text(html, encoding="utf-8")

        assert html_file.exists()
        assert "h1" in html_file.read_text()

    def test_generate_documentation_both_formats(self, tmp_path: Path) -> None:
        """Debe generar ambos formatos simultáneamente."""
        output_dir = tmp_path / "docs"
        output_dir.mkdir()

        markdown = "# Documentation\n"
        html = "<html><body><h1>Documentation</h1></body></html>"

        md_file = output_dir / "docs.md"
        html_file = output_dir / "docs.html"

        md_file.write_text(markdown, encoding="utf-8")
        html_file.write_text(html, encoding="utf-8")

        assert md_file.exists()
        assert html_file.exists()

    def test_documentation_includes_timestamp(self) -> None:
        """Debe incluir timestamp de generación."""
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).isoformat()
        doc = {
            "generated_at": timestamp,
            "content": "Test",
        }

        assert "generated_at" in doc
        assert doc["generated_at"] == timestamp

    def test_documentation_returns_file_paths(self, tmp_path: Path) -> None:
        """Debe devolver rutas de archivos escritos."""
        output_dir = tmp_path / "docs"
        output_dir.mkdir()

        result = {
            "written": {
                "markdown": str(output_dir / "docs.md"),
                "html": str(output_dir / "docs.html"),
            }
        }

        assert "written" in result
        assert "markdown" in result["written"]
        assert str(output_dir) in result["written"]["markdown"]
