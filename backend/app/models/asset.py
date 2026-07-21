"""Модель Asset — оборудование, по п. 3.2 ТЗ.
Бизнес-правила (реализуются в сервисном слое, не здесь):
- нельзя перевести в written_off при наличии открытых заявок (см. B06-B08);
- изменение status/location создаёт запись Movement (см. B02, модель Movement).
"""
import enum
import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetStatus(str, enum.Enum):
    IN_USE = "in_use"
    REPAIR = "repair"
    WRITTEN_OFF = "written_off"
    IN_STOCK = "in_stock"

if TYPE_CHECKING:
    from app.models.equipment_type import EquipmentType
    from app.models.user import User

class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inventory_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment_type.id"), nullable=False
    )
    type: Mapped["EquipmentType"] = relationship()

    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=AssetStatus.IN_STOCK,
        index=True,
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=True
    )
    responsible_user: Mapped["User | None"] = relationship()

    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} inventory_number={self.inventory_number!r} status={self.status}>"
