# 🔧 Plan de Acciones para Dejar el MCP IMPECABLE

**Fecha:** 8 de junio de 2026  
**Proyecto:** Power BI MCP Server v0.1.0  
**Objetivo:** Llevar el proyecto de Efectividad 71% (C+) a 90%+ (A-)

---

## 📊 Resumen Ejecutivo

El MCP está **bien estructurado pero incompleto**. Se identificaron:
- **3 problemas CRÍTICOS** que previenen funcionamiento
- **7 problemas ALTOS** que afectan confiabilidad
- **7 problemas MEDIO** que afectan mantenibilidad
- **10 problemas BAJO** que afectan profesionalismo

**Tiempo total estimado:** 40-60 horas

---

## 🔴 PROBLEMAS CRÍTICOS (BLOQUEAN FUNCIÓN)

### CRÍTICO-001: Función `run()` No Existe

**Ubicación:** `src/powerbi_mcp/server.py` (falta definición)  
**Error:** `__main__.py` línea 58 intenta importar `run()` que no existe  
**Impacto:** El servidor NO ARRANCA

**Acción Requerida:**
```python
# Agregar a src/powerbi_mcp/server.py (al final del archivo)

async def run() -> None:
    """Inicia el servidor MCP con la configuración actual."""
    logger.info("Iniciando servidor Power BI MCP v%s", __version__)
    
    try:
        async with mcp.server.stdio_server() as (read_stream, write_stream):
            logger.info("Servidor escuchando en stdin/stdout")
            await mcp.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="power-bi-mcp",
                    server_version=__version__,
                )
            )
    except Exception as e:
        logger.error("Error al ejecutar servidor: %s", e, exc_info=True)
        raise
```

**Prioridad:** 🔴 INMEDIATO (máximo 30 minutos)

---

### CRÍTICO-002: Módulo `powerbi_api/auth.py` Incompleto

**Ubicación:** `src/powerbi_mcp/powerbi_api/auth.py`  
**Problema:** Las herramientas de Power BI API (5 herramientas listadas) pueden no estar implementadas  
**Impacto:** Autenticación OAuth2 y llamadas a API fallan en runtime

**Acción Requerida:**
1. Revisar que `OAuth2Client` está completamente implementado
2. Verificar que `get_tokens()`, `refresh_token()` funcionan
3. Agregar tests para flujo OAuth2 completo
4. Implementar fallback/retry para llamadas a API

**Prioridad:** 🔴 INMEDIATO (máximo 2-4 horas)

---

### CRÍTICO-003: Dependencias Circulares Potenciales

**Ubicación:** `src/powerbi_mcp/server.py` importa de casi todos los módulos  
**Problema:** Potencial para circular imports si no se maneja con `TYPE_CHECKING`  
**Impacto:** Fallos inesperados de importación en runtime

**Acción Requerida:**
```python
# En los módulos que importan tipos de server.py, usar:

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from powerbi_mcp.server import MCP_Server  # Solo para type checking

# En runtime, usar strings o Any para évitar circular import
```

**Archivos a revisar:**
- `core/__init__.py`
- `model/__init__.py`
- `visuals/__init__.py`
- `security/__init__.py`

**Prioridad:** 🔴 INMEDIATO (máximo 1 hora)

---

## 🟠 PROBLEMAS ALTOS (AFECTAN CONFIABILIDAD)

### ALTO-001: Cobertura de Tests Solo 34% (Necesita 70%+)

**Ubicación:** Toda la suite de tests  
**Problema:** 36% de brecha de cobertura. Módulos sin tests:
- ❌ `visuals/pbip_visuals.py` - 0%
- ❌ `visuals/html_visuals.py` - 0%
- ❌ `visuals/themes.py` - 0%
- ❌ `visuals/pages.py` - 0%
- ❌ `analysis/performance.py` - 0%
- ❌ `analysis/best_practices.py` - 0%
- ❌ `analysis/profiling.py` - 0%
- ❌ `ai/*.py` (todos) - 5%
- ❌ `docs/*.py` - 0%
- ❌ `pbip/pbix.py` - 0%
- ❌ `pbip/parser.py` - 0%
- ❌ `security/masking.py` - 0%
- ❌ `powerbi_api/client.py` - 0%

