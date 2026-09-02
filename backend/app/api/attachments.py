"""
API-роуты для Attachment (вложения к заявкам) — сессия B10a.

POST /api/tickets/{ticket_id}/attachments — загрузка файла (multipart/form-data),
    валидация MIME-whitelist и лимита размера (MAX_ATTACHMENT_SIZE_MB).
GET /api/tickets/{ticket_id}/attachments — список вложений с presigned-ссылками.
DELETE /api/attachments/{id} — удаление (права см. attachment_service.check_delete_permission).

Доступ: Engineer+ (Engineer, IT-Head, Admin) — по аналогии с /api/tickets.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.storage import get_presigned_url
from app.models.attachment import Attachment
from app.models.user import User, UserRole
from app.schemas.attachment import AttachmentRead
from app.services import attachment_service, ticket_service
from app.services.attachment_service import (
    AttachmentPermissionError,
    AttachmentTooLargeError,
    AttachmentTypeNotAllowedError,
)

router = APIRouter(
    tags=["attachments"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


def _to_read(attachment: Attachment) -> AttachmentRead:
    """Собирает AttachmentRead вручную — download_url не поле модели,
    генерируется на лету (см. schemas/attachment.py)."""
    return AttachmentRead(
        id=attachment.id,
        file_name=attachment.file_name,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        download_url=get_presigned_url(attachment.storage_key),
        created_at=attachment.created_at,
    )


@router.post(
    "/api/tickets/{ticket_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    ticket_id: uuid.UUID,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentRead:
    ticket = ticket_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")

    file_bytes = await file.read()

    try:
        attachment_service.validate_upload(
            file_name=file.filename or "",
            content_type=file.content_type or "",
            size_bytes=len(file_bytes),
            max_size_mb=settings.MAX_ATTACHMENT_SIZE_MB,
        )
    except (AttachmentTypeNotAllowedError, AttachmentTooLargeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    attachment = attachment_service.create_attachment(
        db,
        ticket_id=ticket_id,
        file_name=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
        uploaded_by=current_user.id,
    )
    return _to_read(attachment)


@router.get("/api/tickets/{ticket_id}/attachments", response_model=list[AttachmentRead])
def get_ticket_attachments(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[AttachmentRead]:
    ticket = ticket_service.get_ticket(db, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")

    attachments = attachment_service.list_attachments(db, ticket_id)
    return [_to_read(item) for item in attachments]


@router.delete("/api/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    attachment = attachment_service.get_attachment(db, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вложение не найдено")

    try:
        attachment_service.check_delete_permission(attachment, current_user)
    except AttachmentPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    attachment_service.delete_attachment(db, attachment)
