# Changelog

Todos los cambios notables del servidor Power BI MCP se documentan en este
archivo.

El formato sigue la idea de Keep a Changelog y el proyecto usa versionado
semantico.

## [0.1.0] - 2026-06-06

### Incluido

- Servidor MCP `powerbi-mcp` con transporte `stdio`.
- Empaquetado Python con `pyproject.toml`, `src layout` y entrada
  `powerbi-mcp`.
- Configuracion por variables de entorno con prefijo `PBIMCP_` y soporte de
  archivo `.env`.
- Instalador Windows `install.ps1`.
- Configuraciones listas para clientes MCP en `clients/`.

### Proyecto PBIP/PBIX

- Apertura y resumen de proyectos PBIP.
- Lectura de estructura del proyecto.
- Carga de modelos semanticos TMSL y lectura basica TMDL.
- Lectura de reportes PBIR.
- Lectura de metadatos PBIX.
- Conversion PBIP a PBIX mediante `pbi-tools` cuando esta disponible.

### Modelo Semantico

- Listado y descripcion de tablas.
- Gestion de tablas de datos y tablas calculadas.
- Gestion de columnas de datos y columnas calculadas.
- Gestion de medidas DAX.
- Validacion DAX sintactica, semantica ligera y de buenas practicas.
- Gestion y diagnostico de relaciones.
- Clasificacion de esquema estrella, copo de nieve o indeterminado.

### Inteligencia Artificial

- Deteccion de anomalias.
- Clustering.
- Forecasting.
- Segmentacion RFM.
- Analisis de correlacion.
- Arbol de decision explicativo.
- Regresion.
- Clasificacion.
- Integracion de resultados al modelo como DAX o Power Query M.

### Visuales Y Reportes

- Creacion de paginas PBIR.
- Creacion de visuales nativos PBIR.
- Creacion de dashboards.
- Exportacion de visuales HTML interactivos.
- Generacion de temas Power BI.
- Sincronizacion automatica de la sesion despues de escrituras de reporte.

### Analisis Y Documentacion

- Analisis de calidad de datos.
- Perfilado de datasets.
- Analisis estatico de rendimiento.
- Analizador de buenas practicas.
- Generacion de documentacion tecnica Markdown/HTML.
- Diccionario de datos Markdown/JSON/CSV.
- Changelog automatico por proyecto Power BI.

### Seguridad Y Auditoria

- Backups automaticos antes de escrituras.
- Restauracion de backups de archivos y carpetas.
- Backups cifrados opcionales con Fernet.
- Extraccion segura de ZIP/PBIX con validacion de rutas internas.
- Modo `dry_run` sin persistencia ni residuos en la sesion activa.
- Enmascaramiento de PII.
- Claves subrogadas deterministas.
- Cifrado y descifrado de valores con Fernet.
- Auditoria de operaciones relevantes en JSON Lines.
- Reporte formal de auditoria tecnica interna aprobada.

### Pruebas

- Pruebas unitarias de DAX y operaciones de modelo.
- Pruebas de backup, restauracion y cifrado.
- Pruebas contra ZIP/PBIX con rutas inseguras.
- Pruebas de estado de sesion para `dry_run` y paginas PBIR.
- Smoke test end-to-end sobre un proyecto PBIP temporal.

### Estado De Revision

- `pytest`: 27 pruebas aprobadas.
- Cobertura total: 34%.
- `smoke_e2e`: aprobado.
- `pip check`: sin dependencias rotas.
- Auditoria tecnica interna: aprobada.
