#!/bin/bash
# ===========================================================================
# run_tests.sh - Ejecutar suite de tests con cobertura
# ===========================================================================

set -e

echo ""
echo "============================================================================"
echo "Power BI MCP Server - Test Suite Runner"
echo "============================================================================"
echo ""

# Verificar si Python está disponible
if ! command -v python &> /dev/null; then
    echo "ERROR: Python no encontrado. Instala Python 3.10+ y asegúrate de que"
    echo "está en PATH."
    exit 1
fi

PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Usando Python: $PYTHON_VERSION"

echo "[1/4] Instalando dependencias de desarrollo..."
pip install -e ".[dev]" -q

echo "[2/4] Ejecutando tests con cobertura..."
pytest tests/ \
    --cov=powerbi_mcp \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    -v

TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
    echo ""
    echo "ERROR: Los tests fallaron con código: $TEST_EXIT"
    exit $TEST_EXIT
fi

echo ""
echo "============================================================================"
echo "Resultados de Tests"
echo "============================================================================"
echo ""

echo "[3/4] Generando reporte HTML de cobertura..."
if command -v xdg-open &> /dev/null; then
    xdg-open htmlcov/index.html
elif command -v open &> /dev/null; then
    open htmlcov/index.html
else
    echo "Abre htmlcov/index.html en tu navegador para ver el reporte detallado."
fi

echo ""
echo "[4/4] Resumen de cobertura por módulo:"
echo ""
python -m coverage report -m --fail-under=75 || echo "(Ejecuta: coverage report -m para más detalles)"

echo ""
echo "============================================================================"
echo "Suite de tests completada exitosamente."
echo "Ver htmlcov/index.html para reporte interactivo de cobertura."
echo "============================================================================"
echo ""

exit 0