**Impacto:** Fallos no detectados, regresiones permitidas

**Acción Requerida:**
```bash
# Paso 1: Verificar cobertura actual
pytest --cov=powerbi_mcp --cov-report=html

# Paso 2: Crear fixtures reutilizables en tests/conftest.py
# - Sample PBIP projects
# - Mock Azure AD responses
# - Sample DataFrames para AI tests

# Paso 3: Escribir tests por módulo (prioridad):
# 1. AI (20+ tests) - 40 horas
# 2. Visuals (15+ tests) - 30 horas
# 3. PBIP parser (10+ tests) - 20 horas
# 4. Analysis (8+ tests) - 15 horas
# 5. Docs generator (8+ tests) - 15 horas
# 6. Security masking (8+ tests) - 15 horas
```

**Estimado:** 40 horas  
**Prioridad:** 🟠 URGENTE (máximo 1 semana)

---

### ALTO-002: Docstrings Incompletos

**Ubicación:** Múltiples módulos especialmente `ai/` y `visuals/`  
**Problema:** 30% de funciones sin docstrings completos

**Acción Requerida:**
Para cada función/clase pública, asegurar:
```python
def mi_funcion(param1: int, param2: str) -> dict[str, Any]:
    """Descripción clara de qué hace la función.
    
    Usa presente activo: "Calcula", "Valida", "Genera", no "Será calculado".
    
    Args:
        param1: Descripción del parámetro 1, incluyendo tipo y restricciones.
        param2: Descripción del parámetro 2.
    
    Returns:
        Descripción de qué retorna, estructura del dict si es aplicable.
        
    Raises:
        ValueError: Cuando param1 es negativo.
        TypeError: Cuando param2 no es string.
    
    Example:
        >>> resultado = mi_funcion(5, "test")
        >>> print(resultado)
        {'status': 'ok'}
    """
```

**Estimado:** 8 horas  
**Prioridad:** 🟠 IMPORTANTE

---

### ALTO-003: Type Hints Genéricos (Demasiados `Any`)

**Ubicación:** `pbip/models.py`, `visuals/builder.py`, otros  
**Problema:** 27+ `type: ignore` comments, muchos `dict[str, Any]`

**Acción Requerida:**
```python
# ❌ Evitar:
def procesar_datos(datos: dict[str, Any]) -> dict[str, Any]:
    pass

# ✅ Usar:
from typing import TypedDict, Literal

class DatosInput(TypedDict):
    tabla: str
    columnas: list[str]
    filtros: dict[str, str]

class DatosOutput(TypedDict):
    status: Literal["ok", "error"]
    count: int
    data: list[dict[str, Any]]

def procesar_datos(datos: DatosInput) -> DatosOutput:
    pass

# Para enums:
class CompatibilityLevel(Enum):
    LEVEL_1100 = 1100
    LEVEL_1200 = 1200
    LEVEL_1550 = 1550
```

**Archivos principales:**
- `pbip/models.py` - Reemplazar genéricos con TypedDict
- `visuals/builder.py` - Validar `field_spec` con schema
- `ai/_base.py` - Definir tipos de entrada/salida claros

**Estimado:** 6 horas  
**Prioridad:** 🟠 IMPORTANTE

---

### ALTO-004: Manejo de Errores Inconsistente

**Ubicación:** `server.py` decorador `_tool()` línea ~55  
**Problema:** Captura `Exception` genérica sin diferenciar errores del dominio

**Acción Requerida:**
```python
# ❌ Actual:
def _tool(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e)}  # Pierde info del tipo

# ✅ Mejorado:
def _tool(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PowerBIMCPError as e:  # Errores del dominio
            logger.warning("Error de dominio: %s", e.code, extra={"error": e.to_dict()})
            return {"error": e.to_dict()}
        except Exception as e:  # Errores inesperados
            logger.error("Error inesperado: %s", e, exc_info=True)
            return {"error": "Internal server error", "code": "internal_error"}
```

