"""Generación de visuales HTML interactivos e independientes (Plotly).

Produce archivos HTML autónomos (un solo archivo, con Plotly embebido o por CDN)
que pueden abrirse en cualquier navegador, compartirse o incrustarse. Útil para
previsualizar resultados (incluidos los de IA) sin abrir Power BI.

Cubre los tipos de gráfico más habituales y un modo de tablero (varios visuales
en una sola página) con tema corporativo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from powerbi_mcp.core.exceptions import ValidationError, VisualError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

CHART_TYPES = frozenset(
    {
        "bar", "column", "line", "area", "pie", "donut", "scatter",
        "histogram", "box", "heatmap", "treemap", "funnel", "waterfall",
        "gauge", "table", "kpi_card",
    }
)


def create_html_visual(
    data: Any,
    chart_type: str,
    *,
    x: str | None = None,
    y: str | list[str] | None = None,
    color: str | None = None,
    title: str = "",
    output_path: str | Path | None = None,
    palette: list[str] | None = None,
    include_plotlyjs: str | bool = "cdn",
) -> dict[str, Any]:
    """Crea un visual HTML interactivo a partir de datos tabulares.

    Args:
        data: Datos (DataFrame, registros, dict de columnas o ruta de archivo).
        chart_type: Tipo de gráfico (ver :data:`CHART_TYPES`).
        x: Columna para el eje X / categorías.
        y: Columna(s) para el eje Y / valores.
        color: Columna para agrupar por color (series/leyenda).
        title: Título del gráfico.
        output_path: Si se indica, guarda el HTML en esa ruta.
        palette: Lista de colores HEX para la secuencia de datos.
        include_plotlyjs: ``"cdn"`` (ligero, requiere internet), ``True``
            (embebido, autónomo) o ``"directory"``.

    Returns:
        Diccionario con ``html`` (cadena) y, si aplica, ``path``.

    Raises:
        ValidationError: Si el tipo de gráfico no es válido.
        VisualError: Si Plotly no está instalado o falla la generación.
    """
    if chart_type not in CHART_TYPES:
        raise ValidationError(
            "Tipo de gráfico no válido.",
            details={"chart_type": chart_type, "valid": sorted(CHART_TYPES)},
        )

    # Import diferido: generar un visual PBIR (JSON) no requiere pandas/numpy;
    # solo el renderizado HTML los necesita.
    from powerbi_mcp.ai._base import to_dataframe

    df = to_dataframe(data)
    fig = _build_figure(df, chart_type, x=x, y=y, color=color, title=title, palette=palette)

    try:
        html = fig.to_html(include_plotlyjs=include_plotlyjs, full_html=True)
    except Exception as exc:
        raise VisualError("Fallo al renderizar el HTML del visual.", details={"error": str(exc)}) from exc

    result: dict[str, Any] = {"chart_type": chart_type, "html": html}
    if output_path:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        result["path"] = str(path)
        logger.info("Visual HTML guardado: %s", path)
    return result


def _scalar_column(value: str | list[str] | None) -> str | None:
    """Reduce una columna o lista de columnas a un único nombre escalar."""
    if value is None:
        return None
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _build_figure(
    df: Any,
    chart_type: str,
    *,
    x: str | None,
    y: str | list[str] | None,
    color: str | None,
    title: str,
    palette: list[str] | None,
) -> Any:
    """Construye la figura Plotly según el tipo de gráfico."""
    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError as exc:  # pragma: no cover
        raise VisualError("plotly no está instalado.") from exc

    seq = palette
    common: dict[str, Any] = {"title": title}
    if seq:
        common["color_discrete_sequence"] = seq

    y_scalar = _scalar_column(y)

    if chart_type in {"bar", "column"}:
        fig = px.bar(df, x=x, y=y, color=color, orientation="v" if chart_type == "column" else "h", **common)
    elif chart_type == "line":
        fig = px.line(df, x=x, y=y, color=color, markers=True, **common)
    elif chart_type == "area":
        fig = px.area(df, x=x, y=y, color=color, **common)
    elif chart_type in {"pie", "donut"}:
        hole = 0.5 if chart_type == "donut" else 0.0
        fig = px.pie(df, names=x, values=y, hole=hole, **common)
    elif chart_type == "scatter":
        fig = px.scatter(df, x=x, y=y, color=color, **common)
    elif chart_type == "histogram":
        fig = px.histogram(df, x=x, color=color, **common)
    elif chart_type == "box":
        fig = px.box(df, x=x, y=y, color=color, **common)
    elif chart_type == "heatmap":
        fig = px.imshow(df.corr(numeric_only=True), text_auto=True, title=title)
    elif chart_type == "treemap":
        fig = px.treemap(df, path=[x] if x else None, values=y, **common)
    elif chart_type == "funnel":
        fig = px.funnel(df, x=y, y=x, **common)
    elif chart_type == "waterfall":
        fig = _waterfall(go, df, x, y_scalar, title)
    elif chart_type == "gauge":
        fig = _gauge(go, df, y_scalar, title)
    elif chart_type == "kpi_card":
        fig = _kpi_card(go, df, y_scalar, title)
    elif chart_type == "table":
        fig = _table(go, df, title)
    else:  # pragma: no cover - protegido por validación previa
        raise ValidationError("Tipo de gráfico no soportado.", details={"chart_type": chart_type})

    fig.update_layout(template="plotly_white", margin={"l": 40, "r": 20, "t": 50, "b": 40})
    return fig


def _waterfall(go: Any, df: Any, x: str | None, y: str | None, title: str) -> Any:
    """Construye un gráfico de cascada."""
    if not (x and y):
        raise ValidationError("Waterfall requiere 'x' e 'y'.")
    return go.Figure(
        go.Waterfall(x=df[x].tolist(), y=df[y].tolist(), connector={"line": {"color": "gray"}})
    ).update_layout(title=title)


def _gauge(go: Any, df: Any, y: str | None, title: str) -> Any:
    """Construye un medidor (gauge) con el primer valor de la columna ``y``."""
    if not y:
        raise ValidationError("Gauge requiere la columna 'y'.")
    value = float(df[y].iloc[0])
    max_val = float(df[y].max()) * 1.2 or value * 1.2 or 1
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title},
            gauge={"axis": {"range": [0, max_val]}},
        )
    )


def _kpi_card(go: Any, df: Any, y: str | None, title: str) -> Any:
    """Construye una tarjeta KPI (número grande con delta)."""
    if not y:
        raise ValidationError("KPI card requiere la columna 'y'.")
    values = df[y].tolist()
    value = float(values[-1])
    ref = float(values[0]) if len(values) > 1 else value
    return go.Figure(
        go.Indicator(
            mode="number+delta",
            value=value,
            delta={"reference": ref},
            title={"text": title},
        )
    )


def _table(go: Any, df: Any, title: str) -> Any:
    """Construye una tabla."""
    return go.Figure(
        go.Table(
            header={"values": list(df.columns), "fill_color": "#1F4E79", "font": {"color": "white"}},
            cells={"values": [df[c].tolist() for c in df.columns]},
        )
    ).update_layout(title=title)


__all__ = ["CHART_TYPES", "create_html_visual"]
