# Roadmap

Este documento describe el camino planificado para llevar Power BI MCP Server
desde la entrega inicial (v0.1.0, ~82/100 en operatividad interna) hacia una
herramienta madura y lista para adopción amplia.

## Estado Actual (v0.1.0)

| Métrica | Valor |
|---------|-------|
| Versión | 0.1.0 (Beta) |
| Pruebas unitarias | 27 |
| Cobertura | ~34% |
| Smoke test E2E | 35 comprobaciones OK |
| Auditoría interna | Aprobada |

## Fase 1 — Calidad Base (82 → 90)

Objetivo: establecer estándares de calidad que el CI aplique automáticamente.

- [x] Integrar `ruff` y `mypy` en GitHub Actions
- [x] Corregir errores de lint y tipado críticos
- [ ] Documentar política de versiones semánticas en releases
- [ ] Publicar primer release `v0.1.0` en GitHub

**Contribuciones bienvenidas:** issues con etiqueta `good first issue`.

## Fase 2 — Cobertura De Pruebas (90 → 95)

Objetivo: subir la cobertura de 34% a 60%+ con tests unitarios focalizados.

- [ ] Tests para `powerbi_api/auth.py` y `powerbi_api/client.py`
- [ ] Tests para `security/masking.py` y `security/surrogate_keys.py`
- [ ] Tests para `visuals/html_visuals.py` y `visuals/pbip_visuals.py`
- [ ] Tests para `docs/generator.py` y `docs/data_dictionary.py`
- [ ] Tests de regresión para módulos `ai/` (no solo smoke E2E)
- [ ] Meta de cobertura mínima en CI (p. ej. 50%)

## Fase 3 — Arquitectura Y Mantenibilidad (95 → 98)

Objetivo: facilitar contribuciones y reducir complejidad.

- [ ] Dividir `server.py` en módulos por dominio (`server/model_tools.py`, etc.)
- [ ] Añadir type stubs o mejoras de tipado en módulos PBIP
- [ ] Documentación de API interna para contribuidores
- [ ] Ejemplos de proyectos PBIP de demostración en `examples/`

## Fase 4 — Producción Empresarial (98 → 100)

Objetivo: preparar el proyecto para entornos exigentes.

- [ ] Política de permisos por workspace/ruta
- [ ] Publicación en PyPI (`pip install powerbi-mcp-server`)
- [ ] Documentación en inglés (README + guías)
- [ ] Integración con Analysis Services para validación DAX profunda
- [ ] Revisión de seguridad externa (pentest o auditoría independiente)

## Cómo Contribuir Al Roadmap

1. Revisa los [issues abiertos](https://github.com/jeyssonzerpa/powerbi-mcp-server/issues).
2. Busca etiquetas `good first issue` o `help wanted`.
3. Comenta en el issue antes de empezar a trabajar.
4. Sigue la guía en [CONTRIBUTING.md](../CONTRIBUTING.md).

## Versiones Planificadas

| Versión | Enfoque |
|---------|---------|
| 0.1.x | Estabilización, CI, lint, documentación open source |
| 0.2.x | Cobertura de tests, Power BI API probada |
| 0.3.x | Refactor de servidor, PyPI |
| 1.0.0 | API estable, permisos, madurez empresarial |
