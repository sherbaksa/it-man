"""Модель Movement — история перемещений оборудования, по п. 3.3 ТЗ.
Запись создаётся автоматически в сервисном слое при изменении Asset.status/location
(см. B02 → B07, asset_service.update_asset()).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Movement(Base):
    __tablename__ = "movement"
    __table_args__ = (
        Index("ix_movement_asset_id_moved_at", "asset_id", "moved_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id"), nullable=False
    )
    asset: Mapped["Asset"] = relationship()

    from_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_location: Mapped[str] = mapped_column(String(255), nullable=False)

    initiator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    initiator: Mapped["User"] = relationship()

    moved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Movement id={self.id} asset_id={self.asset_id} to_location={self.to_location!r}>"