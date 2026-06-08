"""Tests para algoritmos de clustering (K-Means, Hierarchical, DBSCAN)."""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.clustering import run_clustering


class TestClustering:
    """Suite de tests para clustering."""

    def test_kmeans_clustering(self, sample_numeric_data: pd.DataFrame) -> None:
        """K-Means debe agrupar datos en el número especificado de clústeres."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            algorithm="kmeans",
            n_clusters=3,
        )

        assert result.ok
        assert result.model_type == "clustering"
        assert result.clusters is not None
        assert result.n_clusters == 3
        # Debe tener asignaciones de clúster para cada fila
        assert len(result.clusters) == len(sample_numeric_data)

    def test_kmeans_auto_cluster_count(self, sample_numeric_data: pd.DataFrame) -> None:
        """K-Means debe estimar número de clústeres si n_clusters es None."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            algorithm="kmeans",
            n_clusters=None,  # Auto
        )

        assert result.ok
        assert result.n_clusters is not None
        assert result.n_clusters > 0
        assert result.n_clusters <= len(sample_numeric_data)

    def test_hierarchical_clustering(self, sample_numeric_data: pd.DataFrame) -> None:
        """Clustering jerárquico debe funcionar."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="hierarchical",
            n_clusters=4,
        )

        assert result.ok
        assert result.model_type == "clustering"
        assert result.clusters is not None
        assert result.n_clusters == 4

    def test_clustering_with_csv_input(self, sample_csv_file: pd.DataFrame) -> None:
        """Debe aceptar path a archivo CSV."""
        result = run_clustering(
            str(sample_csv_file),
            columns=["Amount", "Quantity"],
            algorithm="kmeans",
            n_clusters=3,
        )

        assert result.ok
        assert result.model_type == "clustering"

    def test_autodetect_numeric_columns(self, sample_sales_data: pd.DataFrame) -> None:
        """Debe autodetectar columnas numéricas."""
        result = run_clustering(
            sample_sales_data,
            columns=None,  # Autodetectar
            algorithm="kmeans",
            n_clusters=2,
        )

        assert result.ok
        assert result.clusters is not None

    @pytest.mark.parametrize("algorithm", ["kmeans", "hierarchical"])
    def test_all_algorithms_return_valid_result(
        self, sample_numeric_data: pd.DataFrame, algorithm: str
    ) -> None:
        """Todos los algoritmos deben devolver resultados válidos."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            algorithm=algorithm,
            n_clusters=3,
        )

        assert result.ok
        assert result.model_type == "clustering"
        assert hasattr(result, "clusters")
        assert hasattr(result, "to_dict")

    def test_clustering_silhouette_score(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe incluir score de calidad (silhouette, inertia)."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            algorithm="kmeans",
            n_clusters=3,
        )

        result_dict = result.to_dict()
        assert result_dict is not None
        # Debe incluir alguna métrica de calidad
        assert "metrics" in result_dict or "silhouette_score" in result_dict or "inertia" in result_dict

    def test_clustering_with_different_cluster_counts(
        self, sample_numeric_data: pd.DataFrame
    ) -> None:
        """Diferentes números de clústeres deben producir resultados válidos."""
        for n in [2, 3, 5, 10]:
            result = run_clustering(
                sample_numeric_data,
                columns=["Feature1", "Feature2"],
                algorithm="kmeans",
                n_clusters=n,
            )
            assert result.ok
            assert result.n_clusters == n

    def test_empty_dataframe_handling(self) -> None:
        """Debe manejar DataFrames vacías."""
        empty_df = pd.DataFrame({"A": [], "B": []})
        try:
            result = run_clustering(empty_df, algorithm="kmeans", n_clusters=2)
            assert result is not None
        except (ValueError, RuntimeError):
            pass

    def test_single_feature_clustering(self, sample_numeric_data: pd.DataFrame) -> None:
        """Debe funcionar con una sola columna."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1"],
            algorithm="kmeans",
            n_clusters=2,
        )

        assert result.ok
        assert len(result.clusters) == len(sample_numeric_data)

    def test_result_serialization(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe ser serializable a diccionario."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2"],
            algorithm="kmeans",
            n_clusters=3,
        )

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "clusters" in result_dict
        assert "model_type" in result_dict
