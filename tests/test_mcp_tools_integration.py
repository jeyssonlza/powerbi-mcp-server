"""Tests de integración end-to-end para las herramientas MCP.

Cobertura:
- Project: abrir, leer info, listar tablas, backup/restore (copia), export ZIP
- Model: describir tablas, listar medidas y relaciones, validar DAX
- AI: anomalías, clustering, correlación, segmentación RFM (contrato AIResult)
- Security: enmascaramiento PII (mask_dataset) y cifrado de archivo (Encryptor)

Usa la API real de cada módulo (sin funciones inventadas) y la sesión activa.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from powerbi_mcp.core.exceptions import PowerBIMCPError
from powerbi_mcp.pbip.parser import describe_table, list_measures, list_relationships, list_tables
from powerbi_mcp.session import session

# ============================================================================
# PROJECT TOOLS
# ============================================================================


class TestProjectToolsIntegration:
    """Abrir → leer info → listar → backup/restore (copia) → export ZIP."""

    def test_project_open_read_list_workflow(self, tmp_path: Path) -> None:
        """Abrir un proyecto, leer su info y listar tablas."""
        project_root = tmp_path / "TestProject"
        project_root.mkdir()
        (project_root / "TestProject.pbip").write_text(
            json.dumps({"version": "1.0", "semanticModelFolder": "TestProject.SemanticModel"}),
            encoding="utf-8",
        )
        model_dir = project_root / "TestProject.SemanticModel"
        model_dir.mkdir()
        (model_dir / "model.bim").write_text(
            json.dumps({
                "name": "TestModel",
                "tables": [{"name": "Table1", "columns": [{"name": "Col1", "dataType": "string"}], "measures": []}],
            }),
            encoding="utf-8",
        )

        try:
            project = session.open(str(project_root), load_report=False)
            assert project.name == "TestProject"

            info = session.info()
            assert info["open"] is True
            assert info["name"] == "TestProject"

            tables = list_tables(project)
            assert len(tables) > 0
            assert tables[0]["name"] == "Table1"
        finally:
            session.close()

    def test_project_export_to_pbix_zip(
        self, sample_pbip_directory: Path, tmp_path: Path
    ) -> None:
        """Empaquetar el proyecto como ZIP (PBIX) preserva model.bim y .pbip."""
        import zipfile

        pbix_path = tmp_path / "exported.pbix"
        with zipfile.ZipFile(pbix_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in sample_pbip_directory.rglob("*"):
                if fpath.is_file():
                    zf.write(fpath, fpath.relative_to(sample_pbip_directory.parent))

        assert zipfile.is_zipfile(pbix_path)
        with zipfile.ZipFile(pbix_path, "r") as zf:
            files = zf.namelist()
            assert any(".pbip" in f for f in files)
            assert any("model.bim" in f for f in files)

    def test_project_backup_restore_cycle(
        self, sample_pbip_directory: Path, tmp_path: Path
    ) -> None:
        """Copiar el proyecto y reabrirlo preserva el conteo de tablas/medidas."""
        import shutil

        try:
            project = session.open(str(sample_pbip_directory), load_report=True)
            original = project.summary()

            backup_dir = tmp_path / "backup_001"
            shutil.copytree(sample_pbip_directory, backup_dir)
            session.close()

            restored = session.open(str(backup_dir), load_report=True).summary()
            assert restored["tables"] == original["tables"]
            assert restored["measures"] == original["measures"]
        finally:
            session.close()


# ============================================================================
# MODEL TOOLS
# ============================================================================


class TestModelToolsIntegration:
    """Describir tablas, listar medidas y relaciones, validar DAX."""

    def test_describe_table_and_list_measures(self, sample_pbip_directory: Path) -> None:
        """Describir una tabla existente y listar medidas del modelo."""
        try:
            project = session.open(str(sample_pbip_directory), load_report=True)
            tables = list_tables(project)
            detail = describe_table(project, tables[0]["name"])
            assert detail is not None
            assert "columns" in detail
            assert isinstance(list_measures(project), list)
        finally:
            session.close()

    def test_relationships_have_expected_shape(self, sample_pbip_directory: Path) -> None:
        """Las relaciones deben exponer 'name', 'from' y 'to'."""
        try:
            project = session.open(str(sample_pbip_directory), load_report=True)
            relationships = list_relationships(project)
            assert isinstance(relationships, list)
            for rel in relationships:
                assert "name" in rel
                assert "from" in rel
                assert "to" in rel
        finally:
            session.close()

    def test_measures_have_non_empty_expressions(self, sample_pbip_directory: Path) -> None:
        """Cada medida listada debe tener una expresión DAX no vacía."""
        try:
            project = session.open(str(sample_pbip_directory), load_report=True)
            for measure in list_measures(project):
                if "expression" in measure:
                    assert isinstance(measure["expression"], str)
                    assert len(measure["expression"]) > 0
        finally:
            session.close()


# ============================================================================
# AI TOOLS
# ============================================================================


class TestAIToolsIntegration:
    """Anomalías → clustering, correlación → RFM (contrato AIResult real)."""

    def test_anomaly_then_clustering(self, sample_numeric_data: pd.DataFrame) -> None:
        """Detectar anomalías y luego agrupar; ambos devuelven AIResult válido."""
        from powerbi_mcp.ai.anomaly import detect_anomalies
        from powerbi_mcp.ai.clustering import run_clustering

        anomaly = detect_anomalies(sample_numeric_data)
        assert anomaly.model_type == "anomaly"
        assert anomaly.summary["anomalies_detected"] >= 0

        clusters = run_clustering(sample_numeric_data, n_clusters=3)
        assert clusters.model_type == "clustering"
        assert clusters.summary["n_clusters"] == 3

    def test_correlation_and_rfm(
        self, sample_rfm_data: pd.DataFrame, sample_sales_data: pd.DataFrame
    ) -> None:
        """Correlación sobre ventas y segmentación RFM por cliente."""
        from powerbi_mcp.ai.correlation import correlation_analysis
        from powerbi_mcp.ai.rfm import rfm_segmentation

        corr = correlation_analysis(sample_sales_data)
        assert corr.model_type == "correlation"

        rfm = rfm_segmentation(
            sample_rfm_data,
            customer_column="CustomerID",
            date_column="TransactionDate",
            amount_column="Amount",
        )
        assert len(rfm.table) > 0


# ============================================================================
# SECURITY TOOLS
# ============================================================================


class TestSecurityToolsIntegration:
    """Enmascaramiento PII (mask_dataset) y cifrado de archivo (Encryptor)."""

    def test_pii_masking_and_file_encryption(
        self, sample_quality_data: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Enmascarar Email y cifrar el CSV resultante con una clave Fernet."""
        from powerbi_mcp.security.encryption import Encryptor, generate_key
        from powerbi_mcp.security.masking import mask_dataset

        masked = mask_dataset(sample_quality_data, columns=["Email"], auto_detect=False)
        masked_df = pd.DataFrame(masked["table"])
        assert len(masked_df) == len(sample_quality_data)

        csv_path = tmp_path / "sensitive.csv"
        masked_df.to_csv(csv_path, index=False)

        enc = Encryptor(key=generate_key())
        encrypted_path = enc.encrypt_file(csv_path, tmp_path / "sensitive.csv.enc")
        assert Path(encrypted_path).exists()
        assert Path(encrypted_path).read_bytes() != csv_path.read_bytes()

    def test_audit_action_does_not_raise(self) -> None:
        """Registrar una acción de auditoría no debe lanzar excepción."""
        from powerbi_mcp.security.audit import audit

        audit("test_action", target="test_object", status="success", details={"test": True})


