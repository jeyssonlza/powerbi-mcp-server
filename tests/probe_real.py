"""Prueba de SOLO LECTURA contra un proyecto PBIP real.

No modifica ningún archivo del proyecto: solo lo abre y ejecuta operaciones de
exploración, análisis y documentación. Uso:

    python tests/probe_real.py "<ruta del proyecto PBIP>"
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


def main(project_path: str) -> int:
    # Aislar logs/backups del MCP fuera del proyecto del usuario.
    tmp = Path(tempfile.mkdtemp(prefix="pbimcp_probe_"))
    os.environ["PBIMCP_LOG_DIR"] = str(tmp / "logs")
    os.environ["PBIMCP_BACKUP_DIR"] = str(tmp / "backups")

    from powerbi_mcp.config import reload_settings

    reload_settings()
    from powerbi_mcp import server

    def show(title: str, data: object, limit: int = 0) -> None:
        print(f"\n{'=' * 70}\n {title}\n{'=' * 70}")
        text = json.dumps(data, indent=2, ensure_ascii=False)
        if limit and len(text) > limit:
            text = text[:limit] + "\n... (recortado)"
        print(text)

    # 1. Abrir
    r = server.open_project(project_path)
    show("1. open_project — resumen del proyecto", r)
    if not r.get("ok"):
        return 1

    # 2. Tablas
    r = server.list_tables()
    tables = r.get("tables", [])
    print(f"\n{'=' * 70}\n 2. list_tables — {len(tables)} tablas\n{'=' * 70}")
    for t in tables:
        flags = []
        if t["is_hidden"]:
            flags.append("oculta")
        if t["is_calculated"]:
            flags.append("calculada")
        suffix = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  - {t['name']}: {t['columns']} col, {t['measures']} medidas{suffix}")

    # 3. Medidas
    r = server.list_measures()
    measures = r.get("measures", [])
    print(f"\n{'=' * 70}\n 3. list_measures — {len(measures)} medidas (primeras 15)\n{'=' * 70}")
    for m in measures[:15]:
        print(f"  - [{m['table']}] {m['name']}")

    # 4. Relaciones
    r = server.list_relationships()
    rels = r.get("relationships", [])
    print(f"\n{'=' * 70}\n 4. list_relationships — {len(rels)} relaciones (primeras 15)\n{'=' * 70}")
    for rel in rels[:15]:
        print(f"  - {rel['from']} -> {rel['to']}  ({rel['cross_filter']}, activa={rel['is_active']})")

    # 5. Esquema
    show("5. classify_schema", server.classify_schema())

    # 6. Diagnóstico de relaciones
    show("6. diagnose_relationships", server.diagnose_relationships())

    # 7. Rendimiento
    r = server.analyze_performance()
    print(f"\n{'=' * 70}\n 7. analyze_performance — {r.get('total_findings')} hallazgos\n{'=' * 70}")
    print(f"  Por severidad: {r.get('by_severity')}")
    for f in r.get("findings", [])[:12]:
        print(f"  [{f['severity']}] {f['object']}: {f['message']}")

    # 8. Buenas prácticas
    r = server.run_best_practices()
    print(f"\n{'=' * 70}\n 8. run_best_practices — {r.get('total_violations')} violaciones\n{'=' * 70}")
    print(f"  Por severidad: {r.get('by_severity')}")
    print(f"  Por categoría: {r.get('by_category')}")
    for v in r.get("violations", [])[:10]:
        print(f"  [{v['severity']}] {v['object_name']}: {v['message']}")

    # 9. Documentación (a carpeta temporal, NO al proyecto del usuario)
    docs_dir = tmp / "docs"
    r = server.generate_documentation(output_dir=str(docs_dir))
    show("9. generate_documentation", r)

    print(f"\n{'=' * 70}")
    print(f" Artefactos generados (temporales) en: {tmp}")
    print(f"{'=' * 70}")
    print(" El proyecto del usuario NO fue modificado (solo lectura).")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tests/probe_real.py \"<ruta del proyecto PBIP>\"")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
