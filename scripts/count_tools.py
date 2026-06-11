"""Cuenta las herramientas MCP registradas en el servidor Power BI MCP.

Recorre ``src/powerbi_mcp/tools/*_tools.py`` y cuenta las funciones decoradas
con ``@mcp.tool()``, agrupándolas por dominio. Es la fuente de verdad para el
número de herramientas: úsalo antes de actualizar README, mcp-manifest.json o
la documentación, para evitar inconsistencias de conteo.

Uso:
    python scripts/count_tools.py
"""

from __future__ import annotations

import ast
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent / "src" / "powerbi_mcp" / "tools"


def _is_mcp_tool(decorator: ast.expr) -> bool:
    """Indica si un decorador es ``@mcp.tool`` o ``@mcp.tool(...)``."""
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(node, ast.Attribute) and node.attr == "tool"


def count_tools() -> dict[str, list[str]]:
    """Devuelve ``{dominio: [nombres de herramientas]}`` leyendo el código real."""
    result: dict[str, list[str]] = {}
    for path in sorted(TOOLS_DIR.glob("*_tools.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and any(
                _is_mcp_tool(d) for d in node.decorator_list
            ):
                names.append(node.name)
        result[path.stem.replace("_tools", "")] = sorted(names)
    return result


def main() -> int:
    tools = count_tools()
    total = sum(len(v) for v in tools.values())
    print(f"Power BI MCP - herramientas registradas (@mcp.tool): {total}\n")
    for domain, names in tools.items():
        print(f"  {domain:<10} {len(names):>3}")
    print(f"  {'-' * 14}")
    print(f"  {'TOTAL':<10} {total:>3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
