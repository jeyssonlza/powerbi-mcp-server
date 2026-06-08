"""Módulos de herramientas MCP organizadas por dominio.

Este paquete contiene 67 herramientas Power BI MCP divididas en 8 dominios:
- project_tools: 11 herramientas de gestión de proyectos PBIP/PBIX
- model_tools: 23 herramientas del modelo semántico (tablas, columnas, medidas, relaciones)
- ai_tools: 8 herramientas de Machine Learning e IA
- visuals_tools: 7 herramientas de visuales y páginas
- analysis_tools: 5 herramientas de análisis de datos
- docs_tools: 3 herramientas de generación de documentación
- security_tools: 6 herramientas de seguridad y auditoría
- pbi_api_tools: 5 herramientas de integración con Power BI Service
"""

from __future__ import annotations

from powerbi_mcp.tools.ai_tools import register_ai_tools
from powerbi_mcp.tools.analysis_tools import register_analysis_tools
from powerbi_mcp.tools.docs_tools import register_docs_tools
from powerbi_mcp.tools.model_tools import register_model_tools
from powerbi_mcp.tools.pbi_api_tools import register_pbi_api_tools
from powerbi_mcp.tools.project_tools import register_project_tools
from powerbi_mcp.tools.security_tools import register_security_tools
from powerbi_mcp.tools.visuals_tools import register_visuals_tools

__all__ = [
    "register_project_tools",
    "register_model_tools",
    "register_ai_tools",
    "register_visuals_tools",
    "register_analysis_tools",
    "register_docs_tools",
    "register_security_tools",
    "register_pbi_api_tools",
]
