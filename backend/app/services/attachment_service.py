"""
Сервисный слой для Attachment (вложения к заявкам) — сессия B10a.

Валидация типа/размера файла, взаимодействие с MinIO (app.core.storage) и БД.
Сервисный слой фреймворк-агностичен (кастомные исключения вместо HTTPException,
по аналогии с ticket_service.py).

Права на DELETE: решено по аналогии с правилом Engineer/IT-Head в ticket_service.py
(update_ticket) — Engineer может удалить только вложение, загруженное им самим
(uploaded_by == current_user.id), IT-Head/Admin — любое.
"""
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import storage
from app.models.attachment import Attachment
from app.models.user import User, UserRole

# MIME-whitelist: изображения + pdf + doc/docx, без исполняемых файлов (см. ТЗ раздел 7)
ALLOWED_CONTENT_TYPES: set[str] = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

# Дублирующая проверка по расширению — на случай подделанного Content-Type;
# отклоняем, если расширение не входит в список, даже если content_type прошёл.
ALLOWED_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".doc", ".docx", ".txt",
}


class AttachmentTypeNotAllowedError(Exception):
    """Тип файла (Content-Type или расширение) не входит в whitelist.
    Обрабатывается в api/attachments.py как 422."""


class AttachmentTooLargeError(Exception):
    """Размер файла превышает MAX_ATTACHMENT_SIZE_MB.
    Обрабатывается в api/attachments.py как 422."""


class AttachmentPermissionError(Exception):
    """Пользователь не имеет права удалить вложение.
    Обрабатывается в api/attachments.py как 403."""


def validate_upload(file_name: str, content_type: str, size_bytes: int, max_size_mb: int) -> None:
    """Валидирует тип и размер файла до загрузки в MinIO."""
    extension = Path(file_name).suffix.lower()
    if content_type not in ALLOWED_CONTENT_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise AttachmentTypeNotAllowedError(
            f"Тип файла не разрешён: {content_type} ({extension or 'без расширения'})"
        )
    max_size_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_size_bytes:
        raise AttachmentTooLargeError(f"Размер файла превышает лимит {max_size_mb} МБ")


def create_attachment(
    db: Session,
    *,
    ticket_id: uuid.UUID,
    file_name: str,
    content_type: str,
    file_bytes: bytes,
    uploaded_by: uuid.UUID,
) -> Attachment:
    """Загружает файл в MinIO и создаёт запись Attachment. Валидацию (тип/размер)
    вызывающая сторона должна выполнить заранее через validate_upload()."""
    storage_key = f"tickets/{ticket_id}/{uuid.uuid4()}_{file_name}"
    storage.upload_file(file_bytes, storage_key, content_type)

    attachment = Attachment(
        ticket_id=ticket_id,
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(file_bytes),
        storage_key=storage_key,
        uploaded_by=uploaded_by,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def list_attachments(db: Session, ticket_id: uuid.UUID) -> list[Attachment]:
    """Возвращает все вложения заявки, отсортированные по дате загрузки (новые сверху)."""
    query = (
        select(Attachment)
        .where(Attachment.ticket_id == ticket_id)
        .order_by(Attachment.created_at.desc())
    )
    return list(db.execute(query).scalars().all())


def get_attachment(db: Session, attachment_id: uuid.UUID) -> Attachment | None:
    """Возвращает вложение по id или None, если не найдено."""
    return db.get(Attachment, attachment_id)


def check_delete_permission(attachment: Attachment, current_user: User) -> None:
    """Engineer может удалить только вложение, загруженное им самим;
    IT-Head/Admin — любое."""
    if current_user.role == UserRole.ENGINEER and attachment.uploaded_by != current_user.id:
        raise AttachmentPermissionError("Engineer может удалять только свои собственные вложения")


def delete_attachment(db: Session, attachment: Attachment) -> None:
    """Удаляет файл из MinIO и запись из БД."""
    storage.delete_file(attachment.storage_key)
    db.delete(attachment)
    db.commit()
