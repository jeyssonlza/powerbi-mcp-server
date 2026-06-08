"""Changelog automático por proyecto Power BI.

Registra cada modificación que el servidor aplica a un proyecto (medida añadida,
columna modificada, visual creado...) en un archivo de historial dentro del
propio proyecto, y permite renderizarlo como Markdown siguiendo el estilo
*Keep a Changelog*.

El historial se persiste en ``<proyecto>/.pbip_changelog.json`` y nunca se
sobrescribe: solo se le añaden entradas (append-only), lo que da trazabilidad.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

#: Nombre del archivo de historial dentro del proyecto.
CHANGELOG_FILE = ".pbip_changelog.json"

#: Categorías válidas (estilo Keep a Changelog).
VALID_ACTIONS = frozenset({"added", "changed", "deprecated", "removed", "fixed", "security"})


def record_change(
    project_root: str | Path,
    *,
    action: str,
    object_type: str,
    object_name: str,
    description: str,
    author: str = "powerbi-mcp",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Registra una entrada en el changelog del proyecto.

    Args:
        project_root: Carpeta raíz del proyecto.
        action: Tipo de cambio (ver :data:`VALID_ACTIONS`).
        object_type: Tipo de objeto afectado (``measure``, ``column``...).
        object_name: Nombre del objeto afectado.
        description: Descripción legible del cambio.
        author: Autor/origen del cambio.
        metadata: Información adicional opcional (dry-run, validación...).

    Returns:
        La entrada registrada.
    """
    action = action.lower()
    if action not in VALID_ACTIONS:
        action = "changed"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "object_type": object_type,
        "object_name": object_name,
        "description": description,
        "author": author,
        "metadata": metadata or {},
    }

    path = Path(project_root).expanduser().resolve() / CHANGELOG_FILE
    history = _read_history(path)
    history.append(entry)
    try:
        path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        logger.warning("No se pudo escribir el changelog: %s", exc)

    logger.debug("Cambio registrado: %s %s '%s'", action, object_type, object_name)
    return entry


def get_history(project_root: str | Path) -> list[dict[str, Any]]:
    """Devuelve el historial completo de cambios del proyecto.

    Args:
        project_root: Carpeta raíz del proyecto.

    Returns:
        Lista de entradas, de la más antigua a la más reciente.
    """
    path = Path(project_root).expanduser().resolve() / CHANGELOG_FILE
    return _read_history(path)


def render_markdown(project_root: str | Path, *, project_name: str = "") -> str:
    """Renderiza el changelog del proyecto como Markdown (Keep a Changelog).

    Agrupa las entradas por fecha (día) y, dentro de cada fecha, por tipo de
    acción.

    Args:
        project_root: Carpeta raíz del proyecto.
        project_name: Nombre del proyecto para el encabezado.

    Returns:
        Documento Markdown del changelog.
    """
    history = get_history(project_root)
    title = f"Changelog — {project_name}" if project_name else "Changelog"
    lines = [f"# {title}\n", "Historial de cambios generado automáticamente.\n"]

    if not history:
        lines.append("_(sin cambios registrados)_")
        return "\n".join(lines)

    by_date: dict[str, list[dict[str, Any]]] = {}
    for entry in history:
        day = entry["timestamp"][:10]
        by_date.setdefault(day, []).append(entry)

    action_titles = {
        "added": "Añadido",
        "changed": "Modificado",
        "deprecated": "Obsoleto",
        "removed": "Eliminado",
        "fixed": "Corregido",
        "security": "Seguridad",
    }

    for day in sorted(by_date, reverse=True):
        lines.append(f"\n## {day}\n")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for entry in by_date[day]:
            grouped.setdefault(entry["action"], []).append(entry)
        for action in VALID_ACTIONS:
            if action not in grouped:
                continue
            lines.append(f"### {action_titles.get(action, action.title())}\n")
            for entry in grouped[action]:
                lines.append(
                    f"- **{entry['object_type']}** `{entry['object_name']}`: "
                    f"{entry['description']}"
                )
            lines.append("")

    return "\n".join(lines)


def _read_history(path: Path) -> list[dict[str, Any]]:
    """Lee el historial JSON del proyecto (lista, posiblemente vacía)."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        logger.warning("Changelog corrupto en %s; se ignora.", path)
        return []


__all__ = [
    "CHANGELOG_FILE",
    "VALID_ACTIONS",
    "get_history",
    "record_change",
    "render_markdown",
]
