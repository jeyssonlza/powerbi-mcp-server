"""Punto de entrada ejecutable del servidor Power BI MCP.

Permite arrancar el servidor con::

    python -m powerbi_mcp

o, si se instaló el paquete, mediante el script de consola::

    powerbi-mcp

El servidor se comunica por transporte ``stdio`` (estándar MCP), por lo que es
compatible con Claude Code, Claude Desktop, VS Code, Antigravity, Codex y
OpenCode sin cambios.
"""

from __future__ import annotations

import argparse
import sys

from powerbi_mcp import __version__


def _build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="powerbi-mcp",
        description="Servidor MCP profesional para proyectos Power BI (PBIP/PBIX).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"powerbi-mcp {__version__}",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transporte de comunicación MCP (por defecto: stdio).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Función principal: parsea argumentos y arranca el servidor MCP.

    Args:
        argv: Lista de argumentos (por defecto ``sys.argv[1:]``).

    Returns:
        Código de salida del proceso (0 = correcto).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Importación diferida para que ``--version``/``--help`` no carguen todo el
    # árbol de dependencias pesadas (pandas, sklearn, etc.).
    from powerbi_mcp.server import run

    try:
        run(transport=args.transport)
        return 0
    except KeyboardInterrupt:  # pragma: no cover - interacción manual
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
