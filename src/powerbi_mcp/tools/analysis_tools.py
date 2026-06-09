"""Herramientas para análisis de datos y rendimiento.

5 herramientas (en realidad 4 implementadas en el server.py):
- analyze_data_quality, profile_data, analyze_performance, run_best_practices, optimize_dax
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.session import session


def _tool(func: Any) -> Any:
    """Decorador: captura errores del dominio y los devuelve estructurados."""
    import functools

    from powerbi_mcp.core.exceptions import PowerBIMCPError
    from powerbi_mcp.core.logger import get_logger

    logger = get_logger(__name__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PowerBIMCPError as exc:
            logger.warning("Error en '%s': %s", func.__name__, exc)
            return {"ok": False, **exc.to_dict()}
        except Exception as exc:
            logger.exception("Error inesperado en '%s'", func.__name__)
            return {
                "ok": False,
                "error": exc.__class__.__name__,
                "code": "unexpected_error",
                "message": str(exc),
            }

    return wrapper


def register_analysis_tools(mcp: Any) -> None:
    """Registra todas las herramientas de análisis en la instancia MCP."""

    @mcp.tool()
    @_tool
    def analyze_data_quality(data: Any, outlier_factor: float = 1.5) -> dict[str, Any]:
        """Analiza la calidad de un conjunto de datos.

        Args:
            data: Datos (ruta o registros).
            outlier_factor: Factor IQR para marcar outliers.

        Returns:
            Métricas de calidad, hallazgos y puntuación global (0-100).
        """
        from powerbi_mcp.analysis.data_quality import analyze_data_quality as _analyze

        return {"ok": True, **_analyze(data, outlier_factor=outlier_factor)}

    @mcp.tool()
    @_tool
    def profile_data(data: Any, top_n: int = 5) -> dict[str, Any]:
        """Perfila un conjunto de datos (estadísticas por columna).

        Args:
            data: Datos (ruta o registros).
            top_n: Valores más frecuentes a reportar por columna.

        Returns:
            Resumen y perfil detallado por columna.
        """
        from powerbi_mcp.analysis.profiling import profile_dataset as _profile

        return {"ok": True, **_profile(data, top_n=top_n)}

    @mcp.tool()
    @_tool
    def analyze_performance() -> dict[str, Any]:
        """Analiza el rendimiento del modelo activo (análisis estático).

        Returns:
            Hallazgos de rendimiento priorizados con recomendaciones.
        """
        from powerbi_mcp.analysis.performance import analyze_performance as _analyze

        return {"ok": True, **_analyze(session.require_semantic_model())}

    @mcp.tool()
    @_tool
    def run_best_practices() -> dict[str, Any]:
        """Ejecuta el analizador de buenas prácticas (BPA) sobre el modelo activo.

        Returns:
            Violaciones detectadas con severidad y recomendaciones.
        """
        from powerbi_mcp.analysis.best_practices import run_best_practices as _run

        return {"ok": True, **_run(session.require_semantic_model())}

    @mcp.tool()
    @_tool
    def optimize_dax(expression: str) -> dict[str, Any]:
        """Analiza una expresión DAX y sugiere optimizaciones.

        Args:
            expression: Expresión DAX a revisar.

        Returns:
            Lista de sugerencias de optimización.
        """
        from powerbi_mcp.analysis.performance import optimize_dax as _optimize

        return {"ok": True, **_optimize(expression)}
