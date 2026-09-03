"""Тесты monitoring_service — на тестовой БД (фикстура db_session из conftest.py),
без Celery/FastAPI. См. B11, шаг 3.
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration_log import IntegrationLog
from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource, MonitoringStatus
from app.services import monitoring_service

HOST_OK: dict[str, Any] = {"hostid": "1", "host": "srv-ok", "status": "0", "triggers": []}
HOST_WARNING: dict[str, Any] = {
    "hostid": "2",
    "host": "srv-warn",
    "status": "0",
    "triggers": [{"triggerid": "10", "description": "High CPU", "priority": "2", "value": "1"}],
}
HOST_CRITICAL: dict[str, Any] = {
    "hostid": "3",
    "host": "srv-crit",
    "status": "0",
    "triggers": [{"triggerid": "11", "description": "Disk full", "priority": "4", "value": "1"}],
}
HOST_RESOLVED_TRIGGER: dict[str, Any] = {
    "hostid": "4",
    "host": "srv-resolved",
    "status": "0",
    "triggers": [{"triggerid": "12", "description": "Old issue", "priority": "5", "value": "0"}],
}


def test_health_status_ok_without_active_triggers() -> None:
    assert monitoring_service.health_status_from_triggers([]) == MonitoringHealthStatus.OK


def test_health_status_ignores_resolved_triggers() -> None:
    """value == '0' — триггер разрешён, не должен влиять на статус, даже с высоким priority."""
    status = monitoring_service.health_status_from_triggers(HOST_RESOLVED_TRIGGER["triggers"])
    assert status == MonitoringHealthStatus.OK


def test_health_status_warning_below_threshold() -> None:
    status = monitoring_service.health_status_from_triggers(HOST_WARNING["triggers"])
    assert status == MonitoringHealthStatus.WARNING


def test_health_status_critical_at_threshold_and_above() -> None:
    status = monitoring_service.health_status_from_triggers(HOST_CRITICAL["triggers"])
    assert status == MonitoringHealthStatus.CRITICAL


def test_apply_zabbix_hosts_creates_new_records(db_session: Session) -> None:
    monitoring_service.apply_zabbix_hosts(db_session, [HOST_OK, HOST_CRITICAL])

    rows = db_session.scalars(select(MonitoringStatus)).all()
    assert len(rows) == 2

    critical_row = next(r for r in rows if r.host_identifier == "srv-crit")
    assert critical_row.status == MonitoringHealthStatus.CRITICAL
    assert critical_row.last_value == "Disk full"
    assert critical_row.source == MonitoringSource.ZABBIX


def test_apply_zabbix_hosts_upserts_existing_record(db_session: Session) -> None:
    """Повторный опрос того же хоста не создаёт вторую запись, а обновляет существующую."""
    monitoring_service.apply_zabbix_hosts(db_session, [HOST_OK])
    monitoring_service.apply_zabbix_hosts(db_session, [HOST_CRITICAL | {"host": "srv-ok"}])

    rows = db_session.scalars(
        select(MonitoringStatus).where(MonitoringStatus.host_identifier == "srv-ok")
    ).all()
    assert len(rows) == 1
    assert rows[0].status == MonitoringHealthStatus.CRITICAL


def test_apply_zabbix_hosts_logs_success(db_session: Session) -> None:
    monitoring_service.apply_zabbix_hosts(db_session, [HOST_OK])

    log = db_session.scalar(select(IntegrationLog))
    assert log is not None
    assert log.status_code == 200
    assert log.error_message is None


def test_record_zabbix_failure_logs_without_marking_unknown(db_session: Session) -> None:
    """Промежуточная попытка (retry ещё не исчерпан) — лог есть, но статусы хостов не трогаем."""
    monitoring_service.apply_zabbix_hosts(db_session, [HOST_OK])

    monitoring_service.record_zabbix_failure(db_session, error_message="timeout", mark_unknown=False)

    row = db_session.scalar(select(MonitoringStatus).where(MonitoringStatus.host_identifier == "srv-ok"))
    assert row is not None
    assert row.status == MonitoringHealthStatus.OK  # не изменился


def test_record_zabbix_failure_marks_known_hosts_unknown(db_session: Session) -> None:
    """Retry исчерпан — все ранее известные хосты Zabbix помечаются unknown."""
    monitoring_service.apply_zabbix_hosts(db_session, [HOST_OK, HOST_CRITICAL])

    monitoring_service.record_zabbix_failure(db_session, error_message="Session terminated", mark_unknown=True)

    rows = db_session.scalars(select(MonitoringStatus)).all()
    assert all(r.status == MonitoringHealthStatus.UNKNOWN for r in rows)