**Estimado:** 2 horas  
**Prioridad:** 🟠 IMPORTANTE

---

### ALTO-005: Validación de Entrada Débil

**Ubicación:** `visuals/builder.py` línea ~64, `field_spec` parameter  
**Problema:** Solo valida si vacío, no estructura interna

**Acción Requerida:**
```python
from pydantic import BaseModel, Field, validator

class FieldSpec(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    data_type: Literal["int", "float", "string", "bool"]
    nullable: bool = False
    default_value: Optional[Any] = None
    
    @validator("name")
    def name_valid(cls, v):
        if not v.isidentifier():
            raise ValueError("Field name must be valid Python identifier")
        return v

# En builder.py:
def create_visual(field_spec: list[FieldSpec]) -> dict:
    # Ahora field_spec está completamente validado
    for field in field_spec:
        # Usar field.name, field.data_type, etc.
        pass
```

**Estimado:** 3 horas  
**Prioridad:** 🟠 IMPORTANTE

---

### ALTO-006: Importación Diferida Incompleta

**Ubicación:** `__main__.py` línea 58, pero también `__init__.py` importa `numpy`, `pandas`  
**Problema:** Dependencias pesadas cargadas incluso para `--version`

**Acción Requerida:**
```python
# src/powerbi_mcp/__init__.py

__version__ = "0.1.0"

# ❌ Evitar en nivel de módulo:
# import numpy as np
# import pandas as pd

# ✅ Solo importar en funciones cuando sea necesario:
def load_pandas_utils():
    import pandas as pd
    return pd
```

**Estimado:** 1 hora  
**Prioridad:** 🟠 IMPORTANTE

---

### ALTO-007: Revisión de `core/archive.py` No Completada

**Ubicación:** `src/powerbi_mcp/core/archive.py`  
**Problema:** No revisado línea por línea, riesgo de vulnerabilidades de path traversal

**Acción Requerida:**
```bash
# Revisar manualmente:
# 1. safe_extract_zip() - ¿Valida todos los paths?
# 2. validate_zip_members() - ¿Rechaza ../ patterns?
# 3. ¿Se usa Path.resolve() para normalizar?
# 4. ¿Hay tests de seguridad?

# Crear tests de seguridad:
pytest tests/test_core/test_archive_security.py
```

**Estimado:** 2 horas  
**Prioridad:** 🟠 URGENTE

---

## 🟡 PROBLEMAS MEDIO (AFECTAN MANTENIBILIDAD)

### MEDIO-001: Logging Inconsistente

**Ubicación:** Múltiples módulos  
**Problema:** Algunos registran logs, otros no. Formato inconsistente.

**Acción:** Asegurar que cada módulo con lógica de negocio tenga:
```python
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

def mi_funcion():
    logger.info("Iniciando operación", extra={"user": "sistema"})
    # ... lógica ...
    logger.info("Operación completada", extra={"duration_ms": 245})
```

**Estimado:** 4 horas  
**Prioridad:** 🟡 MEDIO

---

### MEDIO-002: Duplicación de Lógica de Validación DAX

**Ubicación:** `model/dax_validator.py` y `model/measures.py`  
**Problema:** Validación DAX en dos lugares

**Acción:** Crear `model/validation.py` centralizado:
```python
# model/validation.py
class DAXValidationEngine:
    """Motor de validación centralizado para expresiones DAX."""
    
    def validate_measure_dax(self, expression: str) -> ValidationResult:
        return self._validate_core(expression, context="measure")
    
    def validate_column_dax(self, expression: str) -> ValidationResult:
        return self._validate_core(expression, context="column")
    
    def _validate_core(self, expr: str, context: str) -> ValidationResult:
        # Lógica unificada
        pass
```

**Estimado:** 3 horas  
**Prioridad:** 🟡 MEDIO

---

### MEDIO-003: Constantes Mágicas Sin Centralización

