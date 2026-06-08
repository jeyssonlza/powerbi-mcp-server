"""Lectura y carga de proyectos Power BI (PBIP) desde disco.

Detecta automáticamente la estructura del proyecto y el formato de cada parte:

- Modelo semántico: ``model.bim`` (TMSL/JSON) o ``definition/*.tmdl`` (TMDL).
- Reporte: ``report.json`` (legacy) o ``definition/pages/...`` (PBIR).

El resultado es un :class:`~powerbi_mcp.pbip.models.PbipProject` listo para
consultar o modificar. La lectura **nunca** escribe en disco.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from powerbi_mcp.core.exceptions import PBIPNotFoundError, PBIPParseError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import (
    Column,
    Measure,
    ModelFormat,
    Page,
    Partition,
    PbipProject,
    Relationship,
    Report,
    ReportFormat,
    SemanticModel,
    Table,
    Visual,
)

logger = get_logger(__name__)


# ===========================================================================
# Detección de la estructura del proyecto
# ===========================================================================
def detect_project_paths(root: str | Path) -> dict[str, Path | None]:
    """Localiza las rutas clave de un proyecto PBIP a partir de una carpeta.

    Acepta tanto la carpeta raíz del proyecto como la ruta directa a un archivo
    ``.pbip``.

    Args:
        root: Carpeta raíz del proyecto o archivo ``.pbip``.

    Returns:
        Diccionario con claves ``root``, ``pbip_file``, ``model_path`` y
        ``report_path`` (valores ``Path`` o ``None``).

    Raises:
        PBIPNotFoundError: Si la ruta no existe.
    """
    root_path = Path(root).expanduser().resolve()
    if not root_path.exists():
        raise PBIPNotFoundError(
            "La ruta del proyecto no existe.", details={"path": str(root_path)}
        )

    pbip_file: Path | None = None
    if root_path.is_file():
        if root_path.suffix.lower() == ".pbip":
            pbip_file = root_path
        root_path = root_path.parent

    if pbip_file is None:
        pbip_candidates = list(root_path.glob("*.pbip"))
        pbip_file = pbip_candidates[0] if pbip_candidates else None

    model_path = _find_dir(root_path, suffix=".SemanticModel") or _find_dir(
        root_path, suffix=".Dataset"
    )
    report_path = _find_dir(root_path, suffix=".Report")

    return {
        "root": root_path,
        "pbip_file": pbip_file,
        "model_path": model_path,
        "report_path": report_path,
    }


def _find_dir(root: Path, *, suffix: str) -> Path | None:
    """Devuelve el primer subdirectorio cuyo nombre termina en ``suffix``."""
    for child in root.iterdir():
        if child.is_dir() and child.name.endswith(suffix):
            return child
    return None


# ===========================================================================
# Carga del proyecto completo
# ===========================================================================
def load_project(root: str | Path, *, load_report: bool = True) -> PbipProject:
    """Carga un proyecto PBIP completo en memoria.

    Args:
        root: Carpeta raíz del proyecto o archivo ``.pbip``.
        load_report: Si es ``False``, omite la carga del reporte (más rápido si
            solo interesa el modelo semántico).

    Returns:
        El :class:`~powerbi_mcp.pbip.models.PbipProject` cargado.

    Raises:
        PBIPNotFoundError: Si no se encuentra el modelo semántico.
        PBIPParseError: Si falla la interpretación de algún archivo.
    """
    paths = detect_project_paths(root)
    root_path = paths["root"]
    assert root_path is not None

    name = paths["pbip_file"].stem if paths["pbip_file"] else root_path.name

    if paths["model_path"] is None:
        raise PBIPNotFoundError(
            "No se encontró la carpeta del modelo semántico (*.SemanticModel).",
            details={"root": str(root_path)},
        )

    semantic_model, model_format = load_semantic_model(paths["model_path"])

    report: Report | None = None
    report_format = ReportFormat.UNKNOWN
    if load_report and paths["report_path"] is not None:
        report, report_format = load_report_from(paths["report_path"])

    project = PbipProject(
        name=name,
        root_path=root_path,
        pbip_file=paths["pbip_file"],
        model_path=paths["model_path"],
        report_path=paths["report_path"],
        semantic_model=semantic_model,
        report=report,
        model_format=model_format,
        report_format=report_format,
    )
    logger.info("Proyecto PBIP cargado: %s | %s", name, project.summary())
    return project


# ===========================================================================
# Modelo semántico
# ===========================================================================
def load_semantic_model(model_path: str | Path) -> tuple[SemanticModel, ModelFormat]:
    """Carga el modelo semántico detectando TMSL (model.bim) o TMDL.

    Args:
        model_path: Carpeta ``*.SemanticModel``.

    Returns:
        Tupla ``(modelo, formato)``.

    Raises:
        PBIPParseError: Si no se reconoce ningún formato válido.
    """
    model_dir = Path(model_path)

    bim_file = model_dir / "model.bim"
    if bim_file.exists():
        logger.debug("Modelo en formato TMSL: %s", bim_file)
        return _load_tmsl(bim_file), ModelFormat.TMSL

    tmdl_dir = model_dir / "definition"
    if tmdl_dir.exists() and any(tmdl_dir.rglob("*.tmdl")):
        logger.debug("Modelo en formato TMDL: %s", tmdl_dir)
        return _load_tmdl(tmdl_dir), ModelFormat.TMDL

    raise PBIPParseError(
        "No se encontró model.bim (TMSL) ni definition/*.tmdl (TMDL).",
        details={"model_path": str(model_dir)},
    )


def _load_tmsl(bim_file: Path) -> SemanticModel:
    """Carga un modelo en formato TMSL (``model.bim`` JSON)."""
    try:
        raw = json.loads(bim_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise PBIPParseError(
            "No se pudo leer/parsear model.bim.",
            details={"file": str(bim_file), "error": str(exc)},
        ) from exc

    model_node = raw.get("model", raw)
    model = SemanticModel.model_validate(model_node)
    model.name = raw.get("name", model.name)
    if "compatibilityLevel" in raw:
        model.compatibility_level = raw["compatibilityLevel"]
    model.format = ModelFormat.TMSL
    return model


def _load_tmdl(tmdl_dir: Path) -> SemanticModel:
    """Carga un modelo en formato TMDL (texto) con un parser ligero.

    El parser extrae tablas, columnas, medidas, particiones y relaciones de los
    archivos ``.tmdl``. TMDL es un formato declarativo basado en indentación.

    Args:
        tmdl_dir: Carpeta ``definition`` con los archivos ``.tmdl``.

    Returns:
        El modelo semántico reconstruido.
    """
    model = SemanticModel(format=ModelFormat.TMDL)

    # model.tmdl (cultura, nombre, compatibilidad)
    model_file = tmdl_dir / "model.tmdl"
    if model_file.exists():
        text = model_file.read_text(encoding="utf-8")
        if m := re.search(r"culture:\s*(\S+)", text):
            model.culture = m.group(1)

    # Tablas
    tables_dir = tmdl_dir / "tables"
    if tables_dir.exists():
        for tmdl_file in sorted(tables_dir.glob("*.tmdl")):
            try:
                model.tables.append(_parse_tmdl_table(tmdl_file.read_text(encoding="utf-8")))
            except Exception as exc:
                logger.warning("No se pudo parsear tabla TMDL %s: %s", tmdl_file.name, exc)

    # Relaciones
    rel_file = tmdl_dir / "relationships.tmdl"
    if rel_file.exists():
        model.relationships = _parse_tmdl_relationships(rel_file.read_text(encoding="utf-8"))

    return model


# ---------------------------------------------------------------------------
# Parser TMDL basado en indentación (tabulaciones)
#
# TMDL es un formato declarativo donde la jerarquía se expresa por nivel de
# indentación con TABs:
#     table <Nombre>                 (nivel 0)
#         column <Nombre>            (nivel 1)
#             dataType: ...          (nivel 2)  -> propiedades de la columna
#         measure <Nombre> = <expr>  (nivel 1)
#             <expresión DAX>        (nivel 3)  -> cuerpo de la medida
#             formatString: ...      (nivel 2)  -> propiedades de la medida
# Las expresiones DAX pueden ir en línea, en bloque indentado o entre fences
# de triple backtick (```).
# ---------------------------------------------------------------------------
#: Propiedades conocidas de medidas/columnas (van a nivel 2, no son expresión).
_TMDL_PROP_KEYS = (
    "dataType:", "formatString:", "displayFolder:", "lineageTag:", "sourceColumn:",
    "summarizeBy:", "isHidden", "isKey", "dataCategory:", "sortByColumn:",
    "annotation ", "description", "changedProperty", "relatedColumnDetails",
    "formatStringDefinition", "detailRowsDefinition", "kpi",
)


def _indent_level(line: str) -> int:
    """Devuelve el número de tabulaciones iniciales (nivel de indentación)."""
    count = 0
    for ch in line:
        if ch == "\t":
            count += 1
        else:
            break
    return count


def _strip_tmdl_name(raw: str) -> str:
    """Limpia el nombre de un objeto TMDL (quita comillas simples y el ``=``)."""
    raw = raw.strip()
    if raw.startswith("'"):
        end = raw.find("'", 1)
        if end != -1:
            return raw[1:end]
    return raw.split("=", 1)[0].strip().strip("'").strip()


def _parse_tmdl_table(text: str) -> Table:
    """Parsea un archivo TMDL de tabla a un :class:`Table` (parser por indentación)."""
    lines = text.split("\n")

    name = "Tabla"
    is_hidden = False
    for line in lines:
        s = line.strip()
        if s.startswith("table "):
            name = _strip_tmdl_name(s[len("table "):])
        elif s == "isHidden" or s.startswith("isHidden:"):
            is_hidden = True
    table = Table(name=name, isHidden=is_hidden)

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        indent = _indent_level(line)

        if indent == 1 and stripped.startswith("column "):
            col, i = _parse_tmdl_column(lines, i)
            table.columns.append(col)
            continue
        if indent == 1 and stripped.startswith("measure "):
            measure, i = _parse_tmdl_measure(lines, i)
            table.measures.append(measure)
            continue
        if indent == 1 and stripped.startswith("partition "):
            part, i = _parse_tmdl_partition(lines, i)
            table.partitions.append(part)
            continue
        i += 1

    return table


def _parse_tmdl_column(lines: list[str], i: int) -> tuple[Column, int]:
    """Parsea una columna TMDL (de datos o calculada) y devuelve ``(Column, i)``."""
    header = lines[i].strip()[len("column "):]
    name = _strip_tmdl_name(header)
    is_calculated = "=" in header
    expression, i = _consume_expression_if_any(lines, i, header)

    data_type = "string"
    summarize_by = None
    source_column = None
    format_string = None
    is_hidden = False

    # Propiedades a nivel >= 2.
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _indent_level(line) <= 1:
            break
        s = line.strip()
        if s.startswith("dataType:"):
            data_type = s.split(":", 1)[1].strip()
        elif s.startswith("summarizeBy:"):
            summarize_by = s.split(":", 1)[1].strip()
        elif s.startswith("sourceColumn:"):
            source_column = s.split(":", 1)[1].strip()
        elif s.startswith("formatString:"):
            format_string = s.split(":", 1)[1].strip()
        elif s == "isHidden" or s.startswith("isHidden:"):
            is_hidden = True
        i += 1

    return (
        Column(
            name=name,
            dataType=data_type,
            summarizeBy=summarize_by,
            sourceColumn=source_column,
            formatString=format_string,
            isHidden=is_hidden,
            expression=expression if is_calculated else None,
        ),
        i,
    )


def _parse_tmdl_measure(lines: list[str], i: int) -> tuple[Measure, int]:
    """Parsea una medida TMDL (con expresión en línea, bloque o fence)."""
    header = lines[i].strip()[len("measure "):]
    name = _strip_tmdl_name(header)
    expression, i = _consume_expression_if_any(lines, i, header)

    format_string = None
    display_folder = None
    description = None

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _indent_level(line) <= 1:
            break
        s = line.strip()
        if s.startswith("formatString:"):
            format_string = s.split(":", 1)[1].strip()
        elif s.startswith("displayFolder:"):
            display_folder = s.split(":", 1)[1].strip()
        elif s.startswith("///"):
            description = s.lstrip("/ ").strip()
        i += 1

    return (
        Measure(
            name=name,
            expression=expression or "",
            formatString=format_string,
            displayFolder=display_folder,
            description=description,
        ),
        i,
    )


def _parse_tmdl_partition(lines: list[str], i: int) -> tuple[Partition, int]:
    """Parsea una partición TMDL detectando el tipo de origen (m/calculated/...)."""
    header = lines[i].strip()[len("partition "):]
    name = _strip_tmdl_name(header)
    source_type = "m"
    # El tipo suele venir como 'partition X = calculated' o 'partition X = m'.
    after_eq = header.split("=", 1)[1].strip() if "=" in header else ""
    if after_eq:
        source_type = after_eq.split()[0]

    i += 1
    # Saltar el cuerpo de la partición (nivel >= 2) sin interpretarlo.
    while i < len(lines):
        line = lines[i]
        if line.strip() and _indent_level(line) <= 1:
            break
        i += 1

    return Partition(name=name, source={"type": source_type}), i


def _consume_expression_if_any(lines: list[str], i: int, header: str) -> tuple[str | None, int]:
    """Lee la expresión asociada a ``measure``/``column`` si la hay.

    Soporta tres formas tras el ``=``: fence de triple backtick, expresión en
    línea y expresión en bloque indentado (nivel >= 3). Devuelve la expresión
    (o ``None``) y el índice de la siguiente línea no consumida.
    """
    if "=" not in header:
        return None, i + 1

    after_eq = header.split("=", 1)[1].strip()
    i += 1

    # Forma 1: fence ``` ... ```
    if after_eq.startswith("```"):
        body: list[str] = []
        while i < len(lines):
            if lines[i].strip().startswith("```"):
                i += 1
                break
            body.append(lines[i].strip())
            i += 1
        return "\n".join(b for b in body if b).strip(), i

    # Forma 2: expresión en línea (puede continuar en bloque indentado).
    body = [after_eq] if after_eq else []
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _indent_level(line) >= 3 and not _is_tmdl_prop(line.strip()):
            body.append(line.strip())
            i += 1
        else:
            break
    return ("\n".join(body).strip() or None), i


def _is_tmdl_prop(stripped: str) -> bool:
    """Indica si una línea TMDL es una propiedad conocida (no parte de expresión)."""
    return any(stripped.startswith(key) for key in _TMDL_PROP_KEYS)


def _parse_tmdl_relationships(text: str) -> list[Relationship]:
    """Parsea relaciones desde ``relationships.tmdl`` (parser por indentación)."""
    relationships: list[Relationship] = []
    lines = text.split("\n")
    i, n = 0, len(lines)

    while i < n:
        stripped = lines[i].strip()
        if not stripped.startswith("relationship "):
            i += 1
            continue

        rel_id = stripped[len("relationship "):].strip()
        props: dict[str, str] = {}
        i += 1
        while i < n:
            line = lines[i]
            if line.strip() and _indent_level(line) == 0:
                break
            s = line.strip()
            if ":" in s:
                key, _, value = s.partition(":")
                props[key.strip()] = value.strip()
            i += 1

        if "fromColumn" not in props or "toColumn" not in props:
            continue
        from_table, from_col = _split_tmdl_ref(props["fromColumn"])
        to_table, to_col = _split_tmdl_ref(props["toColumn"])
        cross = (
            "bothDirections"
            if props.get("crossFilteringBehavior") == "bothDirections"
            else "oneDirection"
        )
        is_active = props.get("isActive", "true").lower() != "false"
        relationships.append(
            Relationship(
                name=rel_id,
                from_table=from_table,
                from_column=from_col,
                to_table=to_table,
                to_column=to_col,
                cross_filtering_behavior=cross,
                is_active=is_active,
            )
        )

    return relationships


def _split_tmdl_ref(ref: str) -> tuple[str, str]:
    """Divide una referencia TMDL ``Tabla.Columna`` en ``(tabla, columna)``.

    Maneja nombres entre comillas simples con espacios, p. ej.
    ``dim_Pessoa.'Data  Desligamento'`` o ``'Mi Tabla'.Columna``.
    """
    ref = ref.strip()
    if not ref:
        return "", ""

    # Tabla entre comillas: 'Mi Tabla'.Columna
    if ref.startswith("'"):
        end = ref.find("'", 1)
        if end != -1:
            table = ref[1:end]
            rest = ref[end + 1 :].lstrip(".").strip()
            return table, rest.strip("'")

    table, _, column = ref.partition(".")
    return table.strip().strip("'"), column.strip().strip("'")


# ===========================================================================
# Reporte
# ===========================================================================
def load_report_from(report_path: str | Path) -> tuple[Report, ReportFormat]:
    """Carga el reporte detectando formato PBIR (carpetas) o legacy (archivo).

    Args:
        report_path: Carpeta ``*.Report``.

    Returns:
        Tupla ``(reporte, formato)``.
    """
    report_dir = Path(report_path)

    pbir_pages = report_dir / "definition" / "pages"
    if pbir_pages.exists():
        return _load_pbir_report(report_dir), ReportFormat.PBIR

    legacy_file = report_dir / "report.json"
    if legacy_file.exists():
        return _load_legacy_report(legacy_file), ReportFormat.LEGACY

    logger.warning("No se reconoció el formato del reporte en %s", report_dir)
    return Report(format=ReportFormat.UNKNOWN), ReportFormat.UNKNOWN


def _load_pbir_report(report_dir: Path) -> Report:
    """Carga un reporte en formato PBIR (carpetas con visual.json)."""
    report = Report(format=ReportFormat.PBIR)
    pages_dir = report_dir / "definition" / "pages"

    for page_dir in sorted(p for p in pages_dir.iterdir() if p.is_dir()):
        page_json = page_dir / "page.json"
        if not page_json.exists():
            continue
        try:
            page_data = json.loads(page_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Página PBIR ilegible %s: %s", page_dir.name, exc)
            continue

        page = Page(
            name=page_data.get("name", page_dir.name),
            displayName=page_data.get("displayName"),
            width=page_data.get("width", 1280.0),
            height=page_data.get("height", 720.0),
        )

        visuals_dir = page_dir / "visuals"
        if visuals_dir.exists():
            for visual_dir in sorted(v for v in visuals_dir.iterdir() if v.is_dir()):
                visual_json = visual_dir / "visual.json"
                if visual_json.exists():
                    page.visuals.append(_parse_pbir_visual(visual_json))

        report.pages.append(page)

    return report


def _parse_pbir_visual(visual_json: Path) -> Visual:
    """Parsea un ``visual.json`` de PBIR a un :class:`Visual`."""
    try:
        data = json.loads(visual_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Visual(name=visual_json.parent.name)

    position = data.get("position", {})
    visual_node = data.get("visual", {})
    return Visual(
        name=data.get("name", visual_json.parent.name),
        visualType=visual_node.get("visualType"),
        x=position.get("x", 0.0),
        y=position.get("y", 0.0),
        width=position.get("width", 0.0),
        height=position.get("height", 0.0),
        config=data,
    )


def _load_legacy_report(legacy_file: Path) -> Report:
    """Carga un reporte legacy (``report.json`` monolítico)."""
    try:
        data = json.loads(legacy_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise PBIPParseError(
            "No se pudo leer report.json (legacy).",
            details={"file": str(legacy_file), "error": str(exc)},
        ) from exc

    report = Report(format=ReportFormat.LEGACY)
    for section in data.get("sections", []):
        page = Page(
            name=section.get("name"),
            displayName=section.get("displayName"),
            width=section.get("width", 1280.0),
            height=section.get("height", 720.0),
        )
        for vc in section.get("visualContainers", []):
            cfg: dict[str, Any] = {}
            if isinstance(vc.get("config"), str):
                try:
                    cfg = json.loads(vc["config"])
                except json.JSONDecodeError:
                    cfg = {}
            page.visuals.append(
                Visual(
                    name=str(cfg.get("name", "")),
                    x=vc.get("x", 0.0),
                    y=vc.get("y", 0.0),
                    width=vc.get("width", 0.0),
                    height=vc.get("height", 0.0),
                    config=cfg,
                )
            )
        report.pages.append(page)
    return report


__all__ = [
    "detect_project_paths",
    "load_project",
    "load_report_from",
    "load_semantic_model",
]
