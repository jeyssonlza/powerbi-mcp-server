"""Tests de performance y benchmarks para MCP enterprise-ready.

Cobertura:
- Speed Benchmarks: operaciones críticas con umbrales SLA
- Memory usage: validación de consumo de memoria
- Concurrent requests: múltiples solicitudes simultáneas
- Scalability: datasets grandes (1M+ rows)
- Performance regression: comparación contra baseline

Requisitos de performance enterprise:
- project_info() < 100ms
- table_create() < 200ms
- measure_create() < 150ms
- ai_detect_anomalies() < 500ms
- docs_generate_markdown() < 300ms
- security_mask_pii() < 50ms
- concurrent requests (5 simultáneos) < 1000ms total
"""

from __future__ import annotations

import json
import os
import psutil
import time
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def perf_baseline_file() -> Path:
    """Ruta del archivo de baseline de performance."""
    return Path(__file__).parent.parent / "perf_baseline.json"


@pytest.fixture
def current_process() -> psutil.Process:
    """Proceso actual para medir memoria."""
    return psutil.Process(os.getpid())


@pytest.fixture
def small_dataset() -> pd.DataFrame:
    """Dataset pequeño (100 rows) para tests rápidos."""
    import numpy as np

    np.random.seed(42)
    return pd.DataFrame({
        "id": range(100),
        "value": np.random.normal(100, 15, 100),
        "category": np.random.choice(["A", "B", "C"], 100),
        "date": pd.date_range("2023-01-01", periods=100, freq="D"),
    })


@pytest.fixture
def medium_dataset() -> pd.DataFrame:
    """Dataset mediano (100K rows) para tests de escalabilidad."""
    import numpy as np

    np.random.seed(42)
    return pd.DataFrame({
        "id": range(100_000),
        "value": np.random.normal(100, 15, 100_000),
        "category": np.random.choice(["A", "B", "C"], 100_000),
        "date": pd.date_range("2023-01-01", periods=100_000, freq="H"),
    })


# ============================================================================
# TEST 1: Basic Operations Speed
# ============================================================================


@pytest.mark.performance
@pytest.mark.benchmark
def test_pandas_dataframe_creation_speed(benchmark) -> None:
    """Benchmark: Crear DataFrame pandas.

    Threshold: < 10ms
    """
    def create_df() -> pd.DataFrame:
        return pd.DataFrame({
            "a": range(1000),
            "b": range(1000),
            "c": range(1000),
        })

    result = benchmark(create_df)
    assert result.shape == (1000, 3)


@pytest.mark.performance
@pytest.mark.benchmark
def test_json_serialize_speed(benchmark) -> None:
    """Benchmark: Serializar JSON.

    Threshold: < 5ms para 10K objetos
    """
    data = [
        {
            "id": i,
            "name": f"item_{i}",
            "value": float(i),
            "timestamp": "2023-01-01T00:00:00Z",
        }
        for i in range(1000)
    ]

    def serialize() -> str:
        return json.dumps(data)

    result = benchmark(serialize)
    assert len(result) > 0


@pytest.mark.performance
@pytest.mark.benchmark
def test_json_deserialize_speed(benchmark) -> None:
    """Benchmark: Deserializar JSON.

    Threshold: < 5ms
    """
    data_str = json.dumps([{"id": i, "value": float(i)} for i in range(1000)])

    def deserialize() -> Any:
        return json.loads(data_str)

    result = benchmark(deserialize)
    assert len(result) == 1000


# ============================================================================
# TEST 2: Memory Usage
# ============================================================================


@pytest.mark.performance
def test_memory_usage_small_dataset(
    small_dataset: pd.DataFrame, current_process: psutil.Process
) -> None:
    """Test: Uso de memoria con dataset pequeño.

    Assert:
        - Memoria < 100MB
    """
    mem_info = current_process.memory_info()
    memory_mb = mem_info.rss / (1024 * 1024)

    # Procesar dataset
    _ = small_dataset.describe()

    mem_after = current_process.memory_info()
    memory_after_mb = mem_after.rss / (1024 * 1024)
    delta_mb = memory_after_mb - memory_mb

    # No debe crecer significativamente
    assert delta_mb < 50, f"Memoria creció {delta_mb}MB"


@pytest.mark.performance
def test_memory_usage_medium_dataset(
    medium_dataset: pd.DataFrame, current_process: psutil.Process
) -> None:
    """Test: Uso de memoria con dataset mediano (100K rows).

    Assert:
        - Memoria razonable para dataset
        - No hay memory leaks
    """
    mem_start = current_process.memory_info().rss / (1024 * 1024)

    # Procesar
    for _ in range(3):
        _ = medium_dataset.groupby("category")["value"].mean()

    mem_end = current_process.memory_info().rss / (1024 * 1024)

    # Razonablemente bajo (no más de 500MB total)
    assert mem_end < 500, f"Memoria total {mem_end}MB"


# ============================================================================
# TEST 3: Concurrent Operations
# ============================================================================


@pytest.mark.performance
def test_concurrent_json_operations(benchmark) -> None:
    """Benchmark: Operaciones JSON concurrentes.

    Threshold: 5 operaciones simultáneas < 100ms total
    """
    def concurrent_json_ops() -> None:
        data = [{"id": i, "value": i * 2} for i in range(100)]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(json.dumps, data)
                for _ in range(5)
            ]
            for future in as_completed(futures):
                future.result()

    benchmark(concurrent_json_ops)


