"""Power BI MCP Server.

Servidor MCP (Model Context Protocol) profesional para la gestión, modelado,
análisis, inteligencia artificial, visualización y documentación de proyectos
Power BI en formato PBIP/PBIX.

El paquete está organizado por dominios funcionales:

- :mod:`powerbi_mcp.core`        Infraestructura transversal (logging, errores,
                                 backup, configuración, validadores).
- :mod:`powerbi_mcp.pbip`        Lectura/escritura/parseo de proyectos PBIP/PBIX.
- :mod:`powerbi_mcp.model`       Modelado de datos (tablas, columnas, relaciones,
                                 medidas DAX).
- :mod:`powerbi_mcp.ai`          Modelos de IA aplicados al dataset.
- :mod:`powerbi_mcp.visuals`     Construcción de visuales (PBIP JSON y HTML).
- :mod:`powerbi_mcp.analysis`    Análisis de calidad, perfilado y rendimiento.
- :mod:`powerbi_mcp.docs`        Documentación técnica y diccionario de datos.
- :mod:`powerbi_mcp.security`    Encriptación, secretos, masking y auditoría.
- :mod:`powerbi_mcp.powerbi_api` Integración con Power BI Service (REST API).

El servidor en sí se define en :mod:`powerbi_mcp.server`.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Jeysson Zerpa"
__license__ = "MIT"

__all__ = ["__author__", "__license__", "__version__"]
