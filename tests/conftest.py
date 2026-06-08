"""Fixtures y configuración compartida para tests de Power BI MCP.

Este módulo proporciona:
- Configuración de entorno de tests
- Datos de prueba estándar (DataFrames, modelos semánticos)
- Fixtures de proyecto (PBIP mock)
- Mocks de componentes externos
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from powerbi_mcp.config import reload_settings


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Configura variables de entorno para aislar tests.

    - Establece directorios temp para backups, logs y caché
    - Recarga configuración para aplicar nuevas rutas
    - Se ejecuta automáticamente en cada test (autouse=True)
    """
    monkeypatch.setenv("PBIMCP_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("PBIMCP_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("PBIMCP_CACHE_DIR", str(tmp_path / "cache"))
    reload_settings()
    yield
    reload_settings()  # Restaurar después del test


# ============================================================================
# FIXTURES DE DATOS DE PRUEBA
# ============================================================================


@pytest.fixture
def sample_sales_data() -> pd.DataFrame:
    """DataFrame de ventas para tests de análisis.

    Contiene 100 registros con las columnas típicas de un warehouse de ventas:
    - Fecha de transacción
    - Cliente
    - Producto
    - Cantidad
    - Importe
    - Región

    Returns:
        DataFrame con datos de ventas estándar.
    """
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    customers = [f"CUST_{i % 20:03d}" for i in range(100)]
    products = ["ProductA", "ProductB", "ProductC", "ProductD", "ProductE"]
    regions = ["North", "South", "East", "West"]

    return pd.DataFrame({
        "Date": dates,
        "CustomerID": customers,
        "Product": [products[i % 5] for i in range(100)],
        "Quantity": [int(i % 50 + 1) for i in range(100)],
        "Amount": [float((i * 45.5 + 1000) % 5000) for i in range(100)],
        "Region": [regions[i % 4] for i in range(100)],
    })


@pytest.fixture
def sample_forecast_data() -> pd.DataFrame:
    """Serie temporal para tests de forecasting.

    Datos mensuales de 2 años con tendencia y estacionalidad.

    Returns:
        DataFrame con columnas Date y Value.
    """
    dates = pd.date_range("2022-01-01", periods=24, freq="MS")
    # Tendencia + estacionalidad
    trend = [i * 10 for i in range(24)]
    seasonal = [100 * (1 + 0.3 * (i % 12 / 6 - 1)) for i in range(24)]
    values = [t + s + (i % 3) * 5 for i, (t, s) in enumerate(zip(trend, seasonal))]

    return pd.DataFrame({
        "Date": dates,
        "Value": values,
    })


@pytest.fixture
def sample_rfm_data() -> pd.DataFrame:
    """Datos de transacciones para tests de RFM.

    100 transacciones de 25 clientes únicos.

    Returns:
        DataFrame con CustomerID, TransactionDate, Amount.
    """
    dates = pd.date_range("2023-01-01", periods=100, freq="H")
    customers = [f"CUST_{i % 25:03d}" for i in range(100)]
    amounts = [float(100 + (i * 7.3) % 500) for i in range(100)]

    return pd.DataFrame({
        "CustomerID": customers,
        "TransactionDate": dates,
        "Amount": amounts,
    })


@pytest.fixture
def sample_numeric_data() -> pd.DataFrame:
    """Datos numéricos para tests de ML (anomalías, clustering, correlación).

    50 filas, 5 columnas numéricas (incluyendo algunas anomalías inyectadas).

    Returns:
        DataFrame con columnas Feature1-5.
    """
    import numpy as np

    np.random.seed(42)
    data = np.random.normal(100, 15, (50, 5))

    # Inyectar algunas anomalías
    data[0, 0] = 500  # Outlier en Feature1
    data[5, 2] = -200  # Outlier en Feature3

    return pd.DataFrame(
        data,
        columns=[f"Feature{i + 1}" for i in range(5)],
    )


@pytest.fixture
def sample_classification_data() -> pd.DataFrame:
    """Datos para tests de clasificación.

    80 registros con 4 features y un target categórico (Class: A/B).

    Returns:
        DataFrame con Features y clase objetivo.
    """
    import numpy as np

    np.random.seed(42)
    features = np.random.normal(0, 1, (80, 4))
    # Target separable basado en Feature1
    target = ["A" if features[i, 0] > 0 else "B" for i in range(80)]

    df = pd.DataFrame(features, columns=[f"Feature{i + 1}" for i in range(4)])
    df["Class"] = target
    return df


@pytest.fixture
def sample_quality_data() -> pd.DataFrame:
    """Datos con problemas de calidad para tests.

    - Valores nulos
    - Valores duplicados
    - Outliers
    - Inconsistencias de formato

    Returns:
        DataFrame con problemas típicos.
    """
    return pd.DataFrame({
        "ID": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 3,
        "Name": ["John", "Jane", None, "Bob", "John", "Alice", "  Charlie", "David", "", "Eve"] * 3,
        "Age": [25, 30, 28, None, 999, 35, 28, 42, 31, 29] * 3,  # 999 es outlier
        "Email": ["john@ex.com", "jane@ex.com", "john@ex.com", "bob@ex.com", None, "alice@ex.com"] * 5,
        "Score": [85.5, 90.0, 85.5, 78.0, 88.5, 92.0, 81.5, 79.0, 88.5, 95.0] * 3,
    })


# ============================================================================
# FIXTURES DE ARCHIVOS TEMPORALES
# ============================================================================


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_sales_data: pd.DataFrame) -> Path:
    """Archivo CSV con datos de ventas.

    Args:
        tmp_path: Directorio temporal pytest.
        sample_sales_data: Fixture de datos.

    Returns:
        Ruta al archivo CSV creado.
    """
    csv_path = tmp_path / "sales.csv"
    sample_sales_data.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_excel_file(tmp_path: Path, sample_sales_data: pd.DataFrame) -> Path:
    """Archivo Excel con datos de ventas.

    Args:
        tmp_path: Directorio temporal pytest.
        sample_sales_data: Fixture de datos.

    Returns:
        Ruta al archivo XLSX creado.
    """
    xlsx_path = tmp_path / "sales.xlsx"
    sample_sales_data.to_excel(xlsx_path, index=False)
    return xlsx_path


