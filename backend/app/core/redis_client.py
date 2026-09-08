"""
Синхронный Redis-клиент для кэширования ответов API (в отличие от Celery,
который использует Redis как брокер задач через settings.REDIS_URL напрямую
в celery_app.py — это два независимых назначения одного и того же Redis-инстанса).

Используется в app/api/monitoring.py (B12, см. TZ п. 4.5) для кэширования
GET /api/monitoring/status на 60 секунд. Неймспейс ключей: "monitoring:status:*"
(зарезервировано в плане сессии — не пересекаться с будущим кэшем EspoCRM в B17).

get_redis() — FastAPI-зависимость по аналогии с get_db() из app/core/database.py.
Клиент создаётся один раз на процесс (connection pool внутри redis-py сам
переиспользует соединения), а не на каждый запрос.
"""
import redis

from app.core.config import settings

_redis_client: redis.Redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> redis.Redis:
    """FastAPI-зависимость: возвращает разделяемый клиент Redis."""
    return _redis_client
