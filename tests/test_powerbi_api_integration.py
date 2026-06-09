"""Tests de integración con la Power BI REST API (mocked).

El ``PowerBIClient`` real delega la autenticación en ``PowerBIAuth`` y usa
``requests.request`` dentro de ``_request``. Aquí se inyecta un ``auth`` falso
(sin Azure) y se mockea ``requests.request`` para validar, sin red ni
credenciales reales:

- Construcción de rutas (workspace vs área personal),
- Parseo de respuestas (workspaces, datasets, filas DAX),
- Manejo de errores HTTP (-> PowerBIAPIError),
- Reintento ante 401 y cacheo del token.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from powerbi_mcp.config import Settings
from powerbi_mcp.core.exceptions import PowerBIAPIError
from powerbi_mcp.powerbi_api.client import PowerBIClient


def _make_client() -> PowerBIClient:
    """Crea un cliente con un autenticador falso (sin Azure)."""
    auth = MagicMock()
    auth.get_token.return_value = "fake_token"
    return PowerBIClient(settings=Settings(), auth=auth)


def _resp(status: int = 200, json_body: Any = None) -> MagicMock:
    """Construye una respuesta HTTP falsa compatible con el cliente."""
    r = MagicMock()
    r.status_code = status
    r.ok = 200 <= status < 400
    r.headers = {"Content-Type": "application/json"}
    r.content = b"{}" if json_body is not None else b""
    r.json.return_value = json_body if json_body is not None else {}
    r.text = str(json_body)
    return r


class TestPowerBIClientList:
    """Listado de workspaces, datasets y reports."""

    def test_list_workspaces_parses_value(self) -> None:
        client = _make_client()
        body = {"value": [{"id": "w1", "name": "Workspace 1"}]}
        with patch("requests.request", return_value=_resp(200, body)):
            workspaces = client.list_workspaces()
        assert workspaces == [{"id": "w1", "name": "Workspace 1"}]

    def test_list_datasets_personal_path(self) -> None:
        client = _make_client()
        body = {"value": [{"id": "d1", "name": "Sales"}]}
        with patch("requests.request", return_value=_resp(200, body)) as mock_req:
            datasets = client.list_datasets()
        assert datasets[0]["name"] == "Sales"
        # Sin workspace_id, la ruta es /datasets.
        assert mock_req.call_args.args[1].endswith("/datasets")

    def test_list_datasets_workspace_path(self) -> None:
        client = _make_client()
        with patch("requests.request", return_value=_resp(200, {"value": []})) as mock_req:
            client.list_datasets(workspace_id="ws-123")
        assert "/groups/ws-123/datasets" in mock_req.call_args.args[1]

    def test_list_reports(self) -> None:
        client = _make_client()
        body = {"value": [{"id": "r1", "name": "Report 1"}]}
        with patch("requests.request", return_value=_resp(200, body)):
            reports = client.list_reports()
        assert reports[0]["id"] == "r1"


class TestPowerBIClientDax:
    """Ejecución de consultas DAX y refrescos."""

    def test_execute_dax_parses_rows(self) -> None:
        client = _make_client()
        body = {
            "results": [
                {"tables": [{"rows": [{"Sales": 1000}, {"Sales": 1200}]}]}
            ]
        }
        with patch("requests.request", return_value=_resp(200, body)):
            result = client.execute_dax("ds-1", "EVALUATE 'Sales'")
        assert result["row_count"] == 2
        assert result["rows"][0]["Sales"] == 1000

    def test_refresh_dataset(self) -> None:
        client = _make_client()
        with patch("requests.request", return_value=_resp(200, {})):
            result = client.refresh_dataset("ds-1")
        assert result["refresh_requested"] is True
        assert result["dataset_id"] == "ds-1"


class TestPowerBIClientErrors:
    """Manejo de errores HTTP."""

    def test_500_raises_api_error(self) -> None:
        client = _make_client()
        with patch("requests.request", return_value=_resp(500, {"error": "boom"})), \
                pytest.raises(PowerBIAPIError):
            client.list_workspaces()

    def test_429_rate_limit_raises_api_error(self) -> None:
        client = _make_client()
        with patch("requests.request", return_value=_resp(429, {"error": "throttled"})), \
                pytest.raises(PowerBIAPIError):
            client.list_datasets()

    def test_401_retries_with_fresh_token(self) -> None:
        client = _make_client()
        # Primera respuesta 401, segunda 200: el cliente reintenta una vez.
        responses = [_resp(401, {}), _resp(200, {"value": [{"id": "w1"}]})]
        with patch("requests.request", side_effect=responses):
            workspaces = client.list_workspaces()
        assert workspaces == [{"id": "w1"}]
        # Tras un 401 debe pedir un token nuevo (segunda llamada a get_token).
        assert client.auth.get_token.call_count >= 2

    def test_error_message_does_not_leak_token(self) -> None:
        client = _make_client()
        with patch("requests.request", return_value=_resp(403, {"error": "denied"})), \
                pytest.raises(PowerBIAPIError) as exc_info:
            client.list_workspaces()
        assert "fake_token" not in str(exc_info.value)


class TestPowerBIClientToken:
    """Adquisición y cacheo del token."""

    def test_token_acquired_lazily_and_cached(self) -> None:
        client = _make_client()
        with patch("requests.request", return_value=_resp(200, {"value": []})):
            client.list_workspaces()
            client.list_datasets()
        # El token se obtiene una vez y se reutiliza entre llamadas.
        assert client.auth.get_token.call_count == 1

    def test_client_uses_injected_auth(self) -> None:
        auth = MagicMock()
        auth.get_token.return_value = "tok"
        client = PowerBIClient(settings=Settings(), auth=auth)
        assert client.auth is auth