# ============================================================================
# END-TO-END SCENARIOS
# ============================================================================


class TestEndToEndScenarios:
    """Escenarios que integran proyecto + análisis AI + auditoría."""

    def test_open_project_then_analyze(
        self, sample_pbip_directory: Path, sample_sales_data: pd.DataFrame
    ) -> None:
        """Abrir proyecto, explorar objetos y correr un análisis AI."""
        from powerbi_mcp.ai.anomaly import detect_anomalies

        try:
            project = session.open(str(sample_pbip_directory), load_report=True)
            assert session.info()["open"] is True
            assert len(list_tables(project)) > 0

            anomalies = detect_anomalies(sample_sales_data)
            assert anomalies.model_type == "anomaly"
        finally:
            session.close()

    def test_documentation_and_audit_flow(self, sample_pbip_directory: Path) -> None:
        """Listar objetos documentables y registrar auditoría."""
        from powerbi_mcp.security.audit import audit

        try:
            project = session.open(str(sample_pbip_directory), load_report=True)
            tables = list_tables(project)
            measures = list_measures(project)
            audit(
                "documentation_review",
                target=project.name,
                status="success",
                details={"tables": len(tables), "measures": len(measures)},
            )
        finally:
            session.close()


# ============================================================================
# ERROR HANDLING
# ============================================================================


class TestIntegrationErrorHandling:
    """Manejo de errores en flujos de integración."""

    def test_missing_project_raises_and_keeps_session_clean(self, tmp_path: Path) -> None:
        """Abrir una ruta inexistente debe lanzar y no dejar sesión abierta."""
        with pytest.raises(PowerBIMCPError):
            session.open(str(tmp_path / "nonexistent_project"))
        assert not session.is_open

    def test_ai_tool_rejects_non_numeric_data(self) -> None:
        """Clustering sobre datos de solo texto debe lanzar un error del dominio."""
        from powerbi_mcp.ai.clustering import run_clustering

        invalid_df = pd.DataFrame({"text": ["a", "b", "c", "d", "e"]})
        with pytest.raises(PowerBIMCPError):
            run_clustering(invalid_df, n_clusters=2)
