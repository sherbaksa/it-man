"""Модель IntegrationLog — журнал запросов к внешним системам, по п. 3.9 ТЗ."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IntegrationSystem(str, enum.Enum):
    ZABBIX = "zabbix"
    ESPOCRM = "espocrm"
    OPENPROJECT = "openproject"
    KASPERSKY = "kaspersky"
    N8N = "n8n"


class IntegrationDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class IntegrationLog(Base):
    __tablename__ = "integration_log"
    __table_args__ = (
        Index("ix_integration_log_system_created_at", "system", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    system: Mapped[IntegrationSystem] = mapped_column(
        Enum(IntegrationSystem, name="integration_system", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    direction: Mapped[IntegrationDirection] = mapped_column(
        Enum(IntegrationDirection, name="integration_direction", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<IntegrationLog id={self.id} system={self.system} direction={self.direction}>"