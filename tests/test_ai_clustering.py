"""Tests para algoritmos de clustering (K-Means, Hierarchical).

Valida el contrato real de ``run_clustering`` -> ``AIResult`` con ``summary``
que incluye ``algorithm``, ``n_clusters``, ``silhouette_score`` y ``profiles``,
y un ``table`` con la columna ``cluster`` por fila.
"""

from __future__ import annotations

import pandas as pd
import pytest

from powerbi_mcp.ai.clustering import VALID_ALGORITHMS, run_clustering
from powerbi_mcp.core.exceptions import ValidationError


class TestClustering:
    """Suite de tests para clustering."""

    def test_kmeans_returns_valid_result(self, sample_numeric_data: pd.DataFrame) -> None:
        """K-Means debe agrupar en el número especificado de clústeres."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3"],
            algorithm="kmeans",
            n_clusters=3,
        )
        assert result.model_type == "clustering"
        assert result.summary["algorithm"] == "kmeans"
        assert result.summary["n_clusters"] == 3
        assert "cluster" in result.columns
        assert len(result.table) == len(sample_numeric_data)

    def test_each_row_has_cluster_label(self, sample_numeric_data: pd.DataFrame) -> None:
        """Cada fila del resultado debe tener una etiqueta de clúster válida."""
        result = run_clustering(
            sample_numeric_data, columns=["Feature1", "Feature2"], n_clusters=3
        )
        labels = {row["cluster"] for row in result.table}
        assert labels <= {0, 1, 2}

    def test_auto_select_k(self, sample_numeric_data: pd.DataFrame) -> None:
        """Sin n_clusters, debe autodeterminar un k entre 2 y el máximo."""
        result = run_clustering(
            sample_numeric_data, columns=["Feature1", "Feature2"], n_clusters=None
        )
        assert 2 <= result.summary["n_clusters"] <= len(sample_numeric_data)

    def test_hierarchical_algorithm(self, sample_numeric_data: pd.DataFrame) -> None:
        """El algoritmo jerárquico debe funcionar."""
        result = run_clustering(
            sample_numeric_data,
            columns=["Feature1", "Feature2", "Feature3", "Feature4"],
            algorithm="hierarchical",
            n_clusters=4,
        )
        assert result.summary["algorithm"] == "hierarchical"
        assert result.summary["n_clusters"] == 4

    def test_silhouette_score_present(self, sample_numeric_data: pd.DataFrame) -> None:
        """El summary debe incluir un silhouette_score entre -1 y 1."""
        result = run_clustering(
            sample_numeric_data, columns=["Feature1", "Feature2", "Feature3"], n_clusters=3
        )
        assert -1.0 <= result.summary["silhouette_score"] <= 1.0

    def test_cluster_profiles_present(self, sample_numeric_data: pd.DataFrame) -> None:
        """El summary debe incluir un perfil por clúster con tamaños y medias."""
        result = run_clustering(
            sample_numeric_data, columns=["Feature1", "Feature2"], n_clusters=3
        )
        profiles = result.summary["profiles"]
        assert len(profiles) == 3
        for prof in profiles.values():
            assert "size" in prof
            assert "means" in prof

    @pytest.mark.parametrize("algorithm", ["kmeans", "hierarchical"])
    def test_all_algorithms_work(
        self, sample_numeric_data: pd.DataFrame, algorithm: str
    ) -> None:
        """Ambos algoritmos deben devolver un resultado válido."""
        result = run_clustering(
            sample_numeric_data, columns=["Feature1", "Feature2"], algorithm=algorithm, n_clusters=3
        )
        assert result.model_type == "clustering"

    def test_invalid_algorithm_raises(self, sample_numeric_data: pd.DataFrame) -> None:
        """Un algoritmo no soportado debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            run_clustering(sample_numeric_data, algorithm="dbscan", n_clusters=3)

    def test_n_clusters_out_of_range_raises(self, sample_numeric_data: pd.DataFrame) -> None:
        """Un n_clusters mayor que el número de filas debe lanzar ValidationError."""
        with pytest.raises(ValidationError):
            run_clustering(sample_numeric_data, columns=["Feature1"], n_clusters=999)

    def test_works_with_csv_input(self, sample_csv_file) -> None:
        """Debe aceptar una ruta a CSV como entrada."""
        result = run_clustering(
            str(sample_csv_file), columns=["Amount", "Quantity"], n_clusters=3
        )
        assert result.model_type == "clustering"

    def test_result_serializable(self, sample_numeric_data: pd.DataFrame) -> None:
        """El resultado debe serializarse a un diccionario."""
        result = run_clustering(sample_numeric_data, columns=["Feature1", "Feature2"], n_clusters=2)
        as_dict = result.to_dict()
        assert as_dict["model_type"] == "clustering"
        assert as_dict["row_count"] == len(sample_numeric_data)

    def test_valid_algorithms_constant(self) -> None:
        """La constante VALID_ALGORITHMS debe contener los dos algoritmos."""
        assert {"kmeans", "hierarchical"} == VALID_ALGORITHMS
