# Guia De Uso

Esta guia explica como usar Power BI MCP Server desde un cliente compatible con
Model Context Protocol. El servidor expone herramientas para trabajar con
proyectos Power BI PBIP/PBIX, modelos semanticos, visuales, analisis,
documentacion, seguridad y Power BI Service.

## Flujo General

1. Instala el paquete.
2. Configura el cliente MCP.
3. Abre un proyecto PBIP.
4. Ejecuta consultas, diagnosticos o cambios mediante lenguaje natural.
5. Revisa resultados, backups, changelog y auditoria.

Ejemplo:

```text
Abre el proyecto PBIP en C:\PowerBI\Ventas y dime que tablas, medidas,
relaciones, paginas y visuales contiene.
```

## Trabajo Con Proyectos

Herramientas principales:

| Necesidad | Herramienta |
|---|---|
| Abrir proyecto PBIP | `open_project` |
| Ver resumen del proyecto | `project_info` |
| Ver arbol de archivos | `project_structure` |
| Recargar desde disco | `reload_project` |
| Cerrar proyecto | `close_project` |
| Crear backup manual | `create_backup` |
| Listar backups | `list_backups` |
| Restaurar backup | `restore_backup` |
| Convertir PBIP a PBIX | `convert_to_pbix` |
| Leer metadatos PBIX | `read_pbix_info` |

Ejemplos:

```text
Abre el proyecto PBIP en C:\PowerBI\Finanzas.
```

```text
Muestrame la estructura del proyecto con profundidad 4.
```

```text
Crea un backup manual antes de modificar el modelo.
```

```text
Restaura el backup model.bim__20260606_201045_017695.
```

## Modelado Semantico

Herramientas principales:

`list_tables`, `describe_table`, `list_measures`, `list_relationships`,
`search_objects`, `add_table`, `add_calculated_table`, `rename_table`,
`delete_table`, `add_data_column`, `add_calculated_column`, `update_column`,
`delete_column`, `add_measure`, `update_measure`, `delete_measure`,
`validate_dax`, `add_relationship`, `update_relationship`,
`delete_relationship`, `diagnose_relationships`, `classify_schema`.

Ejemplos:

```text
Lista las tablas del modelo y dime cuales parecen tablas de hechos y dimensiones.
```

```text
Describe la tabla Ventas con columnas, medidas y tipos de datos.
```

```text
Valida esta medida:
Total Ventas = SUM(Ventas[Importe])
```

```text
Crea la medida Ventas Promedio en la tabla Ventas con la expresion
AVERAGE(Ventas[Importe]) y formato #,0.00.
```

```text
Crea una relacion entre Ventas[ProductoID] y Producto[ProductoID].
```

```text
Diagnostica las relaciones y dime si hay ambiguedades o tablas aisladas.
```

## Visuales Y Reportes

Herramientas principales:

`list_pages`, `create_page`, `create_visual`, `create_dashboard`,
`export_html_visual`, `list_color_palettes`, `create_theme`.

Ejemplos:

```text
Crea una pagina llamada Resumen Ejecutivo.
```

```text
Agrega a la pagina Resumen Ejecutivo un grafico de columnas con
Producto[Nombre] como categoria y SUM(Ventas[Importe]) como valor.
```

```text
Crea un dashboard llamado Ventas con una tarjeta del total, una linea por mes
y un treemap por categoria.
```

```text
Exporta ventas.csv como grafico HTML de lineas usando Fecha en X e Importe en Y.
```

## Analisis De Calidad Y Buenas Practicas

Herramientas principales:

`analyze_data_quality`, `profile_data`, `analyze_performance`,
`run_best_practices`, `optimize_dax`.

Ejemplos:

```text
Analiza la calidad de ventas.csv e identifica nulos, duplicados y outliers.
```

```text
Perfila clientes.xlsx y resume cardinalidad, tipos y valores frecuentes.
```

```text
Ejecuta el analizador de buenas practicas sobre el modelo actual.
```

