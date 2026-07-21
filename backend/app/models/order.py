"""Модель Order — заявки на согласование документов ОРД, по п. 3.6 ТЗ.
type переиспользует DocumentTemplateType (тот же набор значений и тот же
enum-тип Postgres document_template_type, что и у DocumentTemplate.type).
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.document_template import DocumentTemplateType


class OrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    REJECTED = "rejected"

if TYPE_CHECKING:
    from app.models.document_template import DocumentTemplate
    from app.models.user import User

class Order(Base):
    __tablename__ = "order"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    type: Mapped[DocumentTemplateType] = mapped_column(
        Enum(
            DocumentTemplateType,
            name="document_template_type",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        index=True,
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_template.id"), nullable=False
    )
    template: Mapped["DocumentTemplate"] = relationship()

    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=OrderStatus.DRAFT,
        index=True,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False, index=True
    )
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=True
    )
    approver: Mapped["User | None"] = relationship(foreign_keys=[approver_id])

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    def __repr__(self) -> str:
        return f"<Order id={self.id} type={self.type} status={self.status}>"
