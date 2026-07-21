"""Модель OrderHistory — история версий заявки Order (снапшоты fields при каждом изменении)."""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User

class OrderHistory(Base):
    __tablename__ = "order_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order.id"), nullable=False, index=True
    )
    order: Mapped["Order"] = relationship()

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)

    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    changed_by_user: Mapped["User"] = relationship()

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<OrderHistory id={self.id} order_id={self.order_id} version={self.version}>"
