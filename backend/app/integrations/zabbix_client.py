"""Тонкий клиент Zabbix API (JSON-RPC) — см. TZ п. 6.1.

Авторизация — Authorization: Bearer <token> (Zabbix 7.0+, см. app.core.config.settings).
Клиент только выполняет вызов и возвращает сырые данные или кидает исключение;
апсерт в MonitoringStatus, retry и запись в IntegrationLog — в app.tasks.monitoring_tasks.
"""
from typing import cast

import httpx

from app.core.config import settings


class ZabbixAPIError(Exception):
    """Zabbix вернул JSON-RPC error (например, ошибка авторизации или неверные params)."""


class ZabbixConnectionError(Exception):
    """Сервер Zabbix недоступен (сеть, таймаут, некорректный ответ)."""


def _call(method: str, params: dict) -> list | dict:
    """Единая точка вызова JSON-RPC методов Zabbix API."""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.ZABBIX_API_TOKEN}",
    }

    try:
        response = httpx.post(settings.ZABBIX_URL, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ZabbixConnectionError(f"Zabbix недоступен: {exc}") from exc

    data = response.json()
    if "error" in data:
        raise ZabbixAPIError(data["error"].get("data") or data["error"].get("message"))

    return data["result"]


def get_hosts() -> list[dict]:
    """host.get с триггерами — см. TZ п. 6.1: output + selectTriggers."""
    result = _call(
        "host.get",
        {
            "output": ["hostid", "host", "status"],
            "selectTriggers": ["triggerid", "description", "priority", "value"],
        },
    )
    return cast(list[dict], result)

