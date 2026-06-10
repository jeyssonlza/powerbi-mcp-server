# Copilot — instrucciones del proyecto Power BI

Hay **dos MCPs de Power BI** configurados en este proyecto. No compiten, se
complementan según el estado de Power BI Desktop:

- **`powerbi-modeling-mcp`** (Microsoft) → escribe el **modelo**: tablas,
  columnas, relaciones y medidas DAX. Requiere **Power BI Desktop ABIERTO**
  (modelo en vivo). Valida el DAX ejecutándolo y preserva `lineageTag`.
- **`powerbi`** (propio) → **IA** (forecast, anomalías, clustering, RFM),
  **calidad de datos, documentación, seguridad/PII y visuales HTML**. Trabaja
  con **Power BI Desktop CERRADO** (archivos PBIP en disco).

## Regla de oro

El MCP propio **NO** persiste tablas ni medidas en el modelo TMDL (su escritura
del modelo es frágil con metadata compleja). La escritura del modelo la hace
**Microsoft**; el propio **lee** el resultado para análisis y visuales.

## Decisión rápida

- ¿Crear/editar tabla, columna, relación o medida? → **Microsoft** (Desktop abierto)
- ¿IA, calidad, docs, seguridad, visuales? → **propio** (Desktop cerrado)
- ¿Transformar fuentes (ETL)? → Power Query en Power BI Desktop

El playbook completo con el orden de pasos por tarea está en `AGENTS.md`
(raíz del repositorio).