@pytest.fixture
def sample_parquet_file(tmp_path: Path, sample_sales_data: pd.DataFrame) -> Path:
    """Archivo Parquet con datos de ventas.

    Args:
        tmp_path: Directorio temporal pytest.
        sample_sales_data: Fixture de datos.

    Returns:
        Ruta al archivo Parquet creado.
    """
    pq_path = tmp_path / "sales.parquet"
    sample_sales_data.to_parquet(pq_path, index=False)
    return pq_path


# ============================================================================
# MOCKS Y UTILIDADES
# ============================================================================


@pytest.fixture
def mock_semantic_model() -> Any:
    """Mock simplificado de un modelo semántico para tests.

    Returns:
        Objeto con atributos tables, measures, relationships.
    """

    class MockTable:
        def __init__(self, name: str) -> None:
            self.name = name
            self.columns = []

    class MockMeasure:
        def __init__(self, name: str, table: str) -> None:
            self.name = name
            self.table = table

    class MockModel:
        def __init__(self) -> None:
            self.tables = [MockTable("Customers"), MockTable("Sales"), MockTable("Products")]
            self.measures = [
                MockMeasure("Total Sales", "Sales"),
                MockMeasure("Count Customers", "Customers"),
            ]
            self.relationships = []

    return MockModel()


class CaptureHandler(pytest.LogCaptureFixture):
    """Wrapper para capturar logs de manera más ergonómica en tests."""

    def messages(self, level: str = "INFO") -> list[str]:
        """Devuelve lista de mensajes registrados en el nivel especificado."""
        return [r.message for r in self.records if r.levelname == level]


@pytest.fixture
def capture_logs(caplog: pytest.LogCaptureFixture) -> CaptureHandler:
    """Fixture para capturar logs con métodos auxiliares.

    Args:
        caplog: Fixture estándar de pytest.

    Returns:
        Wrapper con métodos auxiliares.
    """
    return CaptureHandler(caplog.records)


# ============================================================================
# FIXTURES PARA PBIP (Power BI Project)
# ============================================================================


@pytest.fixture
def sample_model_dict() -> dict[str, Any]:
    """Diccionario TMSL básico (modelo semántico JSON).

    Simula un model.bim mínimo con tablas, columnas y medidas.

    Returns:
        Diccionario TMSL válido para pruebas.
    """
    return {
        "name": "TestModel",
        "compatibilityLevel": 1550,
        "version": "1.0.0",
        "tables": [
            {
                "name": "DimCustomers",
                "columns": [
                    {
                        "name": "CustomerID",
                        "dataType": "int64",
                        "sourceColumn": "CustomerID",
                    },
                    {
                        "name": "CustomerName",
                        "dataType": "string",
                        "sourceColumn": "CustomerName",
                    },
                ],
                "measures": [
                    {
                        "name": "CountCustomers",
                        "expression": "COUNTROWS('DimCustomers')",
                    },
                ],
                "partitions": [
                    {
                        "name": "DimCustomers",
                        "source": {
                            "type": "m",
                            "expression": "let\n  source = ...\nend",
                        },
                    },
                ],
            },
            {
                "name": "FactSales",
                "columns": [
                    {
                        "name": "SalesID",
                        "dataType": "int64",
                        "sourceColumn": "SalesID",
                    },
                    {
                        "name": "Amount",
                        "dataType": "double",
                        "sourceColumn": "Amount",
                    },
                    {
                        "name": "Quantity",
                        "dataType": "int64",
                        "sourceColumn": "Quantity",
                    },
                ],
                "measures": [
                    {
                        "name": "TotalSales",
                        "expression": "SUMX('FactSales', 'FactSales'[Amount])",
                    },
                    {
                        "name": "AverageSale",
                        "expression": "AVERAGE('FactSales'[Amount])",
                    },
                ],
                "partitions": [
                    {
                        "name": "FactSales",
                        "source": {
                            "type": "m",
                            "expression": "let\n  source = ...\nend",
                        },
                    },
                ],
            },
        ],
        "relationships": [
            {
                "name": "rel_Sales_Customers",
                "fromTable": "FactSales",
                "fromColumn": "CustomerID",
                "toTable": "DimCustomers",
                "toColumn": "CustomerID",
                "crossFilteringBehavior": "bothDirections",
            },
        ],
    }


