"""Verifica que ``mcp-manifest.json`` no se desincronice del código real.

Estos tests cuentan las herramientas reales (``@mcp.tool``) y comprueban que el
manifest declare exactamente el mismo total, los mismos dominios y los mismos
nombres. Así, si alguien agrega o elimina una herramienta sin actualizar el
manifest, la suite falla y la inconsistencia se detecta de inmediato.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "src" / "powerbi_mcp" / "tools"
MANIFEST = ROOT / "mcp-manifest.json"


def _is_mcp_tool(decorator: ast.expr) -> bool:
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(node, ast.Attribute) and node.attr == "tool"


def _real_tools() -> dict[str, set[str]]:
    """Mapa ``{dominio: {nombres de herramientas}}`` leído del código."""
    result: dict[str, set[str]] = {}
    for path in sorted(TOOLS_DIR.glob("*_tools.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and any(_is_mcp_tool(d) for d in node.decorator_list)
        }
        result[path.stem.replace("_tools", "")] = names
    return result


def _manifest_tools() -> dict[str, set[str]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {d["name"]: set(d["tools"]) for d in data["tools"]["domains"]}


def test_manifest_total_matches_code() -> None:
    """El ``tools.total`` del manifest debe igualar el conteo real."""
    real_total = sum(len(v) for v in _real_tools().values())
    declared_total = json.loads(MANIFEST.read_text(encoding="utf-8"))["tools"]["total"]
    assert declared_total == real_total, (
        f"Manifest declara {declared_total} herramientas, el código tiene {real_total}."
    )


def test_manifest_domain_counts_match() -> None:
    """La suma de los dominios del manifest debe igualar el total declarado."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    summed = sum(d["count"] for d in data["tools"]["domains"])
    assert summed == data["tools"]["total"]
    for domain in data["tools"]["domains"]:
        assert domain["count"] == len(domain["tools"]), (
            f"Dominio '{domain['name']}': count={domain['count']} pero lista {len(domain['tools'])}."
        )


def test_manifest_tool_names_match_code() -> None:
    """Los nombres de herramientas del manifest deben existir en el código."""
    real = _real_tools()
    declared = _manifest_tools()
    assert set(declared) == set(real), (
        f"Dominios distintos. Manifest: {sorted(declared)} | Código: {sorted(real)}"
    )
    for domain, names in declared.items():
        assert names == real[domain], (
            f"Dominio '{domain}' difiere.\n"
            f"  Solo en manifest: {sorted(names - real[domain])}\n"
            f"  Solo en código:   {sorted(real[domain] - names)}"
        )
