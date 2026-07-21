"""Модель Repair — учёт ремонтов оборудования, по п. 3.4 ТЗ.
executor_espocrm_id пока nullable — привязка к EspoCRM появится в сессии B17.
"""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RepairStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"

if TYPE_CHECKING:
    from app.models.asset import Asset

class Repair(Base):
    __tablename__ = "repair"
    __table_args__ = (
        Index("ix_repair_asset_id_status", "asset_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id"), nullable=False
    )
    asset: Mapped["Asset"] = relationship()

    repair_type: Mapped[str] = mapped_column(String(150), nullable=False)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    executor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executor_espocrm_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[RepairStatus] = mapped_column(
        Enum(RepairStatus, name="repair_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=RepairStatus.PLANNED,
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Repair id={self.id} asset_id={self.asset_id} status={self.status}>"
