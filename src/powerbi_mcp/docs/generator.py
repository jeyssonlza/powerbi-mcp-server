"""Generación de documentación técnica completa de proyectos Power BI.

Produce un documento profesional (Markdown y/o HTML) que cubre:

- Portada y resumen ejecutivo del proyecto.
- Inventario del modelo (tablas, columnas, medidas, relaciones).
- Diagnósticos integrados (esquema, relaciones, buenas prácticas).
- Documentación del reporte (páginas y visuales).

Sigue estándares de documentación de proyectos de datos: estructura clara,
diccionario de datos y trazabilidad.
"""

from __future__ import annotations

import html as html_lib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from powerbi_mcp.analysis.best_practices import run_best_practices
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.docs.data_dictionary import build_data_dictionary, dictionary_to_markdown
from powerbi_mcp.model.relationships import classify_schema, diagnose_relationships
from powerbi_mcp.pbip.models import PbipProject

logger = get_logger(__name__)


def generate_documentation(
    project: PbipProject,
    *,
    output_dir: str | Path | None = None,
    formats: list[str] | None = None,
    include_best_practices: bool = True,
) -> dict[str, Any]:
    """Genera la documentación técnica del proyecto.

    Args:
        project: Proyecto cargado.
        output_dir: Carpeta donde escribir los archivos. Si es ``None``, no se
            escribe a disco y solo se devuelve el contenido.
        formats: Formatos a generar (``"markdown"``, ``"html"``). Por defecto
            ambos.
        include_best_practices: Si es ``True``, incluye el análisis BPA.

    Returns:
        Diccionario con el contenido generado y, si aplica, las rutas escritas.
    """
    formats = formats or ["markdown", "html"]
    context = _build_context(project, include_best_practices)

    markdown = _render_markdown(context)
    result: dict[str, Any] = {"formats": formats}

    if output_dir:
        out = Path(output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)
        written: dict[str, str] = {}
        if "markdown" in formats:
            md_path = out / f"{project.name}_documentation.md"
            md_path.write_text(markdown, encoding="utf-8")
            written["markdown"] = str(md_path)
        if "html" in formats:
            html_doc = _render_html(context, markdown)
            html_path = out / f"{project.name}_documentation.html"
            html_path.write_text(html_doc, encoding="utf-8")
            written["html"] = str(html_path)
        result["written"] = written
        logger.info("Documentación generada en %s", out)
    else:
        result["markdown"] = markdown
        if "html" in formats:
            result["html"] = _render_html(context, markdown)

    return result


def _build_context(project: PbipProject, include_bpa: bool) -> dict[str, Any]:
    """Reúne toda la información necesaria para documentar el proyecto."""
    model = project.semantic_model
    context: dict[str, Any] = {
        "project": project,
        "summary": project.summary(),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "dictionary": build_data_dictionary(model) if model else {},
    }
    if model:
        context["schema"] = classify_schema(model)
        context["relationships_diag"] = diagnose_relationships(model)
        if include_bpa:
            context["best_practices"] = run_best_practices(model)
    if project.report:
        context["pages"] = [
            {
                "name": p.display_name or p.name,
                "visuals": [
                    {"type": v.visual_type or "desconocido", "name": v.name} for v in p.visuals
                ],
            }
            for p in project.report.pages
        ]
    return context


def _render_markdown(context: dict[str, Any]) -> str:
    """Renderiza el documento Markdown completo."""
    summary = context["summary"]
    parts: list[str] = [
        f"# Documentación técnica — {summary['name']}\n",
        f"> Generado automáticamente el {context['generated_at']} por **powerbi-mcp**.\n",
        "## 1. Resumen ejecutivo\n",
        _summary_table(summary),
    ]

    if "schema" in context:
        schema = context["schema"]
        parts.append("\n## 2. Arquitectura del modelo\n")
        parts.append(f"- **Tipo de esquema:** {schema['schema_type']}")
        parts.append(f"- **Tablas de hechos:** {', '.join(schema['fact_tables']) or '—'}")
        parts.append(f"- **Tablas de dimensión:** {', '.join(schema['dimension_tables']) or '—'}\n")

    if context.get("dictionary"):
        parts.append("\n## 3. Diccionario de datos\n")
        parts.append(dictionary_to_markdown(context["dictionary"]))

    if "relationships_diag" in context:
        parts.append("\n## 4. Diagnóstico de relaciones\n")
        parts.append(_diag_section(context["relationships_diag"]))

    if "best_practices" in context:
        parts.append("\n## 5. Buenas prácticas\n")
        parts.append(_bpa_section(context["best_practices"]))

    if "pages" in context:
        parts.append("\n## 6. Reporte: páginas y visuales\n")
        parts.append(_pages_section(context["pages"]))

    return "\n".join(parts)


def _summary_table(summary: dict[str, Any]) -> str:
    """Renderiza la tabla de resumen ejecutivo."""
    rows = [
        ("Nombre", summary["name"]),
        ("Formato del modelo", summary["model_format"]),
        ("Formato del reporte", summary["report_format"]),
        ("Tablas", summary["tables"]),
        ("Medidas", summary["measures"]),
        ("Relaciones", summary["relationships"]),
        ("Páginas", summary["pages"]),
        ("Visuales", summary["visuals"]),
    ]
    body = "\n".join(f"| {k} | {v} |" for k, v in rows)
    return f"| Métrica | Valor |\n| --- | --- |\n{body}\n"


