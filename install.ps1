# ===========================================================================
# Power BI MCP Server - Instalador automatizado (Windows / PowerShell)
# ---------------------------------------------------------------------------
# Crea el entorno virtual, instala las dependencias y verifica el servidor.
# Uso:   .\install.ps1            (instalación de producción)
#        .\install.ps1 -Dev       (incluye herramientas de desarrollo)
# ===========================================================================
[CmdletBinding()]
param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Write-Host "==> Power BI MCP Server - Instalación" -ForegroundColor Cyan
Write-Host "    Directorio: $projectRoot"

# 1. Verificar Python
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
    throw "No se encontró 'python' en el PATH. Instala Python 3.10+ y reintenta."
}
$version = & python --version
Write-Host "    $version"

# 2. Crear entorno virtual si no existe
if (-not (Test-Path $venvPython)) {
    Write-Host "==> Creando entorno virtual (.venv)..." -ForegroundColor Cyan
    & python -m venv (Join-Path $projectRoot ".venv")
} else {
    Write-Host "==> Entorno virtual ya existe; se reutiliza." -ForegroundColor Yellow
}

# 3. Actualizar pip
Write-Host "==> Actualizando pip..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip --quiet

# 4. Instalar dependencias
if ($Dev) {
    Write-Host "==> Instalando dependencias (con extras de desarrollo)..." -ForegroundColor Cyan
    & $venvPython -m pip install -e ".[dev]"
} else {
    Write-Host "==> Instalando dependencias de producción..." -ForegroundColor Cyan
    & $venvPython -m pip install -e .
}

# 5. Crear .env si no existe
$envFile = Join-Path $projectRoot ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $projectRoot ".env.example") $envFile
    Write-Host "==> Archivo .env creado a partir de .env.example" -ForegroundColor Green
}

# 6. Verificar el servidor
Write-Host "==> Verificando el servidor..." -ForegroundColor Cyan
$ver = & $venvPython -m powerbi_mcp --version
Write-Host "    $ver" -ForegroundColor Green

Write-Host ""
Write-Host "Instalación completada." -ForegroundColor Green
Write-Host "Intérprete del servidor:" -ForegroundColor Green
Write-Host "  $venvPython"
Write-Host ""
Write-Host "Configura tu cliente MCP con los archivos de la carpeta 'clients\'." -ForegroundColor Cyan
