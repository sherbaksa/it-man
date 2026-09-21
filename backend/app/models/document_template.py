"""Модель DocumentTemplate — шаблоны документов ОРД, по п. 3.7 ТЗ.
min_approver_role переиспользует UserRole из user.py (не заводим отдельный enum-тип
в БД под ту же смысловую сущность — роль пользователя).

field_schema — JSON-массив описаний полей (не объект): порядок полей в форме
имеет значение (F07 рендерит их именно в этом порядке), а формат
{key, label, type, required, placeholder?, options?, defaultValue?} на каждый
элемент — тот же, что уже реализован на фронте Dev2 (frontend/src/types/order.ts,
OrderFieldDefinition), чтобы при переходе с мока на реальный API форма не
менялась. Ранее (сессия B02) поле было типизировано как dict и содержало {}
(заглушка) — исправлено в сессии B15 вместе с заполнением реальных шаблонов.
"""
import enum
import uuid

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import UserRole


class DocumentTemplateType(str, enum.Enum):
    PURCHASE_REQUEST = "purchase_request"
    WRITE_OFF_ACT = "write_off_act"
    WORK_ORDER = "work_order"


class DocumentTemplate(Base):
    __tablename__ = "document_template"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    type: Mapped[DocumentTemplateType] = mapped_column(
        Enum(
            DocumentTemplateType,
            name="document_template_type",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    field_schema: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)

    min_approver_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DocumentTemplate id={self.id} name={self.name!r} type={self.type}>"
