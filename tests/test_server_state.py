"""Pruebas de estado de sesión del servidor MCP.

Tras la refactorización, las herramientas se registran como closures vía
``register_*_tools(mcp)``. Aquí se capturan esas funciones reales con un MCP
falso y se ejercitan end-to-end contra la sesión activa, validando que:

- ``dry_run`` no contamina la sesión activa (se descarta al recargar de disco),
- crear una página sincroniza la sesión con el disco.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from powerbi_mcp.config import reload_settings


class _CaptureMCP:
    """MCP falso que captura las funciones decoradas con ``@mcp.tool()``."""

    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, *args, **kwargs):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


def _build_sample_pbip(root: Path) -> Path:
    project_dir = root / "Demo"
    model_dir = project_dir / "Demo.SemanticModel"
    pages_dir = project_dir / "Demo.Report" / "definition" / "pages"
    model_dir.mkdir(parents=True)
    pages_dir.mkdir(parents=True)

    (project_dir / "Demo.pbip").write_text(
        json.dumps({"version": "1.0", "artifacts": [{"report": {"path": "Demo.Report"}}]}),
        encoding="utf-8",
    )
    (model_dir / "model.bim").write_text(
        json.dumps(
            {
                "name": "Demo",
                "model": {
                    "culture": "es-ES",
                    "tables": [
                        {
                            "name": "Ventas",
                            "columns": [
                                {"name": "Importe", "dataType": "double"},
                                {"name": "ProductoID", "dataType": "int64"},
                            ],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    return project_dir


@pytest.fixture()
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Captura las herramientas reales y abre un proyecto PBIP de muestra."""
    monkeypatch.setenv("PBIMCP_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("PBIMCP_LOG_DIR", str(tmp_path / "logs"))
    reload_settings()

    import powerbi_mcp.security.audit as audit_mod
    from powerbi_mcp.session import session
    from powerbi_mcp.tools.model_tools import register_model_tools
    from powerbi_mcp.tools.visuals_tools import register_visuals_tools

    audit_mod._default_logger = None

    cap = _CaptureMCP()
    register_model_tools(cap)
    register_visuals_tools(cap)

    session.close()
    project_dir = _build_sample_pbip(tmp_path)
    session.open(str(project_dir))
    yield cap.tools
    session.close()


def test_model_dry_run_does_not_mutate_active_session(tools) -> None:
    """Una medida con dry_run no debe persistir ni quedar en la sesión recargada."""
    result = tools["add_measure"](
        "Ventas", "Dry Run Measure", "SUM(Ventas[Importe])", dry_run=True
    )
    measures = tools["list_measures"]()["measures"]

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert all(m["name"] != "Dry Run Measure" for m in measures)


def test_create_page_syncs_active_session(tools) -> None:
    """Crear una página debe persistir y reflejarse en la sesión activa."""
    created = tools["create_page"]("Resumen Ejecutivo")
    pages = tools["list_pages"]()["pages"]

    assert created["ok"] is True
    assert any(p["display_name"] == "Resumen Ejecutivo" for p in pages)
