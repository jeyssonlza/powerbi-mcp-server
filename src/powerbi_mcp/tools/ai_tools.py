"""Herramientas de Machine Learning e IA para Power BI.

8 herramientas:
- detect_anomalies, run_clustering, forecast_series, rfm_segmentation
- correlation_analysis, decision_tree_explain, train_regression, train_classification
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


def _commit_model(
    reason: str,
    *,
    action: str,
    object_type: str,
    object_name: str,
    dry_run: bool,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Persiste el modelo activo y registra changelog + auditoría."""
    from powerbi_mcp.docs.changelog import record_change
    from powerbi_mcp.pbip.writer import save_semantic_model
    from powerbi_mcp.security.audit import audit

    project = session.require()
    try:
        save_result = save_semantic_model(project, reason=reason, dry_run=dry_run)
    finally:
        if dry_run:
            session.reload()
    if not dry_run:
        record_change(
            project.root_path,
            action=action,
            object_type=object_type,
            object_name=object_name,
            description=reason,
        )
    audit(action, target=object_name, status="success", details={"dry_run": dry_run})
    return {"ok": True, "dry_run": dry_run, "save": save_result, **payload}


def _maybe_integrate(
    result: Any, integrate_as: str | None, integrate_format: str, dry_run: bool
) -> dict[str, Any]:
    """Integra opcionalmente un resultado de IA al modelo activo como tabla.

    Args:
        result: El :class:`AIResult` producido por un modelo de IA.
        integrate_as: Nombre de la tabla a crear. Si es ``None``, no integra.
        integrate_format: ``"dax"`` o ``"m"``.
        dry_run: Si es ``True``, previsualiza sin escribir.

    Returns:
        El resultado de IA serializado y, si aplica, el detalle de integración.
    """
    payload: dict[str, Any] = {"result": result.to_dict()}
    if not integrate_as:
        return {"ok": True, **payload}

    from powerbi_mcp.ai.integration import integrate_ai_result

    session.require()
    integration = integrate_ai_result(
        session.require_semantic_model(), result, integrate_as, format=integrate_format
    )
    commit = _commit_model(
        f"integrate AI {result.model_type} -> {integrate_as}",
        action="added", object_type="table", object_name=integrate_as,
        dry_run=dry_run, payload={"integration": integration},
    )
    return {**commit, **payload}


