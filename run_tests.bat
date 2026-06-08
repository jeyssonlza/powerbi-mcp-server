@echo off
REM ===========================================================================
REM run_tests.bat - Ejecutar suite de tests con cobertura
REM ===========================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo Power BI MCP Server - Test Suite Runner
echo ============================================================================
echo.

REM Verificar si Python está disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instala Python 3.10+ y asegúrate de que
    echo está en PATH.
    exit /b 1
)

echo [1/4] Instalando dependencias de desarrollo...
pip install -e ".[dev]" -q
if errorlevel 1 (
    echo ERROR: No se pudieron instalar las dependencias.
    exit /b 1
)

echo [2/4] Ejecutando tests con cobertura...
pytest tests/ ^
    --cov=powerbi_mcp ^
    --cov-report=html ^
    --cov-report=term-missing ^
    --cov-report=xml ^
    -v

set TEST_EXIT=%errorlevel%

if %TEST_EXIT% neq 0 (
    echo.
    echo ERROR: Los tests fallaron con código: %TEST_EXIT%
    exit /b %TEST_EXIT%
)

echo.
echo ============================================================================
echo Resultados de Tests
echo ============================================================================
echo.

REM Generar reporte de cobertura
python -c "^
import os, json, re
from pathlib import Path

coverage_file = Path('htmlcov/status.json')
if coverage_file.exists():
    with open(coverage_file) as f:
        data = json.load(f)
        print(f'Cobertura Total: {data.get(\"coverage\", \"N/A\")}%%')
else:
    # Intentar leer del reporte de término
    print('Ver htmlcov/index.html para reporte detallado de cobertura')
"

echo.
echo [3/4] Generando reporte HTML de cobertura...
echo Abriendo htmlcov/index.html...
if exist htmlcov\index.html (
    start htmlcov\index.html
) else (
    echo Reporte HTML no generado correctamente.
)

echo.
echo [4/4] Resumen de cobertura por módulo:
echo.
python -m coverage report -m --fail-under=75 2>nul || echo (Ejecuta: coverage report -m para más detalles)

echo.
echo ============================================================================
echo Suite de tests completada exitosamente.
echo Ver htmlcov/index.html para reporte interactivo de cobertura.
echo ============================================================================
echo.

exit /b 0
