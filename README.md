# Power BI MCP Server

Servidor MCP profesional para leer, analizar, documentar y modificar proyectos
Power BI en formato PBIP/PBIX mediante lenguaje natural desde clientes
compatibles con Model Context Protocol.

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-compatible-7e56c2.svg)](https://modelcontextprotocol.io/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Commercial License](https://img.shields.io/badge/Commercial_License-Available-orange.svg)](COMMERCIAL_LICENSE.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/jeyssonlza/powerbi-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/jeyssonlza/powerbi-mcp-server/actions/workflows/ci.yml)

## Estado Del Proyecto

Power BI MCP Server nace como una herramienta modular para equipos que trabajan
con modelos semanticos, reportes, visuales, documentacion y automatizacion de
Power BI. El proyecto incluye desde su primera entrega:

- Servidor MCP por transporte `stdio`.
- Lectura y escritura segura de proyectos PBIP.
- Exploracion y modificacion del modelo semantico.
- Creacion de paginas, visuales y dashboards PBIR.
- Analisis de calidad, rendimiento y buenas practicas.
- Integracion de modelos de IA al modelo Power BI.
- Documentacion tecnica, diccionario de datos y changelog por proyecto.
- Backups automaticos, restauracion, auditoria y cifrado Fernet opcional.
- Integracion con Power BI Service mediante REST API.

La revision tecnica interna del proyecto fue ejecutada y aprobada. El reporte
formal esta disponible en [docs/REPORTE_AUDITORIA.md](docs/REPORTE_AUDITORIA.md).

## Tabla De Contenidos

- [Que Es](#que-es)
- [Para Que Sirve](#para-que-sirve)
- [Caracteristicas](#caracteristicas)
- [Arquitectura](#arquitectura)
- [Instalacion](#instalacion)
- [Configuracion](#configuracion)
- [Uso Rapido](#uso-rapido)
- [Herramientas MCP](#herramientas-mcp)
- [Seguridad Y Auditoria](#seguridad-y-auditoria)
- [Calidad Y Pruebas](#calidad-y-pruebas)
- [Desarrollo](#desarrollo)
- [Publicacion En GitHub](#publicacion-en-github)
- [Licencia](#licencia)

## Que Es

Power BI MCP Server es un servidor Model Context Protocol que permite a
asistentes de IA interactuar con proyectos Power BI usando herramientas
controladas. En lugar de editar manualmente multiples archivos JSON/TMDL/PBIR,
el usuario puede pedir acciones en lenguaje natural y el cliente MCP invoca las
herramientas correspondientes del servidor.

El servidor esta orientado principalmente a PBIP, porque este formato es mas
adecuado para control de versiones, auditoria, revision tecnica y automatizacion
que un archivo PBIX binario.

## Para Que Sirve

Sirve para acelerar y estandarizar tareas comunes en proyectos Power BI:

- Abrir proyectos PBIP y entender su estructura.
- Listar tablas, columnas, medidas y relaciones.
- Crear, actualizar o eliminar medidas DAX.
- Crear tablas, columnas y relaciones del modelo semantico.
- Validar expresiones DAX y sugerir buenas practicas.
- Crear paginas y visuales PBIR.
- Generar visuales HTML interactivos.
- Ejecutar analisis de calidad de datos, perfilado y rendimiento.
- Aplicar modelos de IA como anomalias, clustering, forecasting, RFM,
  regresion, clasificacion, correlacion y arboles de decision.
- Integrar resultados de IA como tablas calculadas DAX o consultas Power Query.
- Generar documentacion tecnica y diccionarios de datos.
- Crear backups automaticos y restaurarlos.
- Consultar logs de auditoria.
- Conectarse a Power BI Service para listar workspaces, datasets, reportes,
  ejecutar DAX y solicitar refrescos.

## Caracteristicas

### Gestion De Proyectos PBIP/PBIX

- Apertura de proyectos desde carpeta raiz o archivo `.pbip`.
- Deteccion automatica de modelo semantico y reporte.
- Lectura de modelos TMSL (`model.bim`) y TMDL basico.
- Lectura de reportes PBIR.
- Conversion PBIP a PBIX mediante `pbi-tools` cuando esta disponible.
- Lectura de metadatos basicos de PBIX existentes.

### Modelado Semantico

- Operaciones sobre tablas, columnas, medidas y relaciones.
- Validacion de nombres y expresiones DAX.
- Diagnostico de relaciones rotas, ambiguas, bidireccionales o aisladas.
- Clasificacion de esquema estrella, copo de nieve o indeterminado.
- Persistencia segura con backup previo y escritura atomica.

### Inteligencia Artificial

- Deteccion de anomalias.
- Clustering.
- Forecasting de series temporales.
- Segmentacion RFM.
- Matriz de correlaciones.
- Arbol de decision explicativo.
- Regresion.
- Clasificacion.
- Integracion de resultados al modelo como DAX o Power Query M.

### Visuales Y Reportes

- Creacion de paginas PBIR.
- Creacion de visuales nativos PBIR.
- Creacion de dashboards con layout automatico.
- Exportacion de visuales HTML interactivos con Plotly.
- Generacion de temas Power BI.
- Sincronizacion automatica de la sesion tras escribir paginas o visuales.

### Analisis Y Documentacion

- Analisis de calidad de datos.
- Perfilado de datasets.
- Analisis de rendimiento estatico.
- Analizador de buenas practicas.
- Documentacion tecnica en Markdown y HTML.
- Diccionario de datos en Markdown, JSON o CSV.
- Changelog automatico por proyecto Power BI.

### Seguridad

- Backups automaticos antes de escrituras.
- Restauracion de backups de archivos y carpetas.
- Backups cifrados opcionales con Fernet (`PBIMCP_BACKUP_ENCRYPT=true`).
- Validacion segura de archivos ZIP antes de extraer.
- Modo `dry_run` sin cambios persistentes ni residuos en memoria.
- Enmascaramiento de PII.
- Claves subrogadas deterministas con HMAC y salt.
- Auditoria de operaciones relevantes.
- Secretos por variables de entorno o `.env`.

## Arquitectura

```text
src/powerbi_mcp/
|-- __init__.py
|-- __main__.py
|-- server.py
|-- session.py
|-- config.py
|
|-- core/
|   |-- archive.py
|   |-- backup.py
|   |-- exceptions.py
|   |-- logger.py
|   `-- validators.py
|
|-- pbip/
|   |-- models.py
|   |-- reader.py
|   |-- writer.py
|   |-- parser.py
|   `-- pbix.py
|
|-- model/
|   |-- tables.py
|   |-- columns.py
|   |-- relationships.py
|   |-- measures.py
|   `-- dax_validator.py
|
|-- ai/
|   |-- anomaly.py
|   |-- clustering.py
|   |-- forecasting.py
|   |-- rfm.py
|   |-- correlation.py
|   |-- decision_tree.py
|   |-- regression.py
|   |-- classification.py
|   `-- integration.py
|
|-- visuals/
|   |-- builder.py
|   |-- pbip_visuals.py
|   |-- html_visuals.py
|   |-- themes.py
|   `-- pages.py
|
|-- analysis/
|   |-- data_quality.py
|   |-- profiling.py
|   |-- performance.py
|   `-- best_practices.py
|
|-- docs/
|   |-- generator.py
|   |-- data_dictionary.py
|   `-- changelog.py
|
|-- security/
|   |-- encryption.py
|   |-- surrogate_keys.py
|   |-- masking.py
|   `-- audit.py
|
`-- powerbi_api/
    |-- auth.py
    `-- client.py
```

## Instalacion

### Requisitos

- Python 3.10 o superior.
- `pip` actualizado.
- Power BI Desktop o `pbi-tools` solo si se requiere conversion PBIP a PBIX.

### Instalacion Automatizada En Windows

```powershell
.\install.ps1
.\install.ps1 -Dev
```

El instalador crea `.venv`, instala dependencias, genera `.env` desde
`.env.example` si no existe y verifica el servidor.

### Instalacion Manual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Para desarrollo:

```powershell
pip install -e ".[dev]"
```

Verificacion:

```powershell
python -m powerbi_mcp --version
```

## Configuracion

La configuracion se carga desde variables de entorno o archivo `.env`, con
prefijo `PBIMCP_`.

Variables principales:

| Variable | Uso |
|---|---|
| `PBIMCP_LOG_LEVEL` | Nivel de log (`INFO`, `DEBUG`, `WARNING`, etc.). |
| `PBIMCP_LOG_DIR` | Carpeta de logs. |
| `PBIMCP_BACKUP_ENABLED` | Activa o desactiva backups automaticos. |
| `PBIMCP_BACKUP_DIR` | Carpeta de backups. |
| `PBIMCP_BACKUP_MAX` | Maximo de backups por origen. |
| `PBIMCP_BACKUP_ENCRYPT` | Cifra backups con Fernet si vale `true`. |
| `PBIMCP_SECRET_KEY` | Clave Fernet para cifrado. |
| `PBIMCP_SURROGATE_SALT` | Salt para claves subrogadas deterministas. |
| `PBIMCP_AZURE_TENANT_ID` | Tenant de Azure AD. |
| `PBIMCP_AZURE_CLIENT_ID` | Client ID de la app registrada. |
| `PBIMCP_AZURE_CLIENT_SECRET` | Client Secret para service principal. |

Los archivos de configuracion para clientes MCP estan en [clients/](clients/).

## Uso Rapido

Ejemplos de peticiones desde un cliente MCP:

```text
Abre el proyecto PBIP en C:\PowerBI\Ventas y lista las tablas.
```

```text
Valida esta medida DAX y dime si cumple buenas practicas:
CALCULATE([Total Ventas], SAMEPERIODLASTYEAR(Fecha[Date]))
```

```text
Crea una pagina llamada Resumen Ejecutivo y agrega un grafico de columnas
por Producto[Nombre] con la suma de Ventas[Importe].
```

```text
Detecta anomalias en ventas.csv sobre la columna Importe e integra el resultado
como tabla calculada DAX llamada AnomaliasVentas.
```

```text
Genera la documentacion tecnica y el diccionario de datos del proyecto.
```

## Herramientas MCP

| Dominio | Herramientas |
|---|---|
| Proyecto | `open_project`, `project_info`, `project_structure`, `reload_project`, `close_project`, `create_backup`, `list_backups`, `restore_backup`, `convert_to_pbix`, `read_pbix_info` |
| Modelo | `list_tables`, `describe_table`, `list_measures`, `list_relationships`, `search_objects`, `add_table`, `add_calculated_table`, `rename_table`, `delete_table`, `add_data_column`, `add_calculated_column`, `update_column`, `delete_column`, `add_measure`, `update_measure`, `delete_measure`, `validate_dax`, `add_relationship`, `update_relationship`, `delete_relationship`, `diagnose_relationships`, `classify_schema` |
| IA | `detect_anomalies`, `run_clustering`, `forecast_series`, `rfm_segmentation`, `correlation_analysis`, `decision_tree_explain`, `train_regression`, `train_classification` |
| Visuales | `list_pages`, `create_page`, `create_visual`, `create_dashboard`, `export_html_visual`, `list_color_palettes`, `create_theme` |
| Analisis | `analyze_data_quality`, `profile_data`, `analyze_performance`, `run_best_practices`, `optimize_dax` |
| Documentacion | `generate_documentation`, `generate_data_dictionary`, `get_changelog` |
| Seguridad | `mask_data`, `generate_surrogate_keys`, `encrypt_value`, `decrypt_value`, `generate_encryption_key`, `get_audit_log` |
| Power BI Service | `pbi_list_workspaces`, `pbi_list_datasets`, `pbi_list_reports`, `pbi_execute_dax`, `pbi_refresh_dataset` |

## Seguridad Y Auditoria

El proyecto fue disenado con controles de seguridad desde su version inicial:

- Toda escritura relevante usa backup automatico previo.
- La restauracion valida el backup y admite archivos o carpetas.
- La extraccion ZIP/PBIX valida rutas internas antes de escribir.
- Las escrituras usan operacion atomica cuando aplica.
- El modo `dry_run` genera previsualizacion sin persistir ni dejar cambios en la
  sesion activa.
- La auditoria registra operaciones de modelo, proyecto, visuales,
  documentacion, backups, restore y llamadas Power BI API.
- Los secretos se cargan desde entorno o `.env`.
- `.env`, backups, logs y binarios Power BI estan excluidos por `.gitignore`.

Para ver el estado formal de revision, consulta
[docs/REPORTE_AUDITORIA.md](docs/REPORTE_AUDITORIA.md).

## Calidad Y Pruebas

La entrega inicial incluye pruebas unitarias y de comportamiento para las zonas
mas sensibles del servidor:

- Validacion DAX.
- Operaciones de modelo.
- Backup y restore.
- Backup cifrado.
- Rechazo de ZIP/PBIX con rutas inseguras.
- Estado de sesion con `dry_run`.
- Sincronizacion de paginas creadas.
- Smoke test end-to-end sobre un PBIP temporal.

Comandos de verificacion:

```powershell
python -m pytest -q
python tests\smoke_e2e.py
python -m pip check
```

Resultado de referencia verificado (ejecución real con `pytest`):

- `pytest`: **351 pruebas aprobadas**, 0 fallos.
- Cobertura total real: **54%** (medida con `pytest --cov`, no estimada).
- Dominios cubiertos: proyecto/sesión, modelo y DAX, IA/ML (anomalías,
  clustering, forecasting, correlación, regresión, clasificación, árbol de
  decisión, RFM), visuales HTML, calidad de datos, masking PII, cifrado,
  Power BI REST API (mockeada) y autenticación OAuth2.
- `pip check`: sin dependencias rotas.

> Nota de transparencia: versiones previas de este README reportaban cifras de
> cobertura no verificadas. Las cifras anteriores se sustituyeron por resultados
> reales obtenidos ejecutando la suite completa.

## Desarrollo

```powershell
pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest -q
```

El proyecto usa `src layout`, `pyproject.toml`, modelos Pydantic, tipado con
`py.typed`, excepciones de dominio y separacion por paquetes funcionales.

## Publicacion En GitHub

El repositorio incluye los archivos base para publicacion abierta:

- Licencia MIT.
- `.gitignore` para excluir `.env`, `.venv`, caches, backups, logs y binarios
  Power BI pesados.
- Workflow de CI en `.github/workflows/ci.yml`.
- Politica de seguridad en `SECURITY.md`.
- Guia de contribucion en `CONTRIBUTING.md`.
- Guia de publicacion en [docs/PUBLICACION_GITHUB.md](docs/PUBLICACION_GITHUB.md).

Antes de publicar, revisa que no se suban secretos reales ni proyectos PBIX
privados. Si se publica manualmente desde la web de GitHub, no incluyas
`.venv`, `.pytest_cache`, `.coverage`, `logs`, `backups`, `.pbip_backups` ni
`src/*.egg-info`.

## Licencia

Este proyecto usa un modelo de **Dual License**:

| Uso | Licencia |
|-----|----------|
| Personal, educativo, open source (AGPL compatible) | ✅ **Gratis** — [AGPL v3](LICENSE) |
| Comercial, SaaS, producto privado, enterprise | 💰 **Commercial License** — [Ver términos](COMMERCIAL_LICENSE.md) |

### AGPL v3 — Uso libre
Si usas este software en un proyecto open source compatible con AGPL,
es completamente gratuito. Ver [LICENSE](LICENSE).

### Commercial License — Uso empresarial
Si integras este software en productos privados, SaaS o herramientas
enterprise sin publicar tu código fuente, necesitas una licencia comercial.

📧 **Contacto:** jeyssonzerpa@gmail.com
📄 **Términos completos:** [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md)

---

## Built With

This project was designed and developed by **Jeysson Zerpa** using a
multi-agent, multi-IDE workflow across several AI-assisted environments:

| Tool | Role |
|------|------|
| **Claude (Anthropic)** | Architecture design, code generation, auditing, refactoring, DevOps |
| **Cursor** | AI-assisted development and code completion |
| **VS Code** | Primary code editor and workspace management |
| **OpenCode** | AI terminal coding assistant |
| **Antigravity** | AI development support |

> All code, design decisions, and project direction were driven by
> **Jeysson Zerpa**. AI tools were used as coding assistants under
> his supervision and review.

---

## Disclaimer

> **Power BI MCP Server is an independent open-source project and is NOT affiliated with,
> endorsed by, or sponsored by Microsoft Corporation.**
>
> "Power BI" is a registered trademark of Microsoft Corporation. This project uses the
> name solely to describe interoperability with Microsoft Power BI products.
>
> Use of the Power BI REST API is subject to
> [Microsoft's Terms of Service](https://learn.microsoft.com/en-us/rest/api/power-bi/).
> This tool does not redistribute any Microsoft software or proprietary code.
