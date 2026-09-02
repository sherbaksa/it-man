"""
Клиент MinIO (S3-совместимое хранилище) для вложений к заявкам — сессия B10a.

MINIO_ENDPOINT — внутренний адрес (docker-сеть), используется backend'ом для
    всех операций с MinIO (put/presign).
MINIO_PUBLIC_ENDPOINT — внешний адрес, доступный из браузера пользователя;
    используется ТОЛЬКО для подмены host'а в уже сгенерированной presigned-ссылке,
    иначе браузер получит ссылку на недоступный ему "minio:9000" (см. риски
    Посессионный_план_IT_Platform.md, сессия B10a).
"""
from __future__ import annotations

import io
from datetime import timedelta
from urllib.parse import urlsplit

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client: Minio | None = None
_presign_client: Minio | None = None


def get_client() -> Minio:
    """Ленивая инициализация клиента MinIO (переиспользуется между вызовами)."""
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_SECURE,
        )
    return _client

def _get_presign_client() -> Minio:
    """Отдельный клиент, сконфигурированный на MINIO_PUBLIC_ENDPOINT — используется
    ТОЛЬКО для генерации presigned-ссылок. Подпись AWS SigV4 включает заголовок Host
    (см. X-Amz-SignedHeaders=host), поэтому подменять host в уже подписанной ссылке
    нельзя — сигнатура перестаёт совпадать. presign — чисто локальное вычисление,
    реального сетевого похода на публичный endpoint при этом не требуется."""
    global _presign_client
    if _presign_client is None:
        parsed = urlsplit(
            settings.MINIO_PUBLIC_ENDPOINT
            if "://" in settings.MINIO_PUBLIC_ENDPOINT
            else f"http://{settings.MINIO_PUBLIC_ENDPOINT}"
        )
        _presign_client = Minio(
            parsed.netloc,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=(parsed.scheme == "https"),
            region="us-east-1",  # MinIO по умолчанию; явный region убирает
            # сетевой запрос _get_region() внутри presigned_get_object() — без
            # этого SDK пытался бы достучаться до MINIO_PUBLIC_ENDPOINT изнутри
            # backend-контейнера, где этот адрес недоступен (см. traceback B10a)
        )
    return _presign_client

def ensure_bucket_exists() -> None:
    """Idempotent-создание бакета для вложений заявок. Вызывается при старте приложения."""
    client = get_client()
    if not client.bucket_exists(settings.MINIO_BUCKET_TICKETS):
        client.make_bucket(settings.MINIO_BUCKET_TICKETS)


def upload_file(file_bytes: bytes, key: str, content_type: str) -> str:
    """Загружает файл в бакет вложений заявок, возвращает storage_key (= key)."""
    client = get_client()
    client.put_object(
        settings.MINIO_BUCKET_TICKETS,
        key,
        data=io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )
    return key


def get_presigned_url(storage_key: str, expires_seconds: int = 300) -> str:
    """Генерирует presigned-ссылку на скачивание через клиент, сконфигурированный
    на публичный endpoint (см. _get_presign_client) — ссылка сразу подписана
    правильным host'ом и открывается из браузера пользователя."""
    client = _get_presign_client()
    return client.presigned_get_object(
        settings.MINIO_BUCKET_TICKETS,
        storage_key,
        expires=timedelta(seconds=expires_seconds),
    )


def delete_file(storage_key: str) -> None:
    """Удаляет объект из MinIO. Не бросает исключение, если объект уже отсутствует."""
    client = get_client()
    try:
        client.remove_object(settings.MINIO_BUCKET_TICKETS, storage_key)
    except S3Error as exc:
        if exc.code != "NoSuchKey":
            raise
