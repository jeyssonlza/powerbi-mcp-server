"""Modelos de datos (pydantic) del esquema de un proyecto Power BI (PBIP).

Un proyecto PBIP se compone, a grandes rasgos, de:

- Un archivo raíz ``<nombre>.pbip`` (apunta al reporte y, opcionalmente, al modelo).
- Una carpeta ``<nombre>.SemanticModel/`` con el **modelo semántico**:
  - ``model.bim`` (formato **TMSL**, JSON) — formato canónico que manipulamos, o
  - ``definition/*.tmdl`` (formato **TMDL**, texto) — detectado y soportado en lectura.
- Una carpeta ``<nombre>.Report/`` con el **reporte**:
  - ``report.json`` (formato legacy), o
  - ``definition/pages/.../visual.json`` (formato **PBIR**).

Los modelos usan ``extra="allow"`` para **preservar** cualquier propiedad
desconocida al re-serializar (no perder información del archivo original) y
``populate_by_name=True`` + alias *camelCase* para mapear los nombres reales
del JSON de Power BI a atributos *snake_case* de Python.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Importar tipos personalizados para mejor type checking
try:
    from powerbi_mcp.types import CompatibilityLevel, DataType
except ImportError:
    # Fallback si no está disponible
    CompatibilityLevel = None  # type: ignore
    DataType = None  # type: ignore


class _PBIPModel(BaseModel):
    """Base común: preserva campos extra y permite alias camelCase."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


# ===========================================================================
# Enumeraciones de formato
# ===========================================================================
class ModelFormat(str, Enum):
    """Formato de serialización del modelo semántico."""

    TMSL = "tmsl"  # model.bim (JSON)
    TMDL = "tmdl"  # definition/*.tmdl (texto)
    UNKNOWN = "unknown"


class ReportFormat(str, Enum):
    """Formato de serialización del reporte."""

    PBIR = "pbir"  # definition/pages/.../visual.json (carpetas)
    LEGACY = "legacy"  # report.json (archivo único)
    UNKNOWN = "unknown"


# ===========================================================================
# Modelo semántico (TMSL / Tabular)
# ===========================================================================
class Column(_PBIPModel):
    """Columna de una tabla del modelo semántico.

    Attributes:
        name: Nombre visible de la columna.
        data_type: Tipo de dato tabular (``string``, ``int64``, ``double``,
            ``decimal``, ``dateTime``, ``boolean``...).
        source_column: Nombre de la columna en el origen (para columnas de datos).
        expression: Expresión DAX (para columnas calculadas).
        format_string: Cadena de formato de visualización.
        is_hidden: Si la columna está oculta.
        summarize_by: Agregación por defecto (``sum``, ``none``, ``count``...).
        data_category: Categoría de datos (``Address``, ``WebUrl``...).
        sort_by_column: Columna por la que se ordena esta columna.
    """

    name: str
    data_type: str = Field(default="string", alias="dataType")
    source_column: str | None = Field(default=None, alias="sourceColumn")
    expression: str | list[str] | None = None
    format_string: str | None = Field(default=None, alias="formatString")
    is_hidden: bool = Field(default=False, alias="isHidden")
    summarize_by: str | None = Field(default=None, alias="summarizeBy")
    data_category: str | None = Field(default=None, alias="dataCategory")
    sort_by_column: str | None = Field(default=None, alias="sortByColumn")

    @property
    def is_calculated(self) -> bool:
        """True si es una columna calculada (tiene expresión DAX)."""
        return self.expression is not None


class Measure(_PBIPModel):
    """Medida DAX de una tabla.

    Attributes:
        name: Nombre de la medida.
        expression: Expresión DAX (puede venir como lista de líneas).
        format_string: Cadena de formato de visualización.
        is_hidden: Si la medida está oculta.
        display_folder: Carpeta de visualización para organizar medidas.
        description: Descripción/documentación de la medida.
    """

    name: str
    expression: str | list[str] = ""
    format_string: str | None = Field(default=None, alias="formatString")
    is_hidden: bool = Field(default=False, alias="isHidden")
    display_folder: str | None = Field(default=None, alias="displayFolder")
    description: str | None = None

    @property
    def expression_text(self) -> str:
        """Devuelve la expresión DAX como texto único (une listas de líneas)."""
        if isinstance(self.expression, list):
            return "\n".join(self.expression)
        return self.expression


