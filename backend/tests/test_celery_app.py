"""Smoke tests for the Celery worker application."""

from app.tasks.celery_app import celery_app


def test_celery_app_uses_redis_by_default() -> None:
    assert celery_app.conf.broker_url == "redis://redis:6379/0"
    assert celery_app.conf.result_backend == "redis://redis:6379/1"
