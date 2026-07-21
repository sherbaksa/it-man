"""Celery application used by the background worker container."""

import os

from celery import Celery

DEFAULT_BROKER_URL = "redis://redis:6379/0"
DEFAULT_RESULT_BACKEND = "redis://redis:6379/1"

celery_app = Celery(
    "it_platform",
    broker=os.getenv("CELERY_BROKER_URL", DEFAULT_BROKER_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", DEFAULT_RESULT_BACKEND),
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Celery discovers this conventional name when started with
# ``celery -A app.tasks.celery_app worker``.
app = celery_app
