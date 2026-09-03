"""Тесты zabbix_client на моках pytest-httpx (без реального Zabbix — см. B11, шаг 2)."""
import httpx
import pytest
from pytest_httpx import HTTPXMock

from app.core.config import settings
from app.integrations.zabbix_client import (
    ZabbixAPIError,
    ZabbixConnectionError,
    get_hosts,
)


def test_get_hosts_success(httpx_mock: HTTPXMock) -> None:
    """host.get возвращает список хостов при успешном ответе Zabbix."""
    httpx_mock.add_response(
        url=settings.ZABBIX_URL,
        json={
            "jsonrpc": "2.0",
            "result": [{"hostid": "1", "host": "srv-01", "status": "0"}],
            "id": 1,
        },
    )

    result = get_hosts()

    assert result == [{"hostid": "1", "host": "srv-01", "status": "0"}]


def test_get_hosts_sends_bearer_token(httpx_mock: HTTPXMock) -> None:
    """Убеждаемся, что токен реально уходит в заголовке Authorization: Bearer."""
    httpx_mock.add_response(
        url=settings.ZABBIX_URL,
        json={"jsonrpc": "2.0", "result": [], "id": 1},
    )

    get_hosts()

    request = httpx_mock.get_requests()[0]
    assert request.headers["authorization"] == f"Bearer {settings.ZABBIX_API_TOKEN}"


def test_get_hosts_api_error(httpx_mock: HTTPXMock) -> None:
    """JSON-RPC error (например, протухший токен) -> ZabbixAPIError."""
    httpx_mock.add_response(
        url=settings.ZABBIX_URL,
        json={
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid params.", "data": "Session terminated, re-login, please."},
            "id": 1,
        },
    )

    with pytest.raises(ZabbixAPIError, match="Session terminated"):
        get_hosts()


def test_get_hosts_connection_error(httpx_mock: HTTPXMock) -> None:
    """Сервер Zabbix недоступен (сеть/таймаут) -> ZabbixConnectionError."""
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))

    with pytest.raises(ZabbixConnectionError):
        get_hosts()
