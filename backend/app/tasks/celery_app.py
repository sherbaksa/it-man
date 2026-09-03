"""Celery-приложение платформы. Broker/backend — Redis (см. app.core.config.REDIS_URL).

beat_schedule по п. 6.1 ТЗ: периодический опрос Zabbix каждые 5 минут.
Задача poll_zabbix регистрируется в app.tasks.monitoring_tasks (B11, шаг 3).
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "it_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "poll-zabbix-every-5-minutes": {
            "task": "app.tasks.monitoring_tasks.poll_zabbix",
            "schedule": crontab(minute="*/5"),
        },
    },
)

# Явный импорт модулей с задачами при старте worker'а (см. B11 — autodiscover_tasks
# рассчитан на Django-конвенцию "<package>.tasks" и не подходит для нашей структуры,
# где app/tasks/ сам является пакетом с несколькими модулями задач).
celery_app.conf.imports = ("app.tasks.monitoring_tasks",)
