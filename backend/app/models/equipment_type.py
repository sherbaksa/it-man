"""Модель EquipmentType — тип оборудования (справочник: компьютер/принтер/сетевое/прочее)."""
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EquipmentType(Base):
    __tablename__ = "equipment_type"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<EquipmentType id={self.id} name={self.name!r}>"