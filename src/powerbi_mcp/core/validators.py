"""Validadores base reutilizables del servidor Power BI MCP.

Reúne validaciones transversales usadas por varios dominios:

- Rutas de archivos y directorios (existencia, tipo).
- Nombres de objetos del modelo (tablas, columnas, medidas).
- Convenciones de nomenclatura de Power BI (buenas prácticas).

Las funciones que validan "dureza" lanzan :class:`ValidationError`; las que
solo informan devuelven estructuras de datos para que el llamador decida.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from powerbi_mcp.core.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Expresiones regulares de nomenclatura
# ---------------------------------------------------------------------------
#: Caracteres no permitidos en nombres de objetos de Power BI.
_INVALID_NAME_CHARS = re.compile(r'[.\x00-\x1f\x7f]')

#: Convención recomendada para medidas: PascalCase o "Title Case" con espacios.
_MEASURE_NAME_OK = re.compile(r"^[A-Z][A-Za-z0-9 %#/()\-_]*$")

#: Convención recomendada para tablas/columnas: empieza por letra.
_IDENTIFIER_OK = re.compile(r"^[A-Za-z][A-Za-z0-9 _]*$")


@dataclass
class ValidationIssue:
    """Un hallazgo de validación no fatal (advertencia o sugerencia).

    Attributes:
        level: ``"error"``, ``"warning"`` o ``"info"``.
        rule: Identificador corto de la regla (ej. ``"naming.measure"``).
        message: Descripción legible del hallazgo.
        target: Objeto afectado (nombre de tabla/columna/medida).
        suggestion: Corrección o recomendación sugerida.
    """

    level: str
    rule: str
    message: str
    target: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Serializa el hallazgo a diccionario."""
        return {
            "level": self.level,
            "rule": self.rule,
            "message": self.message,
            "target": self.target,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationReport:
    """Colección de hallazgos de validación con utilidades de agregación.

    Attributes:
        issues: Lista de :class:`ValidationIssue` detectados.
    """

    issues: list[ValidationIssue] = field(default_factory=list)

    def add(
        self,
        level: str,
        rule: str,
        message: str,
        *,
        target: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Añade un hallazgo al reporte."""
        self.issues.append(
            ValidationIssue(level, rule, message, target=target, suggestion=suggestion)
        )

    @property
    def has_errors(self) -> bool:
        """True si existe al menos un hallazgo de nivel ``error``."""
        return any(i.level == "error" for i in self.issues)

    @property
    def is_clean(self) -> bool:
        """True si no hay ningún hallazgo."""
        return not self.issues

    def summary(self) -> dict[str, int]:
        """Devuelve el conteo de hallazgos por nivel."""
        counts = {"error": 0, "warning": 0, "info": 0}
        for issue in self.issues:
            counts[issue.level] = counts.get(issue.level, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        """Serializa el reporte completo a diccionario."""
        return {
            "summary": self.summary(),
            "is_clean": self.is_clean,
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Validación de rutas
# ---------------------------------------------------------------------------
def validate_existing_path(path: str | Path, *, must_be_dir: bool | None = None) -> Path:
    """Valida que una ruta exista y opcionalmente que sea archivo o directorio.

    Args:
        path: Ruta a validar.
        must_be_dir: Si es ``True`` exige directorio; si es ``False`` exige
            archivo; si es ``None`` acepta cualquiera.

    Returns:
        La ruta resuelta como :class:`~pathlib.Path` absoluta.

    Raises:
        ValidationError: Si la ruta no existe o no cumple el tipo requerido.
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise ValidationError(
            "La ruta no existe.",
            details={"path": str(resolved)},
        )
    if must_be_dir is True and not resolved.is_dir():
        raise ValidationError(
            "Se esperaba un directorio.",
            details={"path": str(resolved)},
        )
    if must_be_dir is False and not resolved.is_file():
        raise ValidationError(
            "Se esperaba un archivo.",
            details={"path": str(resolved)},
        )
    return resolved


# ---------------------------------------------------------------------------
# Validación de nombres de objetos
# ---------------------------------------------------------------------------
def validate_object_name(name: str, *, kind: str = "objeto") -> str:
    """Valida que un nombre de objeto del modelo sea utilizable.

    Aplica las restricciones duras de Power BI (no vacío, sin caracteres de
    control ni punto). Las recomendaciones de estilo se reportan aparte con
    :func:`check_naming_convention`.

    Args:
        name: Nombre propuesto.
        kind: Tipo de objeto, solo para el mensaje de error.

    Returns:
        El nombre saneado (sin espacios sobrantes en los extremos).

    Raises:
        ValidationError: Si el nombre es inválido.
    """
    clean = name.strip()
    if not clean:
        raise ValidationError(f"El nombre del {kind} no puede estar vacío.")
    if _INVALID_NAME_CHARS.search(clean):
        raise ValidationError(
            f"El nombre del {kind} contiene caracteres no permitidos "
            "(puntos o caracteres de control).",
            details={"name": name},
        )
    if len(clean) > 128:
        raise ValidationError(
            f"El nombre del {kind} excede los 128 caracteres.",
            details={"length": len(clean)},
        )
    return clean


def check_naming_convention(
    name: str,
    *,
    kind: str = "table",
    report: ValidationReport | None = None,
) -> ValidationReport:
    """Evalúa un nombre contra las convenciones recomendadas (no fatal).

    Reglas aplicadas (buenas prácticas habituales de Power BI):

    - Tablas/columnas: deben empezar por letra y no tener dobles espacios.
    - Medidas: PascalCase / Title Case, sin notación húngara.
    - No usar prefijos técnicos (``tbl_``, ``dim_`` en columnas, etc.).

    Args:
        name: Nombre a evaluar.
        kind: ``"table"``, ``"column"`` o ``"measure"``.
        report: Reporte donde acumular hallazgos. Si es ``None`` se crea uno.

    Returns:
        El :class:`ValidationReport` con los hallazgos añadidos.
    """
    report = report or ValidationReport()
    rule_ns = f"naming.{kind}"

    if "  " in name:
        report.add(
            "warning",
            rule_ns,
            "El nombre contiene espacios dobles.",
            target=name,
            suggestion=re.sub(r"\s+", " ", name).strip(),
        )

    if kind in {"table", "column"}:
        if not _IDENTIFIER_OK.match(name):
            report.add(
                "warning",
                rule_ns,
                "Debe empezar por letra y evitar caracteres especiales.",
                target=name,
            )
        if re.match(r"^(tbl|dim|fact|fct)[_A-Z]", name, re.IGNORECASE):
            report.add(
                "info",
                rule_ns,
                "Evita prefijos técnicos en nombres visibles al usuario.",
                target=name,
                suggestion=re.sub(r"^(tbl|dim|fact|fct)[_]?", "", name, flags=re.IGNORECASE),
            )

    if kind == "measure" and not _MEASURE_NAME_OK.match(name):
        report.add(
            "info",
            rule_ns,
            "Se recomienda iniciar la medida con mayúscula (Title/PascalCase).",
            target=name,
        )

    return report


def slugify(value: str, *, separator: str = "_") -> str:
    """Convierte un texto a un slug seguro para nombres de archivo/identificadores.

    Args:
        value: Texto de entrada.
        separator: Carácter separador a usar entre palabras.

    Returns:
        Una cadena en minúsculas, sin acentos ni caracteres especiales.
    """
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.lower().strip()
    ascii_only = re.sub(r"[^a-z0-9]+", separator, ascii_only)
    return ascii_only.strip(separator)


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "check_naming_convention",
    "slugify",
    "validate_existing_path",
    "validate_object_name",
]