def _diag_section(diag: dict[str, Any]) -> str:
    """Renderiza la sección de diagnóstico de relaciones."""
    lines = [
        f"- **Total de relaciones:** {diag['total_relationships']}",
        f"- **Relaciones rotas:** {len(diag['broken_relationships'])}",
        f"- **Pares ambiguos:** {len(diag['ambiguous_pairs'])}",
        f"- **Bidireccionales:** {len(diag['bidirectional'])}",
        f"- **Tablas aisladas:** {', '.join(diag['isolated_tables']) or '—'}",
    ]
    return "\n".join(lines) + "\n"


def _bpa_section(bpa: dict[str, Any]) -> str:
    """Renderiza la sección de buenas prácticas."""
    sev = bpa["by_severity"]
    lines = [
        f"Total de hallazgos: **{bpa['total_violations']}** "
        f"(errores: {sev.get('error', 0)}, advertencias: {sev.get('warning', 0)}, "
        f"info: {sev.get('info', 0)}).\n",
    ]
    if bpa["violations"]:
        lines.append("| Severidad | Objeto | Mensaje | Recomendación |")
        lines.append("| --- | --- | --- | --- |")
        for v in bpa["violations"][:50]:
            lines.append(
                f"| {v['severity']} | {v['object_name']} | {v['message']} | {v['recommendation']} |"
            )
    return "\n".join(lines) + "\n"


def _pages_section(pages: list[dict[str, Any]]) -> str:
    """Renderiza la sección de páginas y visuales del reporte."""
    if not pages:
        return "_(sin páginas)_\n"
    lines: list[str] = []
    for page in pages:
        lines.append(f"### Página: {page['name']}\n")
        if page["visuals"]:
            for v in page["visuals"]:
                lines.append(f"- `{v['type']}` ({v['name']})")
        else:
            lines.append("_(sin visuales)_")
        lines.append("")
    return "\n".join(lines)


def _render_html(context: dict[str, Any], markdown: str) -> str:
    """Renderiza el documento HTML con estilo profesional embebido.

    Convierte el Markdown a HTML de forma ligera (encabezados, tablas, listas)
    sin dependencias externas, y lo envuelve en una plantilla con CSS.
    """
    body = _markdown_to_html(markdown)
    title = html_lib.escape(context["summary"]["name"])
    return _HTML_TEMPLATE.format(title=title, body=body, generated=context["generated_at"])


def _markdown_to_html(md: str) -> str:
    """Conversión ligera de un subconjunto de Markdown a HTML."""
    html_lines: list[str] = []
    in_table = False
    in_list = False

    for raw in md.splitlines():
        line = raw.rstrip()

        # Tablas
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue  # fila separadora
            if not in_table:
                html_lines.append("<table>")
                in_table = True
                tag = "th"
            else:
                tag = "td"
            row = "".join(f"<{tag}>{html_lib.escape(c)}</{tag}>" for c in cells)
            html_lines.append(f"<tr>{row}</tr>")
            continue
        if in_table:
            html_lines.append("</table>")
            in_table = False

        # Encabezados
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = html_lib.escape(line.lstrip("# ").strip())
            html_lines.append(f"<h{min(level, 6)}>{text}</h{min(level, 6)}>")
            continue

        # Listas
        if line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline_md(line[2:])}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False

        if line.startswith(">"):
            html_lines.append(f"<blockquote>{_inline_md(line[1:].strip())}</blockquote>")
            continue
        if line:
            html_lines.append(f"<p>{_inline_md(line)}</p>")

    if in_table:
        html_lines.append("</table>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def _inline_md(text: str) -> str:
    """Convierte negrita ``**x**`` y código ``` `x` ``` inline a HTML."""
    import re

    escaped = html_lib.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Documentación — {title}</title>
<style>
  :root {{ --primary: #1F4E79; --accent: #2E75B6; --bg: #f7f9fc; --border: #d9e2ef; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; color: #252423;
         background: var(--bg); margin: 0; padding: 0; line-height: 1.6; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 24px; background: #fff;
               box-shadow: 0 0 24px rgba(0,0,0,.06); }}
  h1 {{ color: var(--primary); border-bottom: 3px solid var(--accent); padding-bottom: 12px; }}
  h2 {{ color: var(--primary); margin-top: 32px; border-left: 4px solid var(--accent);
        padding-left: 12px; }}
  h3 {{ color: var(--accent); }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }}
  th, td {{ border: 1px solid var(--border); padding: 8px 12px; text-align: left; }}
  th {{ background: var(--primary); color: #fff; }}
  tr:nth-child(even) td {{ background: #f2f6fb; }}
  code {{ background: #eef2f7; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
  blockquote {{ border-left: 4px solid var(--accent); margin: 16px 0; padding: 8px 16px;
               background: #eef4fb; color: #444; }}
  footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 40px; }}
</style>
</head>
<body>
  <div class="container">
    {body}
    <footer>Generado el {generated} por powerbi-mcp</footer>
  </div>
</body>
</html>
"""


__all__ = ["generate_documentation"]
