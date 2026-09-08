"""Сервисный слой мониторинга (Zabbix) — framework-agnostic, без Celery/FastAPI,
по тому же принципу, что app/services/asset_service.py: коммитит сам (см. create_asset).
Вызывается из app/tasks/monitoring_tasks.py. См. TZ п. 6.1, B11 шаг 3.

B12: добавлена запись в MonitoringStatusHistory (append-only журнал, отдельно от
"текущего снимка" MonitoringStatus) и функции чтения для app/api/monitoring.py.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.integration_log import IntegrationDirection, IntegrationLog, IntegrationSystem
from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource, MonitoringStatus
from app.models.monitoring_status_history import MonitoringStatusHistory

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

    # B12: append-only журнал — пишется на КАЖДЫЙ опрос (не только на смену статуса),
    # см. обоснование в отчёте сессии B12. Глубина хранения регулируется отдельно
    # (settings.MONITORING_HISTORY_DEFAULT_RETENTION_HOURS / history_retention_hours
    # конкретного хоста) и чистится Celery-задачей cleanup_monitoring_history.
    db.add(
        MonitoringStatusHistory(
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


# --- B12: чтение для app/api/monitoring.py ---------------------------------


def list_current_statuses(db: Session) -> list[MonitoringStatus]:
    """Все текущие статусы (снимок MonitoringStatus), с подгруженным asset — под
    GET /api/monitoring/status. Без пагинации/фильтров — см. обоснование в
    schemas/monitoring.py (ожидаемый объём — все хосты организации, не тысячи)."""
    return list(
        db.scalars(
            select(MonitoringStatus).options(selectinload(MonitoringStatus.asset))
        ).all()
    )


def get_host_history(
    db: Session, host_identifier: str, date_from: datetime | None, date_to: datetime | None
) -> list[MonitoringStatusHistory]:
    """История хоста за период из append-only журнала MonitoringStatusHistory,
    отсортирована по времени. Под GET /api/monitoring/status/{host_identifier}/history."""
    stmt = select(MonitoringStatusHistory).where(
        MonitoringStatusHistory.host_identifier == host_identifier
    )
    if date_from is not None:
        stmt = stmt.where(MonitoringStatusHistory.checked_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(MonitoringStatusHistory.checked_at <= date_to)
    stmt = stmt.order_by(MonitoringStatusHistory.checked_at)
    return list(db.scalars(stmt).all())


def get_summary(db: Session) -> dict[str, int]:
    """Агрегат {ok, warning, critical, unknown} по текущему снимку MonitoringStatus
    для GET /api/monitoring/summary (дашборд руководства, п. 4.5 ТЗ)."""
    rows = db.execute(
        select(MonitoringStatus.status, func.count()).group_by(MonitoringStatus.status)
    ).all()
    counts = {row[0].value: row[1] for row in rows}
    return {
        "ok": counts.get(MonitoringHealthStatus.OK.value, 0),
        "warning": counts.get(MonitoringHealthStatus.WARNING.value, 0),
        "critical": counts.get(MonitoringHealthStatus.CRITICAL.value, 0),
        "unknown": counts.get(MonitoringHealthStatus.UNKNOWN.value, 0),
    }


def cleanup_old_history(db: Session) -> int:
    """Удаляет записи MonitoringStatusHistory старше глубины хранения для каждого
    хоста (history_retention_hours конкретного хоста в MonitoringStatus, либо
    settings.MONITORING_HISTORY_DEFAULT_RETENTION_HOURS, если не задано).
    Вызывается периодической Celery-задачей cleanup_monitoring_history (см. B12).
    Возвращает количество удалённых строк — для логирования в задаче."""
    from app.core.config import settings

    now = datetime.now(timezone.utc)
    total_deleted = 0

    # Глубина хранения настраивается per-host, поэтому нельзя одним DELETE
    # почистить всё разом — сначала собираем актуальный порог для каждого хоста.
    retention_by_host: dict[str, int] = {
        row.host_identifier: row.history_retention_hours
        for row in db.scalars(select(MonitoringStatus)).all()
        if row.history_retention_hours is not None
    }

    # Хосты с индивидуальной настройкой — свой порог отсечения
    for host_identifier, retention_hours in retention_by_host.items():
        cutoff = now - timedelta(hours=retention_hours)
        result = db.execute(
            delete(MonitoringStatusHistory).where(
                MonitoringStatusHistory.host_identifier == host_identifier,
                MonitoringStatusHistory.checked_at < cutoff,
            )
        )
        total_deleted += result.rowcount or 0

    # Остальные хосты (без индивидуальной настройки) — глобальный дефолт.
    default_cutoff = now - timedelta(hours=settings.MONITORING_HISTORY_DEFAULT_RETENTION_HOURS)
    stmt = delete(MonitoringStatusHistory).where(
        MonitoringStatusHistory.checked_at < default_cutoff
    )
    if retention_by_host:
        stmt = stmt.where(MonitoringStatusHistory.host_identifier.notin_(retention_by_host.keys()))
    result = db.execute(stmt)
    total_deleted += result.rowcount or 0

    db.commit()
    return total_deleted
