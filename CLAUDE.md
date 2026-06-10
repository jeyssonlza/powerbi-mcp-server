# Power BI MCP Server — instrucciones del proyecto

Este proyecto orquesta **dos MCPs de Power BI** como un equipo. El playbook
completo (división de responsabilidades, reglas de DAX y orden de pasos por
tarea) está en:

@AGENTS.md

## Regla rápida de orquestación

- **Power BI ABIERTO** (modelo vivo) → usa `powerbi-modeling-mcp` (Microsoft)
  para crear/editar **estructura y medidas**. Escribe con el motor Tabular real,
  preserva `lineageTag` y no rompe el proyecto.
- **Power BI CERRADO** (archivos PBIP) → usa `powerbi` (nuestro) para **IA**
  (forecast, anomalías, clustering, RFM), **calidad de datos, documentación,
  seguridad/PII y visuales**.

**Regla de oro:** el MCP propio **NO** persiste tablas ni medidas en proyectos
TMDL. La escritura del modelo la hace **Microsoft**; el propio **lee** el
resultado para análisis y visuales.
