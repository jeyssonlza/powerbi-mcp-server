"""Modelos de Inteligencia Artificial aplicados al dataset Power BI.

Cada submódulo implementa una familia de modelos y devuelve resultados listos
para integrarse al modelo semántico (como tabla calculada DAX o consulta M):

- :mod:`~powerbi_mcp.ai.anomaly`        Detección de anomalías.
- :mod:`~powerbi_mcp.ai.clustering`     Clustering (k-means, jerárquico).
- :mod:`~powerbi_mcp.ai.forecasting`    Forecasting / series de tiempo.
- :mod:`~powerbi_mcp.ai.rfm`            Segmentación RFM.
- :mod:`~powerbi_mcp.ai.correlation`    Análisis de correlaciones.
- :mod:`~powerbi_mcp.ai.decision_tree`  Árbol de decisión explicativo.
- :mod:`~powerbi_mcp.ai.regression`     Regresión.
- :mod:`~powerbi_mcp.ai.classification` Clasificación.
- :mod:`~powerbi_mcp.ai.integration`    Integración de resultados al modelo.
"""

from __future__ import annotations

__all__: list[str] = []
