"""Creación y composición de páginas de reporte en formato PBIR.

Gestiona la estructura en disco de las páginas de un reporte PBIP/PBIR:

- Crear una página nueva (carpeta ``pages/<id>/page.json`` y registro en
  ``pages.json``).
- Añadir visuales a una página (carpeta ``visuals/<id>/visual.json``).
- Calcular *layouts* automáticos (cuadrícula) para distribuir visuales.

Toda escritura pasa por :mod:`powerbi_mcp.pbip.writer` (respaldo + dry-run).
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from powerbi_mcp.core.exceptions import PBIPNotFoundError, ValidationError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.core.validators import slugify
from powerbi_mcp.pbip.models import PbipProject
from powerbi_mcp.pbip.writer import write_json_file

logger = get_logger(__name__)

#: Esquema PBIR de una página.
_PAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/1.0.0/schema.json"
)


def create_page(
    project: PbipProject,
    display_name: str,
    *,
    width: float = 1280.0,
    height: float = 720.0,
    page_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Crea una página nueva en el reporte PBIR del proyecto.

    Args:
        project: Proyecto destino (debe tener reporte PBIR).
        display_name: Nombre visible de la pestaña.
        width: Ancho del lienzo (px).
        height: Alto del lienzo (px).
        page_id: Identificador interno. Si es ``None``, se deriva del nombre.
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.

    Returns:
        Diccionario con el ``page_id`` y el resultado de escritura.

    Raises:
        PBIPNotFoundError: Si el proyecto no tiene ruta de reporte.
        ValidationError: Si el nombre es inválido.
    """
    if not display_name.strip():
        raise ValidationError("El nombre de la página no puede estar vacío.")
    report_dir = _require_report_dir(project)

    pid = page_id or slugify(display_name) or uuid.uuid4().hex[:12]
    page_dir = report_dir / "definition" / "pages" / pid

    page_json = {
        "$schema": _PAGE_SCHEMA,
        "name": pid,
        "displayName": display_name,
        "width": width,
        "height": height,
        "displayOption": "FitToPage",
    }
    write_result = write_json_file(
        page_dir / "page.json",
        page_json,
        reason=f"create_page {display_name}",
        dry_run=dry_run,
    )

    # Asegura que la página quede registrada en pages.json (orden de pestañas).
    pages_index_result = _register_page_in_index(report_dir, pid, dry_run=dry_run)

    logger.info("Página creada: %s (id=%s)", display_name, pid)
    return {
        "created": True,
        "page_id": pid,
        "display_name": display_name,
        "page_json": write_result,
        "index": pages_index_result,
    }


def add_visual_to_page(
    project: PbipProject,
    page_id: str,
    visual_json: dict[str, Any],
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Añade un visual (ya construido) a una página existente.

    Args:
        project: Proyecto destino.
        page_id: Identificador de la página.
        visual_json: Definición del visual (de
            :func:`~powerbi_mcp.visuals.pbip_visuals.build_visual_json`).
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.

    Returns:
        Diccionario con el ``visual_id`` y el resultado de escritura.

    Raises:
        PBIPNotFoundError: Si la página no existe.
    """
    report_dir = _require_report_dir(project)
    page_dir = report_dir / "definition" / "pages" / page_id
    if not dry_run and not page_dir.exists():
        raise PBIPNotFoundError("La página no existe.", details={"page_id": page_id})

    visual_id = visual_json.get("name") or uuid.uuid4().hex[:20]
    visual_json["name"] = visual_id
    visual_path = page_dir / "visuals" / visual_id / "visual.json"

    write_result = write_json_file(
        visual_path,
        visual_json,
        reason=f"add_visual {visual_id} -> {page_id}",
        dry_run=dry_run,
    )
    logger.info("Visual %s añadido a página %s", visual_id, page_id)
    return {"added": True, "visual_id": visual_id, "page_id": page_id, "write": write_result}


def auto_grid_layout(
    n_visuals: int,
    *,
    page_width: float = 1280.0,
    page_height: float = 720.0,
    columns: int | None = None,
    margin: float = 16.0,
    header: float = 60.0,
) -> list[dict[str, float]]:
    """Calcula posiciones en cuadrícula para distribuir ``n_visuals`` visuales.

    Args:
        n_visuals: Número de visuales a colocar.
        page_width: Ancho de la página.
        page_height: Alto de la página.
        columns: Número de columnas. Si es ``None``, se calcula automáticamente.
        margin: Margen entre visuales y bordes (px).
        header: Espacio reservado en la parte superior (px).

    Returns:
        Lista de diccionarios ``{x, y, width, height}`` para cada visual.

    Raises:
        ValidationError: Si ``n_visuals`` < 1.
    """
    if n_visuals < 1:
        raise ValidationError("n_visuals debe ser >= 1.", details={"n_visuals": n_visuals})

    cols = columns or max(1, round(n_visuals**0.5))
    rows = (n_visuals + cols - 1) // cols

    usable_w = page_width - margin * (cols + 1)
    usable_h = page_height - header - margin * (rows + 1)
    cell_w = usable_w / cols
    cell_h = usable_h / rows

    positions: list[dict[str, float]] = []
    for i in range(n_visuals):
        r, c = divmod(i, cols)
        positions.append(
            {
                "x": round(margin + c * (cell_w + margin), 2),
                "y": round(header + margin + r * (cell_h + margin), 2),
                "width": round(cell_w, 2),
                "height": round(cell_h, 2),
            }
        )
    return positions


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _require_report_dir(project: PbipProject) -> Path:
    """Devuelve la carpeta del reporte o lanza error."""
    if project.report_path is None:
        raise PBIPNotFoundError(
            "El proyecto no tiene carpeta de reporte (*.Report).",
            details={"project": project.name},
        )
    return project.report_path


def _register_page_in_index(report_dir: Path, page_id: str, *, dry_run: bool) -> dict[str, Any]:
    """Añade la página al índice ``pages.json`` (crea el índice si no existe)."""
    index_path = report_dir / "definition" / "pages" / "pages.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            index = {"pageOrder": [], "activePageName": page_id}
    else:
        index = {"pageOrder": [], "activePageName": page_id}

    order = index.setdefault("pageOrder", [])
    if page_id not in order:
        order.append(page_id)
    index.setdefault("activePageName", page_id)

    return write_json_file(
        index_path, index, reason=f"register page {page_id}", dry_run=dry_run, backup=False
    )


__all__ = [
    "add_visual_to_page",
    "auto_grid_layout",
    "create_page",
]
