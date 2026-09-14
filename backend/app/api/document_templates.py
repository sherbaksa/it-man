"""
API-роут для DocumentTemplate (справочник шаблонов документов ОРД) — сессия
B14a, введена по факту сверки контракта с Dev2 (не было в исходном плане B14).

GET /api/document-templates — список всех шаблонов, отсортированный по name.
Нужен фронтенду (F07) для формы создания Order: выбор шаблона + получение
field_schema для динамической генерации полей.

Доступ: Engineer, IT-Head, Admin — по аналогии с equipment-types (B09a).
Executive не создаёт Order (раздел 8 ТЗ: "создание — Engineer/IT-Head"),
поэтому этот справочник ему не нужен — в отличие от роутера orders.py,
где Executive присутствует ради согласования.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.document_template import DocumentTemplate
from app.models.user import UserRole
from app.schemas.document_template import DocumentTemplateRead

router = APIRouter(
    prefix="/api/document-templates",
    tags=["document-templates"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


@router.get("", response_model=list[DocumentTemplateRead])
def get_document_templates(db: Session = Depends(get_db)) -> list[DocumentTemplate]:
    stmt = select(DocumentTemplate).order_by(DocumentTemplate.name)
    return list(db.scalars(stmt).all())
