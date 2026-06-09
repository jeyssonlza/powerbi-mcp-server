"""Escritura segura de proyectos Power BI (PBIP) en disco.

Toda escritura pasa por estas garantías:

1. **Respaldo automático** del objetivo antes de modificarlo (salvo dry-run).
2. **Modo dry-run**: previsualiza el contenido que se escribiría sin tocar disco.
3. **Escritura atómica**: se escribe en un archivo temporal y se reemplaza, para
   evitar archivos corruptos ante un fallo a mitad de escritura.

Provee primitivas de bajo nivel (:func:`write_json_file`, :func:`write_text_file`)
y operaciones de alto nivel (:func:`save_semantic_model`, :func:`save_report`).

Sobre formatos:
- El **modelo semántico** se regenera de forma fiable en **TMSL** (``model.bim``).
  Para proyectos TMDL, las ediciones puntuales se realizan a nivel de texto en
  los módulos de :mod:`powerbi_mcp.model`; la regeneración completa exporta TMSL.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from powerbi_mcp.core.backup import auto_backup
from powerbi_mcp.core.exceptions import PBIPWriteError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import ModelFormat, PbipProject, SemanticModel

logger = get_logger(__name__)


# ===========================================================================
# Primitivas de escritura segura
# ===========================================================================
def write_text_file(
    path: str | Path,
    content: str,
    *,
    reason: str,
    dry_run: bool = False,
    backup: bool = True,
) -> dict[str, Any]:
    """Escribe texto en un archivo de forma atómica, con respaldo previo.

    Args:
        path: Ruta destino.
        content: Contenido de texto a escribir (UTF-8).
        reason: Motivo de la escritura (para backup y auditoría).
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.
        backup: Si es ``True``, respalda el archivo existente antes de escribir.

    Returns:
        Diccionario con ``path``, ``dry_run``, ``bytes`` y, en dry-run,
        ``preview`` (primeros 2000 caracteres).

    Raises:
        PBIPWriteError: Si falla la escritura.
    """
    target = Path(path).expanduser().resolve()

    if dry_run:
        logger.info("[dry-run] Escritura de texto prevista en %s (%s)", target, reason)
        return {
            "path": str(target),
            "dry_run": True,
            "bytes": len(content.encode("utf-8")),
            "preview": content[:2000],
        }

    if backup and target.exists():
        auto_backup(target, reason=reason)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(target, content)
    except OSError as exc:
        raise PBIPWriteError(
            "No se pudo escribir el archivo.",
            details={"path": str(target), "error": str(exc)},
        ) from exc

    logger.info("Archivo escrito: %s (%d bytes) | %s", target, len(content), reason)
    return {"path": str(target), "dry_run": False, "bytes": len(content.encode("utf-8"))}


def write_json_file(
    path: str | Path,
    data: dict[str, Any] | list[Any],
    *,
    reason: str,
    dry_run: bool = False,
    backup: bool = True,
    indent: int = 2,
) -> dict[str, Any]:
    """Serializa ``data`` a JSON y lo escribe con :func:`write_text_file`.

    Args:
        path: Ruta destino.
        data: Estructura JSON-serializable.
        reason: Motivo de la escritura.
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.
        backup: Si es ``True``, respalda el archivo existente antes de escribir.
        indent: Indentación del JSON (2 por defecto, como Power BI Desktop).

    Returns:
        El mismo diccionario de resultado que :func:`write_text_file`.
    """
    content = json.dumps(data, indent=indent, ensure_ascii=False)
    return write_text_file(path, content, reason=reason, dry_run=dry_run, backup=backup)


def _atomic_write(target: Path, content: str) -> None:
    """Escribe ``content`` en ``target`` de forma atómica (temp + replace)."""
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        os.replace(tmp_name, target)
    except BaseException:
        # Limpia el temporal si algo falla.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


# ===========================================================================
# Serialización del modelo semántico (TMSL)
# ===========================================================================
#: Campos internos del modelo que NO pertenecen al esquema TMSL y deben
#: excluirse al serializar de vuelta a disco.
_MODEL_INTERNAL_FIELDS = {"format"}


def serialize_model_to_tmsl(model: SemanticModel) -> dict[str, Any]:
    """Convierte un :class:`SemanticModel` a la estructura TMSL (``model.bim``).

    Preserva los campos extra capturados al leer (gracias a ``extra="allow"``)
    y excluye los campos internos del MCP (como ``format``).

    Args:
        model: Modelo semántico a serializar.

    Returns:
        Diccionario con la estructura TMSL ``{"name", "compatibilityLevel",
        "model": {...}}``.
    """
    model_body = model.model_dump(
        by_alias=True,
        exclude_none=True,
        exclude=_MODEL_INTERNAL_FIELDS,
    )

    # ``name`` y ``compatibilityLevel`` viven en el nivel raíz del TMSL.
    name = model_body.pop("name", "Model")
    compatibility = model_body.pop("compatibilityLevel", model.compatibility_level)

    return {
        "name": name,
        "compatibilityLevel": compatibility,
        "model": model_body,
    }


def save_semantic_model(
    project: PbipProject,
    *,
    reason: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Guarda el modelo semántico del proyecto en disco (formato TMSL).

    Args:
        project: Proyecto cuyo modelo se guardará.
        reason: Motivo de la escritura.
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.

    Returns:
        El resultado de la operación de escritura.

    Raises:
        PBIPWriteError: Si el proyecto no tiene modelo o ruta de modelo.
    """
    if project.semantic_model is None or project.model_path is None:
        raise PBIPWriteError(
            "El proyecto no tiene modelo semántico cargado o ruta de modelo.",
            details={"project": project.name},
        )

    if project.model_format == ModelFormat.TMDL:
        logger.warning(
            "El proyecto está en TMDL; la regeneración completa se exporta a TMSL "
            "(model.bim). Las ediciones puntuales conservan TMDL."
        )

    tmsl = serialize_model_to_tmsl(project.semantic_model)
    bim_path = project.model_path / "model.bim"
    return write_json_file(bim_path, tmsl, reason=reason, dry_run=dry_run)