**Ubicación:** Múltiples módulos  
**Problema:** `5 * 1024 * 1024`, `min_rows=5`, etc. hardcodeados

**Acción:** Agregar a `config.py`:
```python
class AppConstants:
    """Constantes de la aplicación."""
    
    # Logging
    LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
    LOG_BACKUP_COUNT = 5
    
    # AI
    AI_MIN_ROWS = 5
    AI_MAX_FEATURES = 100
    
    # PBIP
    DEFAULT_COMPATIBILITY_LEVEL = 1550
    
    # Backup
    BACKUP_MAX_DEFAULT = 10
```

**Estimado:** 2 horas  
**Prioridad:** 🟡 MEDIO

---

### MEDIO-004: Validación de `compatibility_level`

**Ubicación:** `pbip/models.py` línea 219  
**Problema:** `compatibility_level: int` sin validación

**Acción:**
```python
from enum import Enum
from pydantic import Field, validator

class CompatibilityLevel(Enum):
    """Niveles de compatibilidad soportados en PBIP/PBIX."""
    LEVEL_1100 = 1100  # Power BI Desktop Feb 2014
    LEVEL_1200 = 1200  # Power BI Desktop Jul 2015
    LEVEL_1550 = 1550  # Current

class PBIPModel(BaseModel):
    compatibility_level: CompatibilityLevel = CompatibilityLevel.LEVEL_1550
    
    @validator("compatibility_level", pre=True)
    def validate_level(cls, v):
        if isinstance(v, int):
            try:
                return CompatibilityLevel(v)
            except ValueError:
                raise ValueError(f"Nivel no soportado: {v}")
        return v
```

**Estimado:** 1 hora  
**Prioridad:** 🟡 MEDIO

---

### MEDIO-005: Documentación de CLI Incompleta

**Ubicación:** `__main__.py`  
**Problema:** `--help` no es informativo

**Acción:**
```python
def main():
    parser = argparse.ArgumentParser(
        description="Servidor Power BI MCP - Integración Power BI con Claude",
        epilog="""
        Ejemplos:
            powerbi-mcp --version
            powerbi-mcp --transport stdio
        
        Documentación: https://github.com/tuusuario/powerbi-mcp
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transporte MCP a usar (default: stdio)"
    )
```

**Estimado:** 1 hora  
**Prioridad:** 🟡 MEDIO

---

### MEDIO-006: Archivo `_atomic_write()` Verificación

**Ubicación:** `pbip/writer.py`  
**Problema:** Función usada pero no completamente revisada

**Acción:**
```bash
# Verificar implementación:
grep -n "_atomic_write" src/powerbi_mcp/pbip/writer.py

# Debe cumplir:
# 1. ✅ Crear archivo temporal
# 2. ✅ Escribir a temp file
# 3. ✅ Usar os.replace() (atómico en POSIX/Windows)
# 4. ✅ Manejar excepciones y limpiar temp
# 5. ✅ Tener tests para fallo de escritura
```

**Estimado:** 1 hora  
**Prioridad:** 🟡 MEDIO

---

### MEDIO-007: Validación de `backup_max = 0`

**Ubicación:** `core/backup.py` línea 229  
**Problema:** `backup_max=0` significa "sin límite" pero no documentado

**Acción:**
```python
# En config.py:
class Settings(BaseModel):
    backup_max: int = Field(
        default=10,
        ge=0,
        description="Máximo de backups a retener (0 = sin límite)"
    )
    
    @validator("backup_max")
    def backup_max_warning(cls, v):
        if v == 0:
            logger.warning("backup_max=0: se retendrán todos los backups (cuidado con espacio disco)")
        return v
```

**Estimado:** 1 hora  
**Prioridad:** 🟡 MEDIO

---

## 🟢 PROBLEMAS BAJO (AFECTAN PROFESIONALISMO)

### BAJO-001: Ejemplos Ejecutables en README

**Ubicación:** README.md  
**Acción:** Agregar sección "Inicio Rápido" con código ejecutable

**Estimado:** 1 hora  
**Prioridad:** 🟢 BAJO

