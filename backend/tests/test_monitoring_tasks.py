"""Тесты monitoring_tasks — retry-оркестрация на моках (get_hosts, monitoring_service, SessionLocal).
Персистентность уже покрыта test_monitoring_service.py; здесь только оркестрация и retry. См. B11, шаг 3.
"""
from unittest.mock import MagicMock

import pytest
from celery.exceptions import Retry

from app.integrations.zabbix_client import ZabbixAPIError, ZabbixConnectionError
from app.tasks import monitoring_tasks


@pytest.fixture(autouse=True)
def eager_celery():
    """Выполняет задачу синхронно, без реального брокера/воркера."""
    monitoring_tasks.celery_app.conf.task_always_eager = True
    monitoring_tasks.celery_app.conf.task_eager_propagates = True
    yield
    monitoring_tasks.celery_app.conf.task_always_eager = False
    monitoring_tasks.celery_app.conf.task_eager_propagates = False


@pytest.fixture()
def fake_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Подменяем SessionLocal в monitoring_tasks — retry-тесты не должны трогать реальную БД."""
    session = MagicMock()
    monkeypatch.setattr(monitoring_tasks, "SessionLocal", lambda: session)
    return session


def test_poll_zabbix_success_calls_apply_zabbix_hosts(
    monkeypatch: pytest.MonkeyPatch, fake_session: MagicMock
) -> None:
    hosts = [{"host": "srv-1", "triggers": []}]
    monkeypatch.setattr(monitoring_tasks, "get_hosts", lambda: hosts)
    apply_mock = MagicMock()
    monkeypatch.setattr(monitoring_tasks.monitoring_service, "apply_zabbix_hosts", apply_mock)

    monitoring_tasks.poll_zabbix.apply()

    apply_mock.assert_called_once_with(fake_session, hosts)
    fake_session.close.assert_called_once()


def test_poll_zabbix_api_error_marks_unknown_without_retry(
    monkeypatch: pytest.MonkeyPatch, fake_session: MagicMock
) -> None:
    def _raise() -> None:
        raise ZabbixAPIError("Session terminated")

    monkeypatch.setattr(monitoring_tasks, "get_hosts", _raise)
    record_mock = MagicMock()
    monkeypatch.setattr(monitoring_tasks.monitoring_service, "record_zabbix_failure", record_mock)

    monitoring_tasks.poll_zabbix.apply()

    record_mock.assert_called_once_with(fake_session, error_message="Session terminated", mark_unknown=True)


def test_poll_zabbix_connection_error_triggers_retry(
    monkeypatch: pytest.MonkeyPatch, fake_session: MagicMock
) -> None:
    """Первая неудачная попытка — лог без mark_unknown, Celery поднимает Retry.
    В реальном воркере Retry перекладывает задачу в очередь с задержкой; eager-режим
    сам цикл ретраев не воспроизводит (подтверждено эмпирически) — здесь проверяем
    только то, что происходит до и в момент поднятия Retry.
    """
    monkeypatch.setattr(monitoring_tasks, "get_hosts", MagicMock(side_effect=ZabbixConnectionError("timeout")))
    record_mock = MagicMock()
    monkeypatch.setattr(monitoring_tasks.monitoring_service, "record_zabbix_failure", record_mock)

    with pytest.raises(Retry):
        monitoring_tasks.poll_zabbix.apply(throw=True)

    record_mock.assert_called_once_with(fake_session, error_message="timeout", mark_unknown=False)


def test_poll_zabbix_connection_error_marks_unknown_when_retries_exhausted(
    monkeypatch: pytest.MonkeyPatch, fake_session: MagicMock
) -> None:
    """Симулируем последнюю попытку через push_request(retries=...) и вызов .run()
    напрямую — без прогона через реальный retry-цикл Celery, которого eager-режим
    не даёт; проверяем именно ветку self.request.retries >= len(RETRY_COUNTDOWNS).
    """
    monkeypatch.setattr(monitoring_tasks, "get_hosts", MagicMock(side_effect=ZabbixConnectionError("timeout")))
    record_mock = MagicMock()
    monkeypatch.setattr(monitoring_tasks.monitoring_service, "record_zabbix_failure", record_mock)

    monitoring_tasks.poll_zabbix.push_request(retries=len(monitoring_tasks.RETRY_COUNTDOWNS))
    try:
        monitoring_tasks.poll_zabbix.run()
    finally:
        monitoring_tasks.poll_zabbix.pop_request()

    record_mock.assert_called_once_with(fake_session, error_message="timeout", mark_unknown=True)