class Partition(_PBIPModel):
    """Partición de una tabla (define el origen de datos: M, DAX, etc.).

    Attributes:
        name: Nombre de la partición.
        mode: Modo de almacenamiento (``import``, ``directQuery``...).
        source: Definición del origen (tipo ``m``, ``query``, ``calculated``).
    """

    name: str
    mode: str | None = None
    source: dict[str, Any] | None = None

    @property
    def source_type(self) -> str | None:
        """Tipo de origen de la partición (``m``, ``calculated``, ``query``)."""
        if self.source:
            return self.source.get("type")
        return None


class Table(_PBIPModel):
    """Tabla del modelo semántico.

    Attributes:
        name: Nombre de la tabla.
        columns: Columnas de la tabla.
        measures: Medidas DAX de la tabla.
        partitions: Particiones (orígenes de datos).
        is_hidden: Si la tabla está oculta.
        description: Descripción de la tabla.
    """

    name: str
    columns: list[Column] = Field(default_factory=list)
    measures: list[Measure] = Field(default_factory=list)
    partitions: list[Partition] = Field(default_factory=list)
    is_hidden: bool = Field(default=False, alias="isHidden")
    description: str | None = None

    @property
    def is_calculated_table(self) -> bool:
        """True si la tabla se define por una expresión DAX (tabla calculada)."""
        return any(p.source_type == "calculated" for p in self.partitions)

    def get_column(self, name: str) -> Column | None:
        """Devuelve la columna con el nombre dado (o ``None``)."""
        return next((c for c in self.columns if c.name == name), None)

    def get_measure(self, name: str) -> Measure | None:
        """Devuelve la medida con el nombre dado (o ``None``)."""
        return next((m for m in self.measures if m.name == name), None)


class Relationship(_PBIPModel):
    """Relación entre dos tablas del modelo.

    Attributes:
        name: Identificador de la relación.
        from_table: Tabla origen (lado "muchos" habitualmente).
        from_column: Columna origen.
        to_table: Tabla destino (lado "uno" habitualmente).
        to_column: Columna destino.
        cross_filtering_behavior: ``oneDirection`` o ``bothDirections``.
        from_cardinality: Cardinalidad del lado origen (``many``/``one``).
        to_cardinality: Cardinalidad del lado destino (``one``/``many``).
        is_active: Si la relación está activa.
    """

    name: str | None = None
    from_table: str = Field(alias="fromTable")
    from_column: str = Field(alias="fromColumn")
    to_table: str = Field(alias="toTable")
    to_column: str = Field(alias="toColumn")
    cross_filtering_behavior: str = Field(
        default="oneDirection", alias="crossFilteringBehavior"
    )
    from_cardinality: str | None = Field(default=None, alias="fromCardinality")
    to_cardinality: str | None = Field(default=None, alias="toCardinality")
    is_active: bool = Field(default=True, alias="isActive")

    @property
    def is_bidirectional(self) -> bool:
        """True si el filtro cruzado es bidireccional."""
        return self.cross_filtering_behavior == "bothDirections"


class SemanticModel(_PBIPModel):
    """Modelo semántico (capa Tabular) de un proyecto Power BI.

    Attributes:
        name: Nombre del modelo.
        compatibility_level: Nivel de compatibilidad TMSL.
        culture: Cultura/idioma por defecto (ej. ``es-ES``).
        tables: Tablas del modelo.
        relationships: Relaciones entre tablas.
        format: Formato detectado en disco (TMSL/TMDL).
    """

    name: str = "Model"
    compatibility_level: int = Field(default=1550, alias="compatibilityLevel")
    culture: str | None = None
    tables: list[Table] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    format: ModelFormat = ModelFormat.TMSL

    def get_table(self, name: str) -> Table | None:
        """Devuelve la tabla con el nombre dado (o ``None``)."""
        return next((t for t in self.tables if t.name == name), None)

    def all_measures(self) -> list[tuple[str, Measure]]:
        """Devuelve todas las medidas como pares ``(tabla, medida)``."""
        return [(t.name, m) for t in self.tables for m in t.measures]

    def find_measure(self, name: str) -> tuple[str, Measure] | None:
        """Busca una medida por nombre en todo el modelo."""
        for table_name, measure in self.all_measures():
            if measure.name == name:
                return table_name, measure
        return None


