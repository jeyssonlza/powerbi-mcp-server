"""Temas corporativos y paletas de colores para reportes Power BI.

Genera archivos de tema en el formato JSON oficial de Power BI (el mismo que se
importa con *Ver > Temas > Buscar temas*) y ofrece paletas predefinidas además
de la creación de temas personalizados a partir de un color primario.
"""

from __future__ import annotations

import colorsys
from typing import Any

from powerbi_mcp.core.exceptions import ValidationError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

#: Paletas predefinidas (listas de colores HEX).
PALETTES: dict[str, list[str]] = {
    "corporate_blue": ["#1F4E79", "#2E75B6", "#5B9BD5", "#9DC3E6", "#BDD7EE", "#DEEBF7"],
    "executive_dark": ["#0B1F33", "#13476B", "#1C6E8C", "#2E8BC0", "#79C2D0", "#B1D4E0"],
    "vibrant": ["#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#9D4EDD", "#FF9F1C"],
    "earth": ["#582F0E", "#7F4F24", "#936639", "#A68A64", "#B6AD90", "#C2C5AA"],
    "pastel": ["#A0C4FF", "#BDB2FF", "#FFC6FF", "#FFADAD", "#FFD6A5", "#CAFFBF"],
    "monochrome_gray": ["#212529", "#495057", "#6C757D", "#ADB5BD", "#CED4DA", "#E9ECEF"],
    "finance_green": ["#0B3D2E", "#14664B", "#1E8C66", "#2BB789", "#7FD1AE", "#BFE8D6"],
}


def list_palettes() -> dict[str, list[str]]:
    """Devuelve las paletas predefinidas disponibles.

    Returns:
        Diccionario ``{nombre_paleta: [colores HEX]}``.
    """
    return dict(PALETTES)


def build_theme(
    name: str,
    *,
    palette: list[str] | str = "corporate_blue",
    background: str = "#FFFFFF",
    foreground: str = "#252423",
    table_accent: str | None = None,
    font_family: str = "Segoe UI",
) -> dict[str, Any]:
    """Construye un tema de Power BI en formato JSON.

    Args:
        name: Nombre del tema.
        palette: Lista de colores HEX o el nombre de una paleta predefinida.
        background: Color de fondo del lienzo.
        foreground: Color de texto principal.
        table_accent: Color de acento (por defecto, el primer color de la paleta).
        font_family: Familia tipográfica por defecto.

    Returns:
        Diccionario con la definición del tema, listo para serializar a JSON.

    Raises:
        ValidationError: Si la paleta nombrada no existe o los colores son inválidos.
    """
    colors = _resolve_palette(palette)
    for color in [*colors, background, foreground]:
        _validate_hex(color)

    accent = table_accent or colors[0]
    theme: dict[str, Any] = {
        "name": name,
        "dataColors": colors,
        "background": background,
        "foreground": foreground,
        "tableAccent": accent,
        "textClasses": {
            "title": {"fontFace": font_family, "fontSize": 14, "color": foreground},
            "header": {"fontFace": font_family, "fontSize": 12, "color": foreground},
            "label": {"fontFace": font_family, "fontSize": 10, "color": foreground},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": background}}}],
                    "border": [{"show": True, "color": {"solid": {"color": colors[-1]}}}],
                }
            }
        },
    }
    logger.info("Tema construido: %s (%d colores)", name, len(colors))
    return theme


def generate_palette_from_color(base_hex: str, *, count: int = 6) -> list[str]:
    """Genera una paleta armónica a partir de un color base.

    Crea variaciones de luminosidad/saturación en torno al color base para
    obtener una paleta coherente.

    Args:
        base_hex: Color base en formato ``#RRGGBB``.
        count: Número de colores a generar.

    Returns:
        Lista de colores HEX.

    Raises:
        ValidationError: Si el color base no es válido o ``count`` < 1.
    """
    _validate_hex(base_hex)
    if count < 1:
        raise ValidationError("count debe ser >= 1.", details={"count": count})

    r, g, b = _hex_to_rgb(base_hex)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

    palette: list[str] = []
    # Distribuye la luminosidad de oscuro a claro manteniendo el tono.
    for i in range(count):
        factor = 0.35 + (0.55 * i / max(count - 1, 1))
        nr, ng, nb = colorsys.hls_to_rgb(h, factor, s)
        palette.append(_rgb_to_hex(int(nr * 255), int(ng * 255), int(nb * 255)))
    return palette


# ---------------------------------------------------------------------------
# Helpers de color
# ---------------------------------------------------------------------------
def _resolve_palette(palette: list[str] | str) -> list[str]:
    """Resuelve una paleta por nombre o devuelve la lista tal cual."""
    if isinstance(palette, str):
        if palette not in PALETTES:
            raise ValidationError(
                "Paleta predefinida no encontrada.",
                details={"palette": palette, "available": sorted(PALETTES)},
            )
        return list(PALETTES[palette])
    if not palette:
        raise ValidationError("La paleta no puede estar vacía.")
    return palette


def _validate_hex(color: str) -> None:
    """Valida un color HEX ``#RRGGBB`` (o ``#RGB``)."""
    if not isinstance(color, str) or not color.startswith("#") or len(color) not in (4, 7):
        raise ValidationError("Color HEX inválido.", details={"color": color})
    try:
        int(color[1:], 16)
    except ValueError as exc:
        raise ValidationError("Color HEX inválido.", details={"color": color}) from exc


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convierte ``#RRGGBB`` a ``(r, g, b)``."""
    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convierte ``(r, g, b)`` a ``#RRGGBB``."""
    return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"


__all__ = [
    "PALETTES",
    "build_theme",
    "generate_palette_from_color",
    "list_palettes",
]
