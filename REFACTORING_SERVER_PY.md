# 🔧 Plan de Refactorización: server.py (1849 líneas → Módulos)

**Estado Actual:** server.py monolítico con 67 herramientas  
**Objetivo:** Dividir en 8 módulos especializados  
**Beneficios:** Mejor mantenibilidad, escalabilidad, testabilidad

---

## 📋 ESTRUCTURA PROPUESTA

```
src/powerbi_mcp/
├── server.py                      (200 líneas: setup, imports, run())
└── tools/
    ├── __init__.py                (Exports all tools)
    ├── project_tools.py           (11 tools: project_*)
    ├── model_tools.py             (23 tools: table_*, column_*, measure_*, relationship_*)
    ├── ai_tools.py                (8 tools: ai_*)
    ├── visuals_tools.py           (7 tools: visual_*)
    ├── analysis_tools.py          (4 tools: analysis_*)
    ├── docs_tools.py              (3 tools: docs_*)
    ├── security_tools.py          (6 tools: security_*)
    └── pbi_api_tools.py           (5 tools: pbi_*)
```

---

## 🔀 MIGRACIÓN PASO A PASO

### Paso 1: Crear módulos base (ya hecho)
```bash
mkdir -p src/powerbi_mcp/tools/
```

### Paso 2: Crear archivos de tools
```python
# src/powerbi_mcp/tools/project_tools.py
from powerbi_mcp.server import mcp, _tool

@mcp.tool()
@_tool
def project_info() -> dict[str, Any]:
    # ... contenido actual de project_info del server.py
    pass

# ... más tools de project
```

### Paso 3: Actualizar server.py
```python
# src/powerbi_mcp/server.py
from powerbi_mcp.tools import (
    project_tools,
    model_tools,
    ai_tools,
    visuals_tools,
    analysis_tools,
    docs_tools,
    security_tools,
    pbi_api_tools,
)

# Solo mcp y run() aquí
```

### Paso 4: Crear __init__.py en tools/
```python
# src/powerbi_mcp/tools/__init__.py
from . import (
    project_tools,
    model_tools,
    ai_tools,
    visuals_tools,
    analysis_tools,
    docs_tools,
    security_tools,
    pbi_api_tools,
)

__all__ = [
    "project_tools",
    "model_tools",
    # ...
]
```

---

## 📊 DESGLOSE DE HERRAMIENTAS

### project_tools.py (11 tools)
```python
def project_info()
def project_structure(max_depth: int = 4)
def project_create(project_name: str, location: str)
def project_read(project_path: str)
def project_update_metadata(project_id: str, metadata: dict)
def project_list()
def project_export_pbix(project_id: str, output_path: str)
def project_import_pbip(pbip_path: str)
def project_backup(project_id: str)
def project_restore_backup(project_id: str, backup_id: str)
def project_delete(project_id: str)
```

### model_tools.py (23 tools)
```python
# Table operations
def table_create(project_id: str, table_name: str, columns: list)
def table_list(project_id: str)
# ... 9 more

# Column operations
def column_create(project_id: str, table_name: str, column_spec: dict)
# ... 4 more

# Measure operations
def measure_create(project_id: str, table_name: str, measure_name: str, dax_expr: str)
# ... 3 more

# Relationship operations
def relationship_create(...)
# ... 2 more
```

### ai_tools.py (8 tools)
```python
def ai_detect_anomalies(df: pd.DataFrame, method: str = "isolation_forest")
def ai_clustering_kmeans(df: pd.DataFrame, n_clusters: int = 3)
def ai_clustering_hierarchical(df: pd.DataFrame, method: str = "ward")
def ai_forecasting_arima(series: list, order: tuple = (1, 1, 1))
def ai_forecasting_exponential(series: list, alpha: float = 0.3)
def ai_segmentation_rfm(df: pd.DataFrame, recency_col: str, frequency_col: str, monetary_col: str)
def ai_correlation_pearson(df: pd.DataFrame)
def ai_correlation_spearman(df: pd.DataFrame)
```

### visuals_tools.py (7 tools)
```python
def visual_create_page(project_id: str, page_name: str)
def visual_add_chart(project_id: str, page_id: str, chart_spec: dict)
def visual_add_table(project_id: str, page_id: str, table_spec: dict)
def visual_add_matrix(project_id: str, page_id: str, matrix_spec: dict)
def visual_apply_theme(project_id: str, page_id: str, theme_name: str)
def visual_export_html(project_id: str, page_id: str, output_path: str)
def visual_generate_report(project_id: str, output_path: str)
```

### analysis_tools.py (4 tools)
```python
def analysis_data_quality(df: pd.DataFrame)
def analysis_profile_data(df: pd.DataFrame)
def analysis_detect_patterns(df: pd.DataFrame)
def analysis_performance_metrics(model_id: str)
```

### docs_tools.py (3 tools)
```python
def docs_generate_markdown(project_id: str, output_path: str)
def docs_generate_html(project_id: str, output_path: str)
def docs_generate_data_dictionary(project_id: str, output_path: str)
```

### security_tools.py (6 tools)
```python
def security_mask_pii(data: dict, fields: list)
def security_hash_column(df: pd.DataFrame, column: str)
def security_encrypt_file(input_path: str, output_path: str)
def security_decrypt_file(input_path: str, output_path: str)
def security_audit_log_read(limit: int = 100)
def security_backup_project(project_id: str, encrypt: bool = True)
```

### pbi_api_tools.py (5 tools)
```python
def pbi_list_workspaces()
def pbi_list_datasets(workspace_id: str | None = None)
def pbi_list_reports(workspace_id: str | None = None)
def pbi_execute_dax(dataset_id: str, dax_query: str, workspace_id: str | None = None)
def pbi_refresh_dataset(dataset_id: str, workspace_id: str | None = None)
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear estructura de carpetas `src/powerbi_mcp/tools/`
- [ ] Crear 8 archivos de tools (project, model, ai, visuals, analysis, docs, security, pbi_api)
- [ ] Mover funciones desde server.py a módulos correspondientes
- [ ] Crear __init__.py en tools/
- [ ] Actualizar server.py para importar desde tools/
- [ ] Ejecutar tests para validar funcionamiento
- [ ] Actualizar imports en tests si es necesario
- [ ] Documentar en README el nuevo estructura

---

## 📈 BENEFICIOS

✅ **Mantenibilidad:** Cada módulo tiene responsabilidad única  
✅ **Testabilidad:** Tests específicos por dominio  
✅ **Escalabilidad:** Fácil agregar nuevas tools  
✅ **Reusabilidad:** Importar solo lo que necesitas  
✅ **Performance:** Carga modular en lugar de monolítica  

---

## ⏱️ TIEMPO ESTIMADO

- Crear estructura: 30 min
- Mover código: 2 horas
- Refactorizar imports: 1 hora
- Testing: 1 hora
- **TOTAL: 4.5 horas**

---

**Estado:** 📋 PLAN LISTO - PUEDE IMPLEMENTARSE EN PRÓXIMA ITERACIÓN
