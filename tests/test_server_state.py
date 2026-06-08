"""Pruebas de estado de sesion del servidor MCP."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from powerbi_mcp.config import reload_settings


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
def configured_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PBIMCP_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("PBIMCP_LOG_DIR", str(tmp_path / "logs"))
    reload_settings()

    import powerbi_mcp.security.audit as audit_mod
    from powerbi_mcp import server

    audit_mod._default_logger = None
    server.close_project()
    project_dir = _build_sample_pbip(tmp_path)
    server.open_project(str(project_dir))
    yield server
    server.close_project()


def test_model_dry_run_does_not_mutate_active_session(configured_server) -> None:
    server = configured_server

    result = server.add_measure("Ventas", "Dry Run Measure", "SUM(Ventas[Importe])", dry_run=True)
    measures = server.list_measures()["measures"]

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert all(m["name"] != "Dry Run Measure" for m in measures)


def test_create_page_syncs_active_session(configured_server) -> None:
    server = configured_server

    created = server.create_page("Resumen Ejecutivo")
    pages = server.list_pages()["pages"]

    assert created["ok"] is True
    assert any(p["display_name"] == "Resumen Ejecutivo" for p in pages)
