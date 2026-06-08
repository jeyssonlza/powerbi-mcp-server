"""Cliente de la Power BI REST API.

Envoltorio ligero sobre los endpoints más usados de la API de Power BI Service:

- Workspaces (grupos).
- Datasets y refrescos.
- Reportes.
- Ejecución de consultas DAX (``executeQueries``).

La autenticación se delega en :class:`~powerbi_mcp.powerbi_api.auth.PowerBIAuth`;
el token se adquiere de forma perezosa en la primera llamada y se reutiliza.
"""

from __future__ import annotations

from typing import Any, cast

from powerbi_mcp.config import Settings, get_settings
from powerbi_mcp.core.exceptions import PowerBIAPIError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.powerbi_api.auth import PowerBIAuth

logger = get_logger(__name__)

_API_BASE = "https://api.powerbi.com/v1.0/myorg"


class PowerBIClient:
    """Cliente para interactuar con Power BI Service vía REST API.

    Args:
        settings: Configuración. Si es ``None``, se toma la global.
        auth: Autenticador a usar. Si es ``None``, se crea uno por defecto.
    """

    def __init__(self, settings: Settings | None = None, auth: PowerBIAuth | None = None) -> None:
        self.settings = settings or get_settings()
        self.auth = auth or PowerBIAuth(self.settings)
        self._token: str | None = None

    # ------------------------------------------------------------------ infra
    def _get_token(self) -> str:
        """Obtiene (y cachea) el token de acceso."""
        if self._token is None:
            self._token = self.auth.get_token()
        return self._token

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una petición autenticada contra la API.

        Args:
            method: Método HTTP (``GET``, ``POST``...).
            path: Ruta relativa al endpoint base (empieza con ``/``).
            json_body: Cuerpo JSON opcional.
            params: Parámetros de query opcionales.

        Returns:
            La respuesta JSON como diccionario (``{}`` si no hay cuerpo).

        Raises:
            PowerBIAPIError: Si la respuesta es un error HTTP o de red.
        """
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise PowerBIAPIError("La librería 'requests' no está instalada.") from exc

        url = f"{_API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.request(
                method, url, headers=headers, json=json_body, params=params, timeout=60
            )
        except requests.RequestException as exc:
            raise PowerBIAPIError(
                "Fallo de red al llamar a la Power BI API.",
                details={"url": url, "error": str(exc)},
            ) from exc

        if response.status_code == 401:
            # Token expirado: reintenta una vez con token nuevo.
            self._token = None
            headers["Authorization"] = f"Bearer {self._get_token()}"
            response = requests.request(
                method, url, headers=headers, json=json_body, params=params, timeout=60
            )

        if not response.ok:
            raise PowerBIAPIError(
                "La Power BI API devolvió un error.",
                details={
                    "status": response.status_code,
                    "url": url,
                    "body": response.text[:500],
                },
            )

        if response.content and "application/json" in response.headers.get("Content-Type", ""):
            return cast(dict[str, Any], response.json())
        return {}

    # -------------------------------------------------------------- workspaces
    def list_workspaces(self) -> list[dict[str, Any]]:
        """Lista los workspaces (grupos) accesibles.

        Returns:
            Lista de workspaces con sus metadatos.
        """
        data = self._request("GET", "/groups")
        return cast(list[dict[str, Any]], data.get("value", []))

    # ---------------------------------------------------------------- datasets
    def list_datasets(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        """Lista los datasets de un workspace (o del área personal).

        Args:
            workspace_id: ID del workspace. Si es ``None``, usa "My workspace".

        Returns:
            Lista de datasets.
        """
        path = f"/groups/{workspace_id}/datasets" if workspace_id else "/datasets"
        return cast(list[dict[str, Any]], self._request("GET", path).get("value", []))

    def refresh_dataset(self, dataset_id: str, workspace_id: str | None = None) -> dict[str, Any]:
        """Dispara un refresco de un dataset.

        Args:
            dataset_id: ID del dataset.
            workspace_id: ID del workspace (opcional).

        Returns:
            Diccionario confirmando la solicitud de refresco.
        """
        base = f"/groups/{workspace_id}" if workspace_id else ""
        self._request("POST", f"{base}/datasets/{dataset_id}/refreshes", json_body={})
        logger.info("Refresco solicitado para dataset %s", dataset_id)
        return {"dataset_id": dataset_id, "refresh_requested": True}

    # ----------------------------------------------------------------- reports
    def list_reports(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        """Lista los reportes de un workspace (o del área personal).

        Args:
            workspace_id: ID del workspace (opcional).

        Returns:
            Lista de reportes.
        """
        path = f"/groups/{workspace_id}/reports" if workspace_id else "/reports"
        return cast(list[dict[str, Any]], self._request("GET", path).get("value", []))

    # --------------------------------------------------------------- DAX query
    def execute_dax(
        self,
        dataset_id: str,
        dax_query: str,
        *,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Ejecuta una consulta DAX contra un dataset publicado.

        Args:
            dataset_id: ID del dataset.
            dax_query: Consulta DAX (debe empezar por ``EVALUATE``).
            workspace_id: ID del workspace (opcional).

        Returns:
            Diccionario con las filas resultantes en ``rows``.

        Raises:
            PowerBIAPIError: Si la consulta falla.
        """
        base = f"/groups/{workspace_id}" if workspace_id else ""
        body = {"queries": [{"query": dax_query}], "serializerSettings": {"includeNulls": True}}
        data = self._request("POST", f"{base}/datasets/{dataset_id}/executeQueries", json_body=body)

        rows: list[dict[str, Any]] = []
        for result in data.get("results", []):
            for table in result.get("tables", []):
                rows.extend(table.get("rows", []))
        return {"dataset_id": dataset_id, "row_count": len(rows), "rows": rows}


__all__ = ["PowerBIClient"]