```text
Optimiza esta expresion DAX y dime que riesgos tiene:
Ventas Ratio = [Ventas] / [Clientes]
```

## Inteligencia Artificial

Herramientas principales:

`detect_anomalies`, `run_clustering`, `forecast_series`, `rfm_segmentation`,
`correlation_analysis`, `decision_tree_explain`, `train_regression`,
`train_classification`.

Los datos pueden enviarse como registros, `DataFrame` o rutas a archivos
`.csv`, `.parquet` y `.xlsx`.

Ejemplos:

```text
Detecta anomalias en ventas.csv usando la columna Importe e integra el resultado
como tabla calculada DAX llamada AnomaliasVentas.
```

```text
Haz un forecast de 6 meses usando Fecha como columna temporal e Importe como
valor.
```

```text
Segmenta clientes por RFM usando ClienteID, Fecha e Importe.
```

```text
Entrena una regresion para predecir Importe usando Mes, Region y Categoria.
```

## Documentacion

Herramientas principales:

`generate_documentation`, `generate_data_dictionary`, `get_changelog`.

Ejemplos:

```text
Genera la documentacion tecnica completa del proyecto en Markdown y HTML.
```

```text
Crea el diccionario de datos en CSV.
```

```text
Muestrame el changelog del proyecto.
```

La documentacion generada puede utilizarse para revisiones tecnicas, traspaso de
conocimiento, auditorias internas y gobierno de datos.

## Seguridad Y Auditoria

Herramientas principales:

`mask_data`, `generate_surrogate_keys`, `encrypt_value`, `decrypt_value`,
`generate_encryption_key`, `get_audit_log`.

Ejemplos:

```text
Enmascara las columnas con datos personales de clientes.csv.
```

```text
Genera claves subrogadas deterministas para la columna Email.
```

```text
Genera una clave de cifrado Fernet para configurar PBIMCP_SECRET_KEY.
```

```text
Muestrame las ultimas 50 entradas del log de auditoria.
```

Variables importantes:

| Variable | Proposito |
|---|---|
| `PBIMCP_SECRET_KEY` | Clave Fernet para cifrado. |
| `PBIMCP_BACKUP_ENCRYPT` | Activa cifrado de backups si vale `true`. |
| `PBIMCP_SURROGATE_SALT` | Salt para claves subrogadas deterministas. |
| `PBIMCP_BACKUP_DIR` | Carpeta de backups. |
| `PBIMCP_LOG_DIR` | Carpeta de logs y auditoria. |

## Power BI Service

Herramientas principales:

`pbi_list_workspaces`, `pbi_list_datasets`, `pbi_list_reports`,
`pbi_execute_dax`, `pbi_refresh_dataset`.

Requiere configurar Azure AD:

```env
PBIMCP_AZURE_TENANT_ID=
PBIMCP_AZURE_CLIENT_ID=
PBIMCP_AZURE_CLIENT_SECRET=
```

Ejemplos:

```text
Lista mis workspaces de Power BI.
```

```text
Lista los datasets del workspace 00000000-0000-0000-0000-000000000000.
```

```text
Ejecuta esta consulta DAX contra el dataset X:
EVALUATE TOPN(10, Ventas)
```

```text
Solicita refresco del dataset X.
```

## Uso Seguro Recomendado

- Trabaja con PBIP bajo control de versiones.
- Mantén `.env` fuera del repositorio.
- Usa `dry_run` antes de cambios complejos.
- Revisa `list_backups` antes de restaurar.
- Activa `PBIMCP_BACKUP_ENCRYPT=true` si los proyectos contienen informacion
  sensible.
- Consulta `get_audit_log` para validar trazabilidad.
- Ejecuta `python -m pytest -q` tras cambios de codigo.

## Reporte De Auditoria

El proyecto incluye un reporte formal de revision tecnica interna en
[REPORTE_AUDITORIA.md](REPORTE_AUDITORIA.md). Este documento resume alcance,
controles revisados, evidencias, riesgos residuales y estado de aprobacion.
