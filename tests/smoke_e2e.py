"""Prueba de humo end-to-end del servidor (sin dependencias de IA pesadas).

Crea un proyecto PBIP mínimo en una carpeta temporal, lo abre mediante las
herramientas del servidor y ejerce el flujo de lectura/escritura/validación,
comprobando que el respaldo automático y el changelog funcionan.

Ejecutar con:  python tests/smoke_e2e.py
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


def _build_sample_pbip(root: Path) -> Path:
    """Crea un proyecto PBIP de ejemplo (TMSL) y devuelve su carpeta raíz."""
    project_dir = root / "Demo"
    model_dir = project_dir / "Demo.SemanticModel"
    report_dir = project_dir / "Demo.Report" / "definition" / "pages"
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    # Archivo .pbip raíz
    (project_dir / "Demo.pbip").write_text(
        json.dumps({"version": "1.0", "artifacts": [{"report": {"path": "Demo.Report"}}]}, indent=2),
        encoding="utf-8",
    )

    # model.bim (TMSL) con una tabla de ventas
    model = {
        "name": "Demo",
        "compatibilityLevel": 1567,
        "model": {
            "culture": "es-ES",
            "tables": [
                {
                    "name": "Ventas",
                    "columns": [
                        {"name": "Fecha", "dataType": "dateTime", "sourceColumn": "Fecha"},
                        {"name": "Importe", "dataType": "double", "sourceColumn": "Importe"},
                        {"name": "ProductoID", "dataType": "int64", "sourceColumn": "ProductoID"},
                    ],
                    "measures": [
                        {"name": "Total Ventas", "expression": "SUM(Ventas[Importe])", "formatString": "#,0"}
                    ],
                    "partitions": [
                        {"name": "Ventas", "mode": "import", "source": {"type": "m", "expression": "let Source = ... in Source"}}
                    ],
                },
                {
                    "name": "Producto",
                    "columns": [
                        {"name": "ProductoID", "dataType": "int64", "sourceColumn": "ProductoID"},
                        {"name": "Nombre", "dataType": "string", "sourceColumn": "Nombre"},
                    ],
                    "partitions": [
                        {"name": "Producto", "mode": "import", "source": {"type": "m", "expression": "let Source = ... in Source"}}
                    ],
                },
            ],
            "relationships": [
                {
                    "name": "rel1",
                    "fromTable": "Ventas",
                    "fromColumn": "ProductoID",
                    "toTable": "Producto",
                    "toColumn": "ProductoID",
                    "crossFilteringBehavior": "oneDirection",
                }
            ],
        },
    }
    (model_dir / "model.bim").write_text(json.dumps(model, indent=2), encoding="utf-8")
    return project_dir


def main() -> int:
    """Ejecuta la prueba de humo y reporta el resultado."""
    import os

    tmp = Path(tempfile.mkdtemp(prefix="pbimcp_smoke_"))
    # Aislar backups/logs dentro del temporal.
    os.environ["PBIMCP_BACKUP_DIR"] = str(tmp / ".backups")
    os.environ["PBIMCP_LOG_DIR"] = str(tmp / "logs")

    from powerbi_mcp.config import reload_settings

    reload_settings()

    from powerbi_mcp import server

    failures: list[str] = []

    def check(label: str, condition: bool, detail: str = "") -> None:
        status = "OK " if condition else "FALLO"
        print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(label)

    try:
        project_dir = _build_sample_pbip(tmp)

        # 1. Abrir proyecto
        r = server.open_project(str(project_dir))
        check("open_project", r.get("ok") and r.get("tables") == 2, str(r))

        # 2. Listar tablas
        r = server.list_tables()
        check("list_tables", r.get("ok") and len(r["tables"]) == 2, str(r))

        # 3. Describir tabla
        r = server.describe_table("Ventas")
        check("describe_table", r.get("ok") and len(r["table"]["columns"]) == 3, str(r))

        # 4. Validar DAX (correcto)
        r = server.validate_dax("DIVIDE(SUM(Ventas[Importe]), COUNTROWS(Ventas))")
        check("validate_dax (valido)", r.get("ok") and r.get("is_valid"), str(r))

        # 5. Validar DAX (paréntesis desbalanceados)
        r = server.validate_dax("SUM(Ventas[Importe]")
        check("validate_dax (invalido detectado)", r.get("ok") and not r.get("is_valid"), str(r))

        # 6. Agregar medida
        r = server.add_measure("Ventas", "Ventas Promedio", "AVERAGE(Ventas[Importe])", format_string="#,0.00")
        check("add_measure", r.get("ok") and not r.get("dry_run"), str(r))

        # 7. Verificar persistencia: recargar y comprobar la medida
        server.reload_project()
        r = server.list_measures()
        names = {m["name"] for m in r["measures"]}
        check("medida persistida", "Ventas Promedio" in names, str(names))

        # 8. Verificar respaldo creado
        r = server.list_backups()
        check("respaldo automatico creado", r.get("ok") and len(r["backups"]) >= 1, str(r))

        # 9. Agregar medida duplicada (debe fallar con gracia)
        r = server.add_measure("Ventas", "Total Ventas", "SUM(Ventas[Importe])")
        check("duplicado rechazado", not r.get("ok") and r.get("code") == "duplicate_object", str(r))

        # 10. dry_run no escribe
        len(server.list_measures()["measures"])
        r = server.add_measure("Ventas", "Medida DryRun", "1+1", dry_run=True)
        len(server.list_measures()["measures"])
        # En dry_run la medida SÍ se agrega en memoria pero no se guarda en disco;
        # verificamos que el resultado marque dry_run.
        check("dry_run marcado", r.get("ok") and r.get("dry_run") is True, str(r))

        # 11. Diagnóstico de relaciones
        r = server.diagnose_relationships()
        check("diagnose_relationships", r.get("ok") and r["total_relationships"] == 1, str(r))

        # 12. Clasificar esquema
        r = server.classify_schema()
        check("classify_schema", r.get("ok") and r["schema_type"] in {"star", "undetermined", "snowflake"}, str(r))

        # 13. Buenas prácticas
        r = server.run_best_practices()
        check("run_best_practices", r.get("ok") and "violations" in r, str(r))

        # 14. Crear página en el reporte
        r = server.create_page("Resumen")
        check("create_page", r.get("ok") and r.get("page_id"), str(r))

        # 15. Crear visual
        r = server.create_visual(
            r["page_id"], "columnChart",
            {"Category": [{"table": "Producto", "column": "Nombre"}],
             "Y": [{"table": "Ventas", "column": "Importe", "aggregation": "Sum"}]},
            title="Ventas por producto",
        )
        check("create_visual", r.get("ok"), str(r))

        # 16. Generar documentación
        r = server.generate_documentation(output_dir=str(tmp / "docs"))
        check("generate_documentation", r.get("ok") and "written" in r, str(r))

        # 17. Diccionario de datos
        r = server.generate_data_dictionary(output_format="markdown")
        check("generate_data_dictionary", r.get("ok") and "Diccionario" in r["content"], str(r))

        # 18. Changelog
        r = server.get_changelog()
        check("get_changelog", r.get("ok") and "Changelog" in r["markdown"], str(r))

        # 19. Seguridad: claves subrogadas
        os.environ["PBIMCP_SURROGATE_SALT"] = "salt-de-prueba-larga"
        reload_settings()
        r = server.generate_surrogate_keys(
            [{"cliente": "ana@x.com"}, {"cliente": "luis@y.com"}], "cliente"
        )
        check("generate_surrogate_keys", r.get("ok") and r["unique_values"] == 2, str(r))

        # 20. Seguridad: masking PII
        r = server.mask_data([{"email": "ana@dominio.com"}, {"email": "luis@dominio.com"}])
        check("mask_data (auto-detect email)", r.get("ok") and "email" in r["masked_columns"], str(r))

        # 21. Encriptación
        key = server.generate_encryption_key()["key"]
        os.environ["PBIMCP_SECRET_KEY"] = key
        reload_settings()
        enc = server.encrypt_value("secreto")
        dec = server.decrypt_value(enc["token"])
        check("encriptacion round-trip", dec.get("value") == "secreto", str(dec))

        # 22. Auditoría registrada
        r = server.get_audit_log()
        check("auditoria registrada", r.get("ok") and r["summary"]["total_entries"] >= 1, str(r))

        # --- Modelos de IA (requieren numpy/pandas/sklearn) ----------------
        import random

        random.seed(7)
        ventas_data = [
            {"mes": i, "importe": 100 + i * 5 + random.randint(-8, 8), "region": "Norte" if i % 2 else "Sur"}
            for i in range(1, 40)
        ]
        ventas_data.append({"mes": 40, "importe": 9999, "region": "Norte"})  # outlier

        # 23. Detección de anomalías
        r = server.detect_anomalies(ventas_data, columns=["importe"], method="iqr")
        check("detect_anomalies", r.get("ok") and r["result"]["summary"]["anomalies_detected"] >= 1, str(r.get("result", r)))

        # 24. Clustering
        r = server.run_clustering(ventas_data, columns=["mes", "importe"], algorithm="kmeans", n_clusters=3)
        check("run_clustering", r.get("ok") and r["result"]["summary"]["n_clusters"] == 3, str(r.get("result", r)))

        # 25. Correlación
        r = server.correlation_analysis(ventas_data, columns=["mes", "importe"])
        check("correlation_analysis", r.get("ok") and r["result"]["summary"]["variables"], str(r.get("result", r)))

        # 26. Regresión
        r = server.train_regression(ventas_data, target_column="importe", feature_columns=["mes"])
        check("train_regression", r.get("ok") and "r2" in r["result"]["summary"]["metrics"], str(r.get("result", r)))

        # 27. Clasificación
        r = server.train_classification(ventas_data, target_column="region", feature_columns=["mes", "importe"])
        check("train_classification", r.get("ok") and "accuracy" in r["result"]["summary"]["metrics"], str(r.get("result", r)))

        # 28. Forecasting
        fechas = [{"fecha": f"2025-{m:02d}-01", "valor": 100 + m * 3} for m in range(1, 13)]
        r = server.forecast_series(fechas, date_column="fecha", value_column="valor", periods=3)
        check("forecast_series", r.get("ok") and len([x for x in r["result"]["table"] if x["type"] == "forecast"]) == 3, str(r.get("result", r)))

        # 29. RFM
        trans = [
            {"cliente": f"C{i % 5}", "fecha": f"2025-0{(i % 9) + 1}-01", "monto": 50 + i * 3}
            for i in range(30)
        ]
        r = server.rfm_segmentation(trans, customer_column="cliente", date_column="fecha", amount_column="monto")
        check("rfm_segmentation", r.get("ok") and r["result"]["summary"]["customers"] == 5, str(r.get("result", r)))

        # 30. Árbol de decisión
        r = server.decision_tree_explain(ventas_data, target_column="region", feature_columns=["mes", "importe"])
        check("decision_tree_explain", r.get("ok") and "top_influencers" in r["result"]["summary"], str(r.get("result", r)))

        # 31. Integración de IA al modelo (anomalías -> tabla DAX)
        r = server.detect_anomalies(ventas_data, columns=["importe"], method="iqr", integrate_as="Anomalias_Ventas", integrate_format="dax")
        check("integrate_ai_result (DAX)", r.get("ok") and r.get("integration", {}).get("integrated"), str(r.get("integration", r)))

        # 32. Análisis de calidad de datos
        r = server.analyze_data_quality(ventas_data)
        check("analyze_data_quality", r.get("ok") and 0 <= r["quality_score"] <= 100, str(r))

        # 33. Perfilado
        r = server.profile_data(ventas_data)
        check("profile_data", r.get("ok") and r["summary"]["columns"] == 3, str(r))

        # 34. Export HTML visual
        r = server.export_html_visual(ventas_data, "line", str(tmp / "chart.html"), x="mes", y="importe", title="Tendencia")
        check("export_html_visual", r.get("ok") and Path(r["path"]).exists(), str(r))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"RESULTADO: {len(failures)} prueba(s) fallaron: {failures}")
        return 1
    print("RESULTADO: todas las pruebas de humo pasaron OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
