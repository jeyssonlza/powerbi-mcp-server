"""Soporte para archivos PBIX: lectura, extracción y conversión desde PBIP.

Consideraciones técnicas importantes (y honestas):

Un ``.pbix`` es un contenedor **ZIP** con, entre otros: ``[Content_Types].xml``,
``Report/Layout`` (JSON del reporte, UTF-16-LE), ``DataModel`` (un *backup*
binario del motor Analysis Services / VertiPaq), ``DataMashup`` (Power Query),
miniatura y metadatos.

El componente ``DataModel`` **solo puede generarlo el motor de Power BI**
(Power BI Desktop / Analysis Services). Por tanto, **no es posible** construir
un PBIX 100% funcional con datos cargados usando solo Python.

Estrategia de este módulo:

- **Lectura** de un PBIX existente: extraer el ZIP y leer el ``Layout`` del
  reporte (totalmente posible en Python).
- **Conversión PBIP → PBIX**: se delega en `pbi-tools <https://pbi.tools>`_ si
  está instalado (es la vía soportada y fiable). Si no está, se devuelve una
  guía clara para abrir el PBIP en Power BI Desktop y guardarlo como PBIX.

Esto evita generar archivos corruptos y mantiene la promesa de robustez.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, cast

from powerbi_mcp.core.archive import safe_extract_zip
from powerbi_mcp.core.exceptions import PBIXError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def is_pbi_tools_available() -> bool:
    """Indica si la CLI ``pbi-tools`` está disponible en el ``PATH``.

    Returns:
        ``True`` si se encuentra el ejecutable ``pbi-tools``.
    """
    return shutil.which("pbi-tools") is not None


# ===========================================================================
# Lectura de un PBIX existente
# ===========================================================================
def extract_pbix(pbix_path: str | Path, target_dir: str | Path) -> dict[str, Any]:
    """Extrae el contenido de un archivo PBIX (ZIP) a un directorio.

    Args:
        pbix_path: Ruta del archivo ``.pbix``.
        target_dir: Carpeta destino donde extraer el contenido.

    Returns:
        Diccionario con ``target`` y la lista de ``members`` extraídos.

    Raises:
        PBIXError: Si el archivo no existe o no es un ZIP válido.
    """
    src = Path(pbix_path).expanduser().resolve()
    dest = Path(target_dir).expanduser().resolve()
    if not src.exists():
        raise PBIXError("El archivo PBIX no existe.", details={"path": str(src)})

    try:
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src, "r") as zf:
            members = zf.namelist()
            safe_extract_zip(zf, dest, members=members)
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        raise PBIXError(
            "No se pudo extraer el PBIX (¿archivo corrupto?).",
            details={"path": str(src), "error": str(exc)},
        ) from exc

    logger.info("PBIX extraído: %s -> %s (%d miembros)", src.name, dest, len(members))
    return {"target": str(dest), "members": members}


def read_pbix_layout(pbix_path: str | Path) -> dict[str, Any]:
    """Lee el ``Layout`` (definición del reporte) de un archivo PBIX.

    El ``Layout`` está codificado en UTF-16-LE dentro del ZIP.

    Args:
        pbix_path: Ruta del archivo ``.pbix``.

    Returns:
        El JSON del layout del reporte como diccionario.

    Raises:
        PBIXError: Si no se encuentra o no se puede decodificar el layout.
    """
    src = Path(pbix_path).expanduser().resolve()
    if not src.exists():
        raise PBIXError("El archivo PBIX no existe.", details={"path": str(src)})

    try:
        with zipfile.ZipFile(src, "r") as zf:
            raw = zf.read("Report/Layout")
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise PBIXError(
            "No se pudo leer 'Report/Layout' del PBIX.",
            details={"path": str(src), "error": str(exc)},
        ) from exc

    for encoding in ("utf-16-le", "utf-8-sig", "utf-8"):
        try:
            return cast(dict[str, Any], json.loads(raw.decode(encoding)))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

    raise PBIXError(
        "No se pudo decodificar el layout del PBIX.",
        details={"path": str(src)},
    )


def pbix_info(pbix_path: str | Path) -> dict[str, Any]:
    """Devuelve metadatos básicos de un PBIX sin extraerlo por completo.

    Args:
        pbix_path: Ruta del archivo ``.pbix``.

    Returns:
        Diccionario con ``size_bytes``, ``members``, ``has_data_model`` y
        ``has_data_mashup``.

    Raises:
        PBIXError: Si el archivo no existe o no es un ZIP válido.
    """
    src = Path(pbix_path).expanduser().resolve()
    if not src.exists():
        raise PBIXError("El archivo PBIX no existe.", details={"path": str(src)})

    try:
        with zipfile.ZipFile(src, "r") as zf:
            members = zf.namelist()
    except (OSError, zipfile.BadZipFile) as exc:
        raise PBIXError(
            "PBIX inválido.", details={"path": str(src), "error": str(exc)}
        ) from exc

    return {
        "path": str(src),
        "size_bytes": src.stat().st_size,
        "members": members,
        "has_data_model": "DataModel" in members,
        "has_data_mashup": "DataMashup" in members,
        "has_layout": "Report/Layout" in members,
    }


# ===========================================================================
# Conversión PBIP -> PBIX
# ===========================================================================
def convert_pbip_to_pbix(
    pbip_path: str | Path,
    output_path: str | Path | None = None,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Convierte un proyecto PBIP a PBIX usando ``pbi-tools`` si está disponible.

    Args:
        pbip_path: Ruta del proyecto PBIP (carpeta o archivo ``.pbip``).
        output_path: Ruta de salida del ``.pbix``. Si es ``None``, se usa el
            nombre del proyecto junto al PBIP.
        overwrite: Si es ``True``, sobrescribe un PBIX existente.

    Returns:
        Diccionario con ``status`` (``"converted"`` o ``"manual_required"``),
        y detalles o instrucciones según corresponda.

    Raises:
        PBIXError: Si ``pbi-tools`` está disponible pero la conversión falla.
    """
    src = Path(pbip_path).expanduser().resolve()
    out = (
        Path(output_path).expanduser().resolve()
        if output_path
        else src.with_suffix(".pbix")
    )

    if out.exists() and not overwrite:
        raise PBIXError(
            "El PBIX de salida ya existe (usa overwrite=True para reemplazar).",
            details={"output": str(out)},
        )

    if not is_pbi_tools_available():
        logger.warning("pbi-tools no está instalado; se requiere conversión manual.")
        return {
            "status": "manual_required",
            "reason": "pbi-tools no está instalado en el sistema.",
            "instructions": [
                "Opción A (recomendada): instala pbi-tools desde https://pbi.tools "
                "y vuelve a ejecutar la conversión.",
                "Opción B: abre el archivo .pbip en Power BI Desktop "
                f"({src}) y usa 'Archivo > Guardar como' para generar el .pbix.",
            ],
            "note": (
                "El componente DataModel del PBIX solo lo genera el motor de "
                "Power BI; por eso no puede crearse únicamente con Python."
            ),
        }

    cmd = ["pbi-tools", "compile", str(src), "-format", "PBIX", "-outPath", str(out)]
    if overwrite:
        cmd.append("-overwrite")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        stderr = getattr(exc, "stderr", "")
        raise PBIXError(
            "pbi-tools falló al compilar el PBIX.",
            details={"command": " ".join(cmd), "error": str(exc), "stderr": stderr},
        ) from exc

    logger.info("PBIX generado con pbi-tools: %s", out)
    return {
        "status": "converted",
        "output": str(out),
        "tool": "pbi-tools",
        "stdout": proc.stdout,
    }


__all__ = [
    "convert_pbip_to_pbix",
    "extract_pbix",
    "is_pbi_tools_available",
    "pbix_info",
    "read_pbix_layout",
]