@pytest.fixture
def sample_pbip_directory(tmp_path: Path, sample_model_dict: dict[str, Any]) -> Path:
    """Crea una estructura de carpetas PBIP mínima en disco (temporal).

    Estructura:
        TestProject.pbip/
        ├── TestProject.pbip
        ├── TestProject.SemanticModel/
        │   └── model.bim
        └── TestProject.Report/
            └── report.json

    Args:
        tmp_path: Directorio temporal pytest.
        sample_model_dict: Fixture de modelo TMSL.

    Returns:
        Ruta a la carpeta raíz del proyecto PBIP.
    """
    import json

    project_name = "TestProject"
    project_root = tmp_path / project_name
    project_root.mkdir()

    # Archivo .pbip (metadatos del proyecto)
    pbip_file = project_root / f"{project_name}.pbip"
    pbip_content = {
        "version": "1.0",
        "semanticModelFolder": f"{project_name}.SemanticModel",
        "reportFolder": f"{project_name}.Report",
    }
    pbip_file.write_text(json.dumps(pbip_content, indent=2), encoding="utf-8")

    # Modelo semántico
    model_dir = project_root / f"{project_name}.SemanticModel"
    model_dir.mkdir()
    model_bim = model_dir / "model.bim"
    model_bim.write_text(json.dumps(sample_model_dict, indent=2), encoding="utf-8")

    # Reporte
    report_dir = project_root / f"{project_name}.Report"
    report_dir.mkdir()
    report_json = report_dir / "report.json"
    report_content = {
        "version": "1.0.0",
        "pages": [
            {
                "name": "Page1",
                "displayName": "Sales Overview",
            },
        ],
    }
    report_json.write_text(json.dumps(report_content, indent=2), encoding="utf-8")

    return project_root


@pytest.fixture
def sample_pbip_file(tmp_path: Path, sample_pbip_directory: Path) -> Path:
    """Crea un archivo PBIX comprimido (PBIP como ZIP).

    Returns:
        Ruta al archivo PBIX temporal.
    """
    import zipfile

    pbix_path = tmp_path / "TestProject.pbix"

    with zipfile.ZipFile(pbix_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Añadir todos los archivos de la estructura PBIP
        for fpath in sample_pbip_directory.rglob("*"):
            if fpath.is_file():
                arcname = fpath.relative_to(sample_pbip_directory.parent)
                zf.write(fpath, arcname)

    return pbix_path


@pytest.fixture
def sample_table_meta() -> dict[str, Any]:
    """Metadatos de una tabla para tests de documentación.

    Returns:
        Diccionario con estructura de tabla.
    """
    return {
        "name": "DimDate",
        "description": "Tabla de dimensión de fechas",
        "columns": [
            {
                "name": "DateKey",
                "dataType": "int64",
                "description": "Clave única de la fecha",
            },
            {
                "name": "Date",
                "dataType": "dateTime",
                "description": "Fecha completa",
            },
        ],
        "measures": [
            {
                "name": "DayOfWeek",
                "expression": "WEEKDAY([Date])",
                "description": "Día de la semana",
            },
        ],
    }


@pytest.fixture
def sample_model_meta() -> dict[str, Any]:
    """Metadatos de un modelo semántico para tests.

    Returns:
        Diccionario con metadatos del modelo completo.
    """
    return {
        "name": "SalesModel",
        "version": "1.0.0",
        "description": "Modelo de ventas con análisis histórico",
        "tables": [
            {
                "name": "FactSales",
                "description": "Hechos de ventas",
                "columns": 5,
                "measures": 8,
            },
            {
                "name": "DimDate",
                "description": "Dimensión de fechas",
                "columns": 3,
                "measures": 2,
            },
        ],
        "relationships": 3,
        "cultureDef": "es-ES",
    }


__all__ = [
    "setup_test_env",
    "sample_sales_data",
    "sample_forecast_data",
    "sample_rfm_data",
    "sample_numeric_data",
    "sample_classification_data",
    "sample_quality_data",
    "sample_csv_file",
    "sample_excel_file",
    "sample_parquet_file",
    "mock_semantic_model",
    "capture_logs",
    "sample_model_dict",
    "sample_pbip_directory",
    "sample_pbip_file",
    "sample_table_meta",
    "sample_model_meta",
]
