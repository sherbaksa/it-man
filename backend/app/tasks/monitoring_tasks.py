"""Celery-задача периодического опроса Zabbix (см. TZ п. 6.1, B11 шаг 3).

Раз в 5 минут (beat_schedule в celery_app.py) забирает хосты через
zabbix_client.get_hosts() и передаёт в monitoring_service — сама задача
только оркестрирует retry, вся бизнес-логика и коммиты — в
app/services/monitoring_service.py (коммитит сама, как asset_service.create_asset).

Алерт администратору через MAX после исчерпания retry — вне объёма B11,
канал не спроектирован (см. риски B11).
"""
from app.core.database import SessionLocal
from app.integrations.zabbix_client import ZabbixAPIError, ZabbixConnectionError, get_hosts
from app.services import monitoring_service
from app.tasks.celery_app import celery_app

RETRY_COUNTDOWNS = [60, 120, 240]  # 1м, 2м, 4м — см. TZ п. 6.1


@celery_app.task(bind=True, max_retries=len(RETRY_COUNTDOWNS))
def poll_zabbix(self) -> None:
    db = SessionLocal()
    try:
        try:
            hosts = get_hosts()
        except ZabbixConnectionError as exc:
            retries_exhausted = self.request.retries >= len(RETRY_COUNTDOWNS)
            monitoring_service.record_zabbix_failure(
                db, error_message=str(exc), mark_unknown=retries_exhausted
            )
            if retries_exhausted:
                return
            raise self.retry(exc=exc, countdown=RETRY_COUNTDOWNS[self.request.retries]) from exc
        except ZabbixAPIError as exc:
            # Не транзиентная ошибка (например, протух токен) — ретраить бессмысленно
            monitoring_service.record_zabbix_failure(db, error_message=str(exc), mark_unknown=True)
            return

        monitoring_service.apply_zabbix_hosts(db, hosts)
    finally:
        db.close()
