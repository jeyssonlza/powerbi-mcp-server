"""Validación de expresiones DAX (sintáctica, semántica y de buenas prácticas).

La validación se realiza en capas, de más barata a más costosa:

1. **Sintáctica**: balance de paréntesis/corchetes/comillas, tokens válidos.
2. **Semántica ligera**: las referencias ``Tabla[Columna]`` y ``[Medida]`` se
   contrastan contra el modelo cargado (si se proporciona).
3. **Buenas prácticas (BPA)**: patrones desaconsejados (división con ``/`` en
   lugar de :func:`DIVIDE`, uso de ``FILTER`` innecesario, columnas implícitas,
   etc.).

La validación semántica **profunda** (resolución completa de tipos y contexto)
requiere un motor Analysis Services; si hay una cadena de conexión configurada,
:func:`validate_dax` puede delegar en él (ver ``settings.as_connection_string``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.core.validators import ValidationReport

if TYPE_CHECKING:
    from powerbi_mcp.pbip.models import SemanticModel

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Catálogo (no exhaustivo) de funciones DAX reconocidas, para detectar typos.
# ---------------------------------------------------------------------------
_DAX_FUNCTIONS: frozenset[str] = frozenset(
    {
        # Agregación
        "SUM", "SUMX", "AVERAGE", "AVERAGEX", "MIN", "MINX", "MAX", "MAXX",
        "COUNT", "COUNTA", "COUNTX", "COUNTROWS", "DISTINCTCOUNT", "DISTINCTCOUNTNOBLANK",
        "PRODUCT", "PRODUCTX", "MEDIAN", "MEDIANX", "PERCENTILE.INC", "PERCENTILE.EXC",
        # Filtro / contexto
        "CALCULATE", "CALCULATETABLE", "FILTER", "ALL", "ALLEXCEPT", "ALLSELECTED",
        "ALLNOBLANKROW", "REMOVEFILTERS", "KEEPFILTERS", "VALUES", "DISTINCT",
        "EARLIER", "EARLIEST", "RELATED", "RELATEDTABLE", "USERELATIONSHIP",
        "CROSSFILTER", "SELECTEDVALUE", "HASONEVALUE", "ISFILTERED", "ISCROSSFILTERED",
        # Lógica / información
        "IF", "IFERROR", "SWITCH", "AND", "OR", "NOT", "TRUE", "FALSE", "BLANK",
        "ISBLANK", "ISERROR", "ISEMPTY", "ISNUMBER", "ISTEXT", "COALESCE", "DIVIDE",
        # Texto
        "CONCATENATE", "CONCATENATEX", "FORMAT", "LEFT", "RIGHT", "MID", "LEN",
        "UPPER", "LOWER", "TRIM", "SUBSTITUTE", "REPLACE", "SEARCH", "FIND",
        "VALUE", "UNICHAR", "REPT", "COMBINEVALUES",
        # Fecha/hora e inteligencia de tiempo
        "DATE", "TODAY", "NOW", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
        "WEEKDAY", "WEEKNUM", "EOMONTH", "EDATE", "DATEDIFF", "DATEADD", "DATESYTD",
        "DATESMTD", "DATESQTD", "TOTALYTD", "TOTALMTD", "TOTALQTD", "SAMEPERIODLASTYEAR",
        "PARALLELPERIOD", "PREVIOUSMONTH", "PREVIOUSYEAR", "NEXTMONTH", "NEXTYEAR",
        "STARTOFMONTH", "ENDOFMONTH", "STARTOFYEAR", "ENDOFYEAR", "CALENDAR",
        "CALENDARAUTO", "FIRSTDATE", "LASTDATE",
        # Tablas
        "SUMMARIZE", "SUMMARIZECOLUMNS", "ADDCOLUMNS", "SELECTCOLUMNS", "ROW",
        "GROUPBY", "NATURALINNERJOIN", "NATURALLEFTOUTERJOIN", "UNION", "INTERSECT",
        "EXCEPT", "GENERATE", "GENERATEALL", "GENERATESERIES", "TOPN", "RANKX",
        "RANK.EQ", "DATATABLE", "TREATAS", "VAR", "RETURN", "CROSSJOIN",
        # Matemáticas / estadística
        "ABS", "ROUND", "ROUNDUP", "ROUNDDOWN", "INT", "TRUNC", "CEILING", "FLOOR",
        "MOD", "POWER", "SQRT", "EXP", "LN", "LOG", "LOG10", "SIGN", "RAND", "PI",
        "QUOTIENT", "GCD", "LCM", "FACT", "COMBIN",
    }
)

#: Palabras clave estructurales (no son funciones).
_DAX_KEYWORDS: frozenset[str] = frozenset({"VAR", "RETURN", "IN", "NOT", "ORDER", "BY"})

# Regex de tokens
_RE_COLUMN_REF = re.compile(r"(?:'([^']+)'|(\w+))\s*\[([^\]]+)\]")
_RE_MEASURE_REF = re.compile(r"(?<![\w'])\[([^\]]+)\]")
_RE_FUNCTION_CALL = re.compile(r"\b([A-Z][A-Z0-9_.]*)\s*\(")
_RE_STRING_LITERAL = re.compile(r'"(?:[^"]|"")*"')
_RE_COMMENT_LINE = re.compile(r"//[^\n]*")
_RE_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)


@dataclass
class DaxValidationResult:
    """Resultado de validar una expresión DAX.

    Attributes:
        is_valid: ``True`` si no hay errores (puede haber advertencias).
        errors: Lista de errores que invalidan la expresión.
        warnings: Advertencias (no bloquean, pero conviene revisar).
        best_practices: Sugerencias de buenas prácticas.
        referenced_columns: Referencias ``Tabla[Columna]`` detectadas.
        referenced_measures: Referencias ``[Medida]`` detectadas.
        functions_used: Funciones DAX detectadas.
    """

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    best_practices: list[str] = field(default_factory=list)
    referenced_columns: list[str] = field(default_factory=list)
    referenced_measures: list[str] = field(default_factory=list)
    functions_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serializa el resultado a diccionario."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "best_practices": self.best_practices,
            "referenced_columns": self.referenced_columns,
            "referenced_measures": self.referenced_measures,
            "functions_used": self.functions_used,
        }


def _strip_noise(expression: str) -> str:
    """Elimina comentarios y literales de cadena para analizar la estructura.

    Sustituye las cadenas por espacios para no contar paréntesis/corchetes que
    aparezcan dentro de literales de texto.
    """
    no_block = _RE_COMMENT_BLOCK.sub(" ", expression)
    no_line = _RE_COMMENT_LINE.sub(" ", no_block)
    no_strings = _RE_STRING_LITERAL.sub('""', no_line)
    return no_strings


def _check_balanced(expression: str, result: DaxValidationResult) -> None:
    """Verifica el balance de paréntesis, corchetes y comillas."""
    pairs = {")": "(", "]": "["}
    stack: list[str] = []
    for ch in expression:
        if ch in "([":
            stack.append(ch)
        elif ch in ")]":
            if not stack or stack[-1] != pairs[ch]:
                result.errors.append(f"Símbolo de cierre '{ch}' sin apertura correspondiente.")
                result.is_valid = False
                return
            stack.pop()
    if stack:
        result.errors.append(
            f"Faltan {len(stack)} símbolo(s) de cierre para: {''.join(stack)}"
        )
        result.is_valid = False

    # Comillas dobles balanceadas (tras normalizar "" escapadas).
    quote_count = expression.replace('""', "").count('"')
    if quote_count % 2 != 0:
        result.errors.append("Comillas dobles desbalanceadas en un literal de texto.")
        result.is_valid = False


def _check_functions(expression: str, result: DaxValidationResult) -> None:
    """Detecta funciones usadas y advierte de posibles nombres no reconocidos."""
    used = {m.group(1) for m in _RE_FUNCTION_CALL.finditer(expression)}
    result.functions_used = sorted(used)
    for fn in used:
        if fn in _DAX_KEYWORDS:
            continue
        if fn not in _DAX_FUNCTIONS:
            result.warnings.append(
                f"Función '{fn}' no está en el catálogo conocido "
                "(puede ser válida, una función nueva o un error tipográfico)."
            )


def _extract_references(expression: str, result: DaxValidationResult) -> None:
    """Extrae referencias a columnas y medidas de la expresión."""
    columns: set[str] = set()
    for match in _RE_COLUMN_REF.finditer(expression):
        table = match.group(1) or match.group(2)
        column = match.group(3)
        columns.add(f"{table}[{column}]")
    result.referenced_columns = sorted(columns)

    # Medidas: [X] que no van precedidas de un nombre de tabla.
    measures: set[str] = set()
    for match in _RE_MEASURE_REF.finditer(expression):
        # Evita capturar la parte [Columna] de Tabla[Columna].
        start = match.start()
        preceding = expression[:start].rstrip()
        if preceding and (preceding[-1].isalnum() or preceding[-1] in "'_"):
            continue
        measures.add(match.group(1))
    result.referenced_measures = sorted(measures)


def _check_best_practices(expression: str, result: DaxValidationResult) -> None:
    """Aplica reglas de buenas prácticas habituales sobre DAX."""
    # División con '/' en lugar de DIVIDE (riesgo de división por cero).
    if re.search(r"[\w\])]\s*/\s*[\w('\[]", expression) and "DIVIDE" not in expression.upper():
        result.best_practices.append(
            "Usa DIVIDE(numerador, denominador) en lugar de '/' para manejar "
            "la división por cero de forma segura."
        )
    # IF(ISBLANK(x), ...) -> COALESCE
    if re.search(r"\bIF\s*\(\s*ISBLANK\b", expression, re.IGNORECASE):
        result.best_practices.append(
            "Considera COALESCE(...) en lugar de IF(ISBLANK(...), ...) para "
            "expresiones más concisas."
        )
    # CALCULATE(... , FILTER(Tabla, Tabla[col] = x)) cuando basta un predicado.
    if re.search(r"FILTER\s*\(\s*'?\w", expression, re.IGNORECASE) and "CALCULATE" in expression.upper():
        result.best_practices.append(
            "Si filtras por una condición simple, un predicado directo en "
            "CALCULATE suele ser más eficiente que FILTER(Tabla, ...)."
        )
    # Uso de comillas simples innecesarias en tablas sin espacios (estético).
    if re.search(r"'(\w+)'\[", expression):
        result.best_practices.append(
            "Las comillas simples solo son necesarias en nombres de tabla con "
            "espacios o caracteres especiales."
        )


def _check_semantics(
    result: DaxValidationResult, model: SemanticModel
) -> None:
    """Contrasta las referencias detectadas contra el modelo cargado."""
    table_columns: set[str] = set()
    measure_names: set[str] = set()
    table_names: set[str] = set()
    for table in model.tables:
        table_names.add(table.name)
        for col in table.columns:
            table_columns.add(f"{table.name}[{col.name}]")
        for meas in table.measures:
            measure_names.add(meas.name)

    for ref in result.referenced_columns:
        if ref not in table_columns:
            # Puede ser una medida escrita como Tabla[Medida]; comprobar.
            col_name = ref.split("[", 1)[1].rstrip("]")
            if col_name in measure_names:
                continue
            result.warnings.append(
                f"La referencia {ref} no coincide con ninguna columna del modelo."
            )

    for ref in result.referenced_measures:
        if ref not in measure_names and ref not in {
            c.split("[", 1)[1].rstrip("]") for c in table_columns
        }:
            result.warnings.append(
                f"La medida/columna [{ref}] no existe en el modelo."
            )


def validate_dax(
    expression: str,
    *,
    model: SemanticModel | None = None,
    check_best_practices: bool = True,
) -> DaxValidationResult:
    """Valida una expresión DAX (sintaxis, semántica ligera y buenas prácticas).

    Args:
        expression: Expresión DAX a validar.
        model: Modelo semántico para contrastar referencias (opcional).
        check_best_practices: Si es ``True``, incluye sugerencias de estilo.

    Returns:
        Un :class:`DaxValidationResult` con el detalle del análisis.
    """
    result = DaxValidationResult()

    if not expression or not expression.strip():
        result.is_valid = False
        result.errors.append("La expresión DAX está vacía.")
        return result

    cleaned = _strip_noise(expression)

    _check_balanced(cleaned, result)
    _check_functions(cleaned, result)
    _extract_references(cleaned, result)

    if check_best_practices:
        _check_best_practices(cleaned, result)

    if model is not None and result.is_valid:
        _check_semantics(result, model)

    logger.debug(
        "DAX validado: valido=%s, errores=%d, warnings=%d",
        result.is_valid,
        len(result.errors),
        len(result.warnings),
    )
    return result


def validate_measure_name(name: str, model: SemanticModel | None = None) -> ValidationReport:
    """Valida el nombre de una medida (convención + unicidad en el modelo).

    Args:
        name: Nombre propuesto para la medida.
        model: Modelo para comprobar duplicados (opcional).

    Returns:
        Un :class:`~powerbi_mcp.core.validators.ValidationReport` con hallazgos.
    """
    from powerbi_mcp.core.validators import check_naming_convention

    report = check_naming_convention(name, kind="measure")
    if model is not None:
        existing = {m.name for _, m in model.all_measures()}
        if name in existing:
            report.add(
                "error",
                "uniqueness.measure",
                "Ya existe una medida con ese nombre en el modelo.",
                target=name,
            )
    return report


__all__ = [
    "DaxValidationResult",
    "validate_dax",
    "validate_measure_name",
]