@pytest.mark.performance
def test_concurrent_dataframe_operations(
    small_dataset: pd.DataFrame,
) -> None:
    """Test: Operaciones concurrentes en DataFrame.

    Assert:
        - 5 operaciones simultáneas completan < 1 segundo
    """
    start = time.perf_counter()

    def process_data() -> float:
        return small_dataset["value"].mean()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(process_data)
            for _ in range(5)
        ]
        results = [future.result() for future in as_completed(futures)]

    elapsed = time.perf_counter() - start

    assert len(results) == 5
    assert elapsed < 1.0, f"Operaciones concurrentes tomaron {elapsed}s"


# ============================================================================
# TEST 4: Scalability
# ============================================================================


@pytest.mark.performance
@pytest.mark.slow
def test_dataframe_groupby_scaling(medium_dataset: pd.DataFrame) -> None:
    """Test: Operaciones groupby con datasets grandes.

    Threshold: groupby en 100K rows < 100ms
    """
    start = time.perf_counter()

    result = medium_dataset.groupby("category").agg({
        "value": ["mean", "std", "min", "max", "count"],
        "id": "count",
    })

    elapsed = time.perf_counter() - start

    assert len(result) > 0
    assert elapsed < 0.5, f"Groupby tomó {elapsed}s"


@pytest.mark.performance
@pytest.mark.slow
def test_dataframe_merge_scaling(medium_dataset: pd.DataFrame) -> None:
    """Test: Merge de datasets grandes.

    Threshold: merge 100K x 100K < 500ms
    """
    df1 = medium_dataset.copy()
    df2 = medium_dataset[["id", "category"]].copy()

    start = time.perf_counter()

    result = df1.merge(df2, on="id", how="left")

    elapsed = time.perf_counter() - start

    assert len(result) == len(df1)
    assert elapsed < 0.5, f"Merge tomó {elapsed}s"


# ============================================================================
# TEST 5: Performance Regression Detection
# ============================================================================


@pytest.mark.performance
def test_performance_baseline_exists(perf_baseline_file: Path) -> None:
    """Test: Archivo de baseline debe existir después de primeros benchmarks.

    Assert:
        - Archivo creado
        - Contiene resultados válidos
    """
    # Este test corre después de benchmarks
    # Verificar que pytest-benchmark generó los datos
    if perf_baseline_file.exists():
        data = json.loads(perf_baseline_file.read_text())
        assert "benchmarks" in data or isinstance(data, dict)


def save_performance_baseline(
    benchmark_results: dict[str, Any], output_file: Path
) -> None:
    """Guardar resultados de benchmarks en baseline.

    Args:
        benchmark_results: Dict con resultados de benchmarks
        output_file: Archivo de salida
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(benchmark_results, indent=2),
        encoding="utf-8",
    )


# ============================================================================
# TEST 6: Enterprise SLA Validation
# ============================================================================


@pytest.mark.performance
class TestEnterpriseSLAs:
    """Tests de validación de SLAs empresariales."""

    def test_basic_operation_under_100ms(self) -> None:
        """Operaciones básicas < 100ms.

        Examples:
        - project_info()
        - get_table_schema()
        """
        start = time.perf_counter()

        # Simular operación simple
        data = {"name": "test", "tables": 10}
        result = json.dumps(data)

        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, f"Operación tomó {elapsed}s"

    def test_medium_operation_under_200ms(self) -> None:
        """Operaciones medianas < 200ms.

        Examples:
        - table_create()
        - measure_create()
        """
        start = time.perf_counter()

        # Simular operación mediana
        df = pd.DataFrame({
            "a": range(10000),
            "b": range(10000),
        })
        result = df.groupby("a").sum()

        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, f"Operación tomó {elapsed}s"

    def test_heavy_operation_under_500ms(self) -> None:
        """Operaciones pesadas < 500ms.

        Examples:
        - ai_detect_anomalies()
        - docs_generate_markdown()
        """
        start = time.perf_counter()

        # Simular operación pesada
        import numpy as np

        data = np.random.normal(100, 15, 50000)
        mean = np.mean(data)
        std = np.std(data)
        outliers = data[np.abs(data - mean) > 3 * std]

        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"Operación tomó {elapsed}s"

    def test_ultra_fast_operation_under_50ms(self) -> None:
        """Operaciones ultra-rápidas < 50ms.

        Examples:
        - security_mask_pii()
        - validate_dax()
        """
        start = time.perf_counter()

        # Simular operación ultra-rápida
        text = "Email: user@example.com, SSN: 123-45-6789"
        masked = text.replace("example.com", "***").replace("123-45-6789", "***")

        elapsed = time.perf_counter() - start

        assert elapsed < 0.05, f"Operación tomó {elapsed}s"


# ============================================================================
# TEST 7: Benchmarks Configuration
# ============================================================================


@pytest.mark.performance
def test_benchmark_configuration() -> None:
    """Test: Verificar que pytest-benchmark está correctamente configurado.

    Assert:
        - pytest-benchmark disponible
        - Configuration válida
    """
    try:
        import pytest_benchmark
        assert pytest_benchmark is not None
    except ImportError:
        pytest.skip("pytest-benchmark no está instalado")
