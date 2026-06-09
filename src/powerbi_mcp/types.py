"""Type hints y TypedDicts para Power BI MCP.

Define tipos reutilizables para:
- Especificación de campos (FieldSpec)
- Niveles de compatibilidad TMSL (CompatibilityLevel)
- Estructuras de datos comunes (TableSpec, MeasureSpec)
- Configuración y validación

Permite type-checking más estricto y documentación mejorada.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, TypedDict

# ===========================================================================
# ENUMERACIONES
# ===========================================================================


class CompatibilityLevel(Enum):
    """Niveles de compatibilidad TMSL soportados.

    Atributos:
        LEVEL_1100: SQL Server 2012 / AS 2012 (Tabular 100).
        LEVEL_1200: SQL Server 2016 / AS 2016 (Tabular 200).
        LEVEL_1400: SQL Server 2017 / AS 2017 (Tabular 400).
        LEVEL_1500: SQL Server 2019 / AS 2019 (Tabular 500).
        LEVEL_1550: Power BI / AS 2022 (Tabular 550).
    """

    LEVEL_1100 = 1100
    LEVEL_1200 = 1200
    LEVEL_1400 = 1400
    LEVEL_1500 = 1500
    LEVEL_1550 = 1550


class DataType(Enum):
    """Tipos de datos TMSL soportados.

    Atributos:
        INT64: Entero de 64 bits.
        DOUBLE: Decimal de precisión doble.
        DECIMAL: Decimal de precisión arbitraria.
        STRING: Texto Unicode.
        BOOLEAN: Valor lógico.
        DATE_TIME: Fecha y hora.
        DATETIME_OFFSET: Fecha/hora con zona horaria.
        BINARY: Datos binarios.
        VARIANT: Tipo genérico (no recomendado).
    """

    INT64 = "int64"
    DOUBLE = "double"
    DECIMAL = "decimal"
    STRING = "string"
    BOOLEAN = "boolean"
    DATE_TIME = "dateTime"
    DATETIME_OFFSET = "dateTimeOffset"
    BINARY = "binary"
    VARIANT = "variant"


# ===========================================================================
# TypedDicts: ESPECIFICACIÓN DE CAMPOS
# ===========================================================================


class FieldSpec(TypedDict, total=False):
    """Especificación de un campo (columna) en una tabla.

    Attributes:
        name: Nombre del campo.
        data_type: Tipo de dato (int64, double, string, etc.).
        nullable: Si el campo permite valores nulos.
        source_column: Nombre de la columna en el origen (para campos importados).
        description: Descripción del campo.
        format_string: Formato de visualización (ej: "#,0.00").
        hidden: Si el campo está oculto en el modelo.
        sort_by_column: Columna por la que se ordena este campo.
    """

    name: str
    data_type: str
    nullable: bool
    source_column: str
    description: str
    format_string: str
    hidden: bool
    sort_by_column: str


class ColumnMetadata(TypedDict, total=False):
    """Metadatos de columna para documentación.

    Attributes:
        name: Nombre de la columna.
        dataType: Tipo de dato.
        description: Descripción clara del contenido.
        sourceColumn: Columna fuente en la base de datos.
        hidden: Si está oculta.
        formatString: Formato de visualización.
        dataCategory: Categoría de datos (Address, WebUrl, etc.).
    """

    name: str
    dataType: str
    description: str
    sourceColumn: str
    hidden: bool
    formatString: str
    dataCategory: str


class MeasureSpec(TypedDict, total=False):
    """Especificación de una medida (medida calculada).

    Attributes:
        name: Nombre de la medida.
        expression: Expresión DAX.
        description: Descripción de la medida.
        format_string: Formato de visualización.
        hidden: Si está oculta.
        data_type: Tipo de resultado esperado.
    """

    name: str
    expression: str
    description: str
    format_string: str
    hidden: bool
    data_type: str


class TableSpec(TypedDict, total=False):
    """Especificación de una tabla en el modelo.

    Attributes:
        name: Nombre de la tabla.
        description: Descripción de la tabla.
        columns: Lista de especificaciones de columnas.
        measures: Lista de especificaciones de medidas.
        is_hidden: Si la tabla está oculta.
        is_calculated: Si es una tabla calculada.
        partition_source: Fuente de datos (M, SQL, etc.).
    """

    name: str
    description: str
    columns: list[FieldSpec]
    measures: list[MeasureSpec]
    is_hidden: bool
    is_calculated: bool
    partition_source: str


class RelationshipSpec(TypedDict, total=False):
    """Especificación de una relación entre tablas.

    Attributes:
        name: Nombre de la relación.
        from_table: Tabla de origen.
        from_column: Columna de origen.
        to_table: Tabla de destino.
        to_column: Columna de destino.
        cross_filtering: Dirección de filtrado (bothDirections, oneDirection, none).
        is_active: Si la relación está activa.
    """

    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cross_filtering: str
    is_active: bool


# ===========================================================================
# TypedDicts: CONFIGURACIÓN Y VALIDACIÓN
# ===========================================================================


class PBIPProjectConfig(TypedDict, total=False):
    """Configuración de un proyecto PBIP.

    Attributes:
        name: Nombre del proyecto.
        version: Versión del proyecto.
        semantic_model_folder: Carpeta del modelo semántico.
        report_folder: Carpeta del reporte.
        compatibility_level: Nivel de compatibilidad TMSL.
    """

    name: str
    version: str
    semantic_model_folder: str
    report_folder: str
    compatibility_level: int


class WriterOptions(TypedDict, total=False):
    """Opciones para escritura segura de archivos.

    Attributes:
        dry_run: Previsualizar sin escribir.
        backup: Crear respaldo antes de escribir.
        reason: Motivo de la escritura (para auditoría).
        atomic: Escritura atómica (temp + replace).
        create_parents: Crear carpetas padre si no existen.
    """

    dry_run: bool
    backup: bool
    reason: str
    atomic: bool
    create_parents: bool


class ValidationResult(TypedDict, total=False):
    """Resultado de validación de estructura/datos.

    Attributes:
        valid: Si la validación pasó.
        errors: Lista de errores encontrados.
        warnings: Lista de advertencias.
        stats: Estadísticas adicionales.
    """

    valid: bool
    errors: list[str]
    warnings: list[str]
    stats: dict[str, Any]


class DocumentationConfig(TypedDict, total=False):
    """Configuración para generación de documentación.

    Attributes:
        output_dir: Directorio donde escribir archivos.
        formats: Formatos a generar (markdown, html).
        include_best_practices: Incluir análisis BPA.
        include_data_dictionary: Incluir diccionario de datos.
        include_relationships: Incluir diagrama de relaciones.
        theme: Tema CSS (light, dark).
    """

    output_dir: str
    formats: list[Literal["markdown", "html"]]
    include_best_practices: bool
    include_data_dictionary: bool
    include_relationships: bool
    theme: Literal["light", "dark"]


# ===========================================================================
# TIPOS GENÉRICOS
# ===========================================================================


# Tipo para expresiones DAX (cadena que contiene expresión DAX)
DAXExpression = str

# Tipo para nombres de objeto (tabla, columna, medida)
ObjectName = str

# Tipo para rutas de archivo
FilePath = str | Any  # Path o str

# Tipo para diccionarios genéricos de JSON
JSONObject = dict[str, Any]

# Tipo para resultados genéricos de operación
OperationResult = dict[str, Any]


__all__ = [
    "ColumnMetadata",
    "CompatibilityLevel",
    "DAXExpression",
    "DataType",
    "DocumentationConfig",
    "FieldSpec",
    "FilePath",
    "JSONObject",
    "MeasureSpec",
    "ObjectName",
    "OperationResult",
    "PBIPProjectConfig",
    "RelationshipSpec",
    "TableSpec",
    "ValidationResult",
    "WriterOptions",
]
