# Publicacion En GitHub

Esta guia resume los pasos recomendados para publicar Power BI MCP Server como
repositorio utilizable por otras personas.

## Estado Publicable

El proyecto incluye:

- `README.md` con descripcion, instalacion, uso, arquitectura y pruebas.
- `LICENSE` con licencia MIT.
- `.gitignore` para excluir secretos, entornos virtuales, caches, logs,
  respaldos y binarios Power BI pesados.
- `.env.example` como plantilla segura de configuracion.
- `SECURITY.md` con politica de reporte de vulnerabilidades.
- `CONTRIBUTING.md` con guia para colaboradores.
- `.github/workflows/ci.yml` para ejecutar pruebas en GitHub Actions.
- `docs/REPORTE_AUDITORIA.md` con revision tecnica interna aprobada.

## Archivos Que No Deben Subirse

Si usas Git correctamente, `.gitignore` los excluye. Si subes archivos desde la
web de GitHub, revisalos manualmente.

- `.env`
- `.venv/`
- `.pytest_cache/`
- `.coverage`
- `htmlcov/`
- `logs/`
- `backups/`
- `.pbip_backups/`
- `src/*.egg-info/`
- Archivos `.pbix`, `.pbit` o `.abf` privados.
- Credenciales, certificados, tokens o secretos reales.

## Publicacion Recomendada

Desde PowerShell:

```powershell
git init
git add .
git status
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/jeyssonzerpa/powerbi-mcp-server.git
git push -u origin main
```

Antes del commit, confirma que `git status` no incluya archivos sensibles o
generados.

## Verificacion Local Antes De Subir

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests\smoke_e2e.py
```

Resultado esperado de la revision interna inicial:

- `pip check`: sin dependencias rotas.
- `pytest`: 27 pruebas aprobadas.
- `smoke_e2e`: todas las pruebas de humo aprobadas.

## Despues De Publicar

Revisa en GitHub:

- Que la pestana `Actions` ejecute el workflow `CI`.
- Que el badge de CI del `README.md` aparezca correctamente.
- Que `.env`, `.venv`, `.coverage`, `.pytest_cache` y `src/*.egg-info` no esten
  en el repositorio.
- Que `SECURITY.md` y `CONTRIBUTING.md` aparezcan en la pagina principal del
  proyecto.

## Nota De Confianza

El reporte de auditoria indica una aprobacion tecnica interna para entrega
inicial. Esta aprobacion ayuda a documentar controles, pruebas y alcance, pero
no sustituye auditorias externas, certificaciones regulatorias ni revisiones
legales.