# ===========================================================================
# Reporte (páginas y visuales)
# ===========================================================================
class Visual(_PBIPModel):
    """Visual de una página de reporte.

    En PBIR cada visual vive en su propio ``visual.json``. Mantenemos los
    campos clave de forma tipada y preservamos el resto en ``extra``.

    Attributes:
        name: Identificador único del visual.
        visual_type: Tipo de visual (``barChart``, ``card``, ``table``...).
        x: Posición X (px).
        y: Posición Y (px).
        width: Ancho (px).
        height: Alto (px).
        config: Configuración cruda del visual (campos, formato...).
    """

    name: str | None = None
    visual_type: str | None = Field(default=None, alias="visualType")
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    config: dict[str, Any] = Field(default_factory=dict)


class Page(_PBIPModel):
    """Página de un reporte.

    Attributes:
        name: Identificador interno de la página.
        display_name: Nombre visible de la pestaña.
        width: Ancho del lienzo.
        height: Alto del lienzo.
        visuals: Visuales contenidos en la página.
    """

    name: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    width: float = 1280.0
    height: float = 720.0
    visuals: list[Visual] = Field(default_factory=list)


class Report(_PBIPModel):
    """Reporte completo de un proyecto Power BI.

    Attributes:
        name: Nombre del reporte.
        pages: Páginas del reporte.
        theme: Tema aplicado (nombre o definición).
        format: Formato detectado en disco (PBIR/legacy).
    """

    name: str = "Report"
    pages: list[Page] = Field(default_factory=list)
    theme: dict[str, Any] | str | None = None
    format: ReportFormat = ReportFormat.PBIR

    def get_page(self, name: str) -> Page | None:
        """Devuelve la página por nombre interno o nombre visible."""
        return next(
            (p for p in self.pages if name in {p.name, p.display_name}),
            None,
        )


# ===========================================================================
# Proyecto PBIP (agregado raíz)
# ===========================================================================
class PbipProject(_PBIPModel):
    """Representa un proyecto PBIP cargado en memoria.

    Es el agregado raíz que combina el modelo semántico y el reporte, junto con
    las rutas físicas necesarias para volver a escribirlos.

    Attributes:
        name: Nombre del proyecto (sin extensión).
        root_path: Carpeta raíz del proyecto.
        pbip_file: Ruta del archivo ``.pbip`` (si existe).
        model_path: Carpeta ``*.SemanticModel``.
        report_path: Carpeta ``*.Report``.
        semantic_model: Modelo semántico cargado.
        report: Reporte cargado.
        model_format: Formato del modelo en disco.
        report_format: Formato del reporte en disco.
    """

    name: str
    root_path: Path
    pbip_file: Path | None = None
    model_path: Path | None = None
    report_path: Path | None = None
    semantic_model: SemanticModel | None = None
    report: Report | None = None
    model_format: ModelFormat = ModelFormat.UNKNOWN
    report_format: ReportFormat = ReportFormat.UNKNOWN

    def summary(self) -> dict[str, Any]:
        """Devuelve un resumen compacto del proyecto para mostrar al usuario."""
        sm = self.semantic_model
        rp = self.report
        return {
            "name": self.name,
            "root_path": str(self.root_path),
            "model_format": self.model_format.value,
            "report_format": self.report_format.value,
            "tables": len(sm.tables) if sm else 0,
            "measures": len(sm.all_measures()) if sm else 0,
            "relationships": len(sm.relationships) if sm else 0,
            "pages": len(rp.pages) if rp else 0,
            "visuals": sum(len(p.visuals) for p in rp.pages) if rp else 0,
        }


__all__ = [
    "Column",
    "Measure",
    "ModelFormat",
    "Page",
    "Partition",
    "PbipProject",
    "Relationship",
    "Report",
    "ReportFormat",
    "SemanticModel",
    "Table",
    "Visual",
]