def register_ai_tools(mcp: Any) -> None:
    """Registra todas las herramientas de IA en la instancia MCP."""

    @mcp.tool()
    @_tool
    def detect_anomalies(
        data: Any,
        columns: list[str] | None = None,
        method: str = "isolation_forest",
        contamination: float = 0.05,
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Detecta anomalías en datos y, opcionalmente, las integra al modelo.

        Args:
            data: Datos (ruta a csv/parquet/xlsx o lista de registros).
            columns: Columnas numéricas a usar (autodetecta si es ``None``).
            method: 'isolation_forest', 'zscore' o 'iqr'.
            contamination: Proporción esperada de anomalías (isolation_forest).
            integrate_as: Nombre de tabla para integrar el resultado (opcional).
            integrate_format: 'dax' o 'm' para la integración.
            dry_run: Si es ``True``, previsualiza la integración sin escribir.

        Returns:
            Resultado del análisis y, si aplica, la integración.
        """
        from powerbi_mcp.ai.anomaly import detect_anomalies as _detect

        result = _detect(data, columns=columns, method=method, contamination=contamination)
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def run_clustering(
        data: Any,
        columns: list[str] | None = None,
        algorithm: str = "kmeans",
        n_clusters: int | None = None,
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Agrupa filas en clústeres y, opcionalmente, integra el resultado.

        Args:
            data: Datos (ruta o registros).
            columns: Columnas numéricas a usar (autodetecta si es ``None``).
            algorithm: 'kmeans' o 'hierarchical'.
            n_clusters: Número de clústeres (auto si es ``None``).
            integrate_as: Nombre de tabla para integrar (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Resultado del clustering y, si aplica, la integración.
        """
        from powerbi_mcp.ai.clustering import run_clustering as _cluster

        result = _cluster(data, columns=columns, algorithm=algorithm, n_clusters=n_clusters)
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def forecast_series(
        data: Any,
        date_column: str,
        value_column: str,
        periods: int = 12,
        seasonal_periods: int | None = None,
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Pronostica una serie temporal y, opcionalmente, integra el resultado.

        Args:
            data: Datos (ruta o registros).
            date_column: Columna de fecha.
            value_column: Columna numérica a pronosticar.
            periods: Número de periodos futuros.
            seasonal_periods: Longitud del ciclo estacional (auto si es ``None``).
            integrate_as: Nombre de tabla para integrar (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Histórico + pronóstico y, si aplica, la integración.
        """
        from powerbi_mcp.ai.forecasting import forecast_series as _forecast

        result = _forecast(
            data, date_column=date_column, value_column=value_column,
            periods=periods, seasonal_periods=seasonal_periods,
        )
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def rfm_segmentation(
        data: Any,
        customer_column: str,
        date_column: str,
        amount_column: str,
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Segmenta clientes por RFM y, opcionalmente, integra el resultado.

        Args:
            data: Detalle de transacciones (ruta o registros).
            customer_column: Columna identificadora del cliente.
            date_column: Columna de fecha de la transacción.
            amount_column: Columna del importe.
            integrate_as: Nombre de tabla para integrar (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Segmentación RFM por cliente y, si aplica, la integración.
        """
        from powerbi_mcp.ai.rfm import rfm_segmentation as _rfm

        result = _rfm(
            data, customer_column=customer_column, date_column=date_column,
            amount_column=amount_column,
        )
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def correlation_analysis(
        data: Any,
        columns: list[str] | None = None,
        method: str = "pearson",
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Analiza correlaciones entre variables numéricas.

        Args:
            data: Datos (ruta o registros).
            columns: Columnas numéricas (autodetecta si es ``None``).
            method: 'pearson', 'spearman' o 'kendall'.
            integrate_as: Nombre de tabla para integrar la matriz (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Matriz de correlación y pares fuertes; si aplica, la integración.
        """
        from powerbi_mcp.ai.correlation import correlation_analysis as _corr

        result = _corr(data, columns=columns, method=method)
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def decision_tree_explain(
        data: Any,
        target_column: str,
        feature_columns: list[str] | None = None,
        max_depth: int = 4,
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Entrena un árbol de decisión explicativo (key influencers).

        Args:
            data: Datos (ruta o registros).
            target_column: Columna objetivo a explicar.
            feature_columns: Variables explicativas (todas las demás si es ``None``).
            max_depth: Profundidad máxima del árbol (interpretabilidad).
            integrate_as: Nombre de tabla para integrar la importancia (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Importancia de variables y reglas; si aplica, la integración.
        """
        from powerbi_mcp.ai.decision_tree import decision_tree_explain as _tree

        result = _tree(data, target_column=target_column, feature_columns=feature_columns, max_depth=max_depth)
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def train_regression(
        data: Any,
        target_column: str,
        feature_columns: list[str] | None = None,
        algorithm: str = "linear",
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Entrena un modelo de regresión y reporta métricas e importancia.

        Args:
            data: Datos (ruta o registros).
            target_column: Variable numérica objetivo.
            feature_columns: Variables predictoras (todas las demás si es ``None``).
            algorithm: 'linear' o 'random_forest'.
            integrate_as: Nombre de tabla para integrar la importancia (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Métricas (R², MAE, RMSE) e importancia; si aplica, la integración.
        """
        from powerbi_mcp.ai.regression import train_regression as _reg

        result = _reg(data, target_column=target_column, feature_columns=feature_columns, algorithm=algorithm)
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)

    @mcp.tool()
    @_tool
    def train_classification(
        data: Any,
        target_column: str,
        feature_columns: list[str] | None = None,
        algorithm: str = "random_forest",
        integrate_as: str | None = None,
        integrate_format: str = "dax",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Entrena un clasificador y reporta métricas, importancia y confusión.

        Args:
            data: Datos (ruta o registros).
            target_column: Variable categórica objetivo.
            feature_columns: Variables predictoras (todas las demás si es ``None``).
            algorithm: 'logistic' o 'random_forest'.
            integrate_as: Nombre de tabla para integrar la importancia (opcional).
            integrate_format: 'dax' o 'm'.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Métricas, matriz de confusión e importancia; si aplica, la integración.
        """
        from powerbi_mcp.ai.classification import train_classification as _clf

        result = _clf(data, target_column=target_column, feature_columns=feature_columns, algorithm=algorithm)
        return _maybe_integrate(result, integrate_as, integrate_format, dry_run)