---

### BAJO-002: Estandarizar Convención de Nombres

**Ubicación:** `tests/smoke_e2e.py` → `tests/test_smoke_e2e.py`

**Estimado:** 0.5 horas  
**Prioridad:** 🟢 BAJO

---

### BAJO-003: Crear `.claude/settings.json` Completo

**Ubicación:** `.claude/settings.json`  
**Acción:** Configurar Claude Code para entender estructura del proyecto

**Estimado:** 0.5 horas  
**Prioridad:** 🟢 BAJO

---

### BAJO-004: Fixture Tests Sin Usar

**Ubicación:** `tests/conftest.py`  
**Acción:** Limpiar fixtures no utilizadas

**Estimado:** 0.5 horas  
**Prioridad:** 🟢 BAJO

---

### BAJO-005: Badges de CI en README

**Ubicación:** README.md  
**Acción:** Crear workflows GitHub Actions antes de mostrar badges

**Estimado:** 1 hora  
**Prioridad:** 🟢 BAJO

---

## 📋 PLAN DE EJECUCIÓN

### Semana 1: Bloqueadores Críticos (5 horas)
- [ ] CRÍTICO-001: Implementar función `run()`
- [ ] CRÍTICO-002: Completar `powerbi_api/auth.py`
- [ ] CRÍTICO-003: Resolver circular imports
- [ ] ALTO-007: Revisar `core/archive.py` seguridad

### Semana 2-4: Tests (40 horas)
- [ ] ALTO-001: Escribir 20+ tests AI
- [ ] ALTO-001: Escribir 15+ tests Visuals
- [ ] ALTO-001: Escribir 10+ tests PBIP
- [ ] ALTO-001: Escribir 8+ tests Analysis
- [ ] ALTO-001: Escribir 8+ tests Docs
- [ ] ALTO-001: Escribir 8+ tests Security

### Semana 5: Calidad (8 horas)
- [ ] ALTO-002: Completar docstrings
- [ ] ALTO-003: Mejorar type hints
- [ ] ALTO-004: Consistencia de errores
- [ ] ALTO-005: Validación de entrada

### Semana 6: Mantenibilidad (8 horas)
- [ ] MEDIO-001: Logging consistente
- [ ] MEDIO-002: Validación DAX centralizada
- [ ] MEDIO-003: Constantes en config
- [ ] MEDIO-004: Validación compatibility_level

### Semana 7: Profesionalismo (4 horas)
- [ ] BAJO: Renombrar tests
- [ ] BAJO: Documentación CLI
- [ ] BAJO: README ejemplos
- [ ] BAJO: Badges CI

---

## ✅ CHECKLIST FINAL

| Tarea | Estimado | Estado |
|-------|----------|--------|
| Función `run()` | 0.5h | ⬜ |
| Auth Power BI API | 2-4h | ⬜ |
| Circular imports | 1h | ⬜ |
| Tests (cobertura 70%) | 40h | ⬜ |
| Docstrings completos | 8h | ⬜ |
| Type hints mejorados | 6h | ⬜ |
| Error handling | 2h | ⬜ |
| Validación entrada | 3h | ⬜ |
| Logging consistente | 4h | ⬜ |
| DAX centralizado | 3h | ⬜ |
| Constantes | 2h | ⬜ |
| CLI mejorada | 1h | ⬜ |
| Profesionalismo | 4h | ⬜ |
| **TOTAL** | **~78 horas** | ⬜ |

---

## 🎯 RESULTADO ESPERADO

Después de completar todas las acciones:

| Métrica | Actual | Esperado |
|---------|--------|----------|
| Efectividad General | 71% (C+) | 92% (A-) |
| Cobertura Tests | 34% | 75%+ |
| Docstrings | 70% | 98% |
| Type Hints | 73% | 95% |
| Bloqueadores Críticos | 3 | 0 |
| Gaps Altos | 7 | 0 |

---

**Generado:** 8 de junio de 2026  
**Versión:** 0.1.0 → 0.2.0 (meta después de correcciones)