# ===========================================================================
# Reporte
# ===========================================================================
def save_report(
    project: PbipProject,
    *,
    reason: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Guarda el reporte del proyecto (solo formato PBIR por archivo).

    Para reportes PBIR, cada página/visual modificado se reescribe en su propio
    archivo desde ``visual.config``. Las operaciones de creación de visuales del
    módulo :mod:`powerbi_mcp.visuals` escriben directamente los archivos PBIR.

    Args:
        project: Proyecto cuyo reporte se guardará.
        reason: Motivo de la escritura.
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.

    Returns:
        Resumen de los archivos escritos.
    """
    if project.report is None or project.report_path is None:
        raise PBIPWriteError(
            "El proyecto no tiene reporte cargado o ruta de reporte.",
            details={"project": project.name},
        )

    written: list[dict[str, Any]] = []
    pages_dir = project.report_path / "definition" / "pages"

    for page in project.report.pages:
        if not page.name:
            continue
        for visual in page.visuals:
            if not visual.name or not visual.config:
                continue
            visual_path = pages_dir / page.name / "visuals" / visual.name / "visual.json"
            written.append(
                write_json_file(
                    visual_path,
                    visual.config,
                    reason=reason,
                    dry_run=dry_run,
                )
            )

    return {"dry_run": dry_run, "files_written": len(written), "details": written}


def save_project(
    project: PbipProject,
    *,
    reason: str,
    dry_run: bool = False,
    include_report: bool = True,
) -> dict[str, Any]:
    """Guarda el proyecto completo (modelo y, opcionalmente, reporte).

    Args:
        project: Proyecto a guardar.
        reason: Motivo de la escritura.
        dry_run: Si es ``True``, no escribe; devuelve la previsualización.
        include_report: Si es ``True``, guarda también el reporte.

    Returns:
        Resumen con los resultados de modelo y reporte.
    """
    result: dict[str, Any] = {
        "model": save_semantic_model(project, reason=reason, dry_run=dry_run),
    }
    if include_report and project.report is not None:
        result["report"] = save_report(project, reason=reason, dry_run=dry_run)
    return result


__all__ = [
    "save_project",
    "save_report",
    "save_semantic_model",
    "serialize_model_to_tmsl",
    "write_json_file",
    "write_text_file",
]
