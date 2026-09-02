"""
Pydantic-схема вложений к заявкам (Attachment) — сессия B10a.

AttachmentRead — тело ответа для GET /api/tickets/{id}/attachments и для
    объекта, возвращаемого после POST-загрузки. download_url — presigned-ссылка
    MinIO, генерируется на лету при каждом ответе (не хранится в модели/БД,
    т.к. недолговечна — см. app/core/storage.get_presigned_url).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    content_type: str
    size_bytes: int
    download_url: str
    created_at: datetime
    can_delete: bool
