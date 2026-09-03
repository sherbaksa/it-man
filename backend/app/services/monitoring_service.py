"""Сервисный слой мониторинга (Zabbix) — framework-agnostic, без Celery/FastAPI,
по тому же принципу, что app/services/asset_service.py: коммитит сам (см. create_asset).
Вызывается из app/tasks/monitoring_tasks.py. См. TZ п. 6.1, B11 шаг 3.
"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.integration_log import IntegrationDirection, IntegrationLog, IntegrationSystem
from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource, MonitoringStatus

# priority >= 3 (high/disaster) -> critical, иначе (average/warning) -> warning,
# нет активных (value == "1") триггеров -> ok. Согласовано в B11.
_CRITICAL_PRIORITY_THRESHOLD = 3


def worst_active_trigger(triggers: list[dict]) -> dict | None:
    """Триггер с максимальным priority среди активных (value == '1'), либо None."""
    active = [t for t in triggers if t.get("value") == "1"]
    if not active:
        return None
    return max(active, key=lambda t: int(t["priority"]))


def health_status_from_triggers(triggers: list[dict]) -> MonitoringHealthStatus:
    worst = worst_active_trigger(triggers)
    if worst is None:
        return MonitoringHealthStatus.OK
    if int(worst["priority"]) >= _CRITICAL_PRIORITY_THRESHOLD:
        return MonitoringHealthStatus.CRITICAL
    return MonitoringHealthStatus.WARNING


def _upsert_monitoring_status(
    db: Session, *, host_identifier: str, status: MonitoringHealthStatus, last_value: str | None
) -> None:
    existing = db.scalar(
        select(MonitoringStatus).where(
            MonitoringStatus.host_identifier == host_identifier,
            MonitoringStatus.source == MonitoringSource.ZABBIX,
        )
    )
    now = datetime.now(timezone.utc)
    if existing:
        existing.status = status
        existing.last_value = last_value
        existing.checked_at = now
    else:
        db.add(
            MonitoringStatus(
                host_identifier=host_identifier,
                source=MonitoringSource.ZABBIX,
                status=status,
                last_value=last_value,
                checked_at=now,
            )
        )


def apply_zabbix_hosts(db: Session, hosts: list[dict]) -> None:
    """Апсертит MonitoringStatus по каждому хосту из ответа host.get, логирует успех, коммитит."""
    for host in hosts:
        triggers = host.get("triggers", [])
        status = health_status_from_triggers(triggers)
        worst = worst_active_trigger(triggers)
        last_value = worst["description"] if worst else None
        _upsert_monitoring_status(db, host_identifier=host["host"], status=status, last_value=last_value)

    db.add(
        IntegrationLog(
            system=IntegrationSystem.ZABBIX,
            direction=IntegrationDirection.INBOUND,
            endpoint="host.get",
            status_code=200,
            error_message=None,
        )
    )
    db.commit()


def record_zabbix_failure(db: Session, *, error_message: str, mark_unknown: bool) -> None:
    """Логирует неудачный опрос; при mark_unknown=True (retry исчерпан либо ошибка не транзиентная)
    дополнительно помечает все ранее известные хосты Zabbix как unknown. Коммитит сам."""
    db.add(
        IntegrationLog(
            system=IntegrationSystem.ZABBIX,
            direction=IntegrationDirection.INBOUND,
            endpoint="host.get",
            status_code=None,
            error_message=error_message,
        )
    )
    if mark_unknown:
        db.execute(
            update(MonitoringStatus)
            .where(MonitoringStatus.source == MonitoringSource.ZABBIX)
            .values(status=MonitoringHealthStatus.UNKNOWN, checked_at=datetime.now(timezone.utc))
        )
    db.commit()
