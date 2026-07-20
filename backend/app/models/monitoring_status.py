"""Модель MonitoringStatus — текущий статус мониторинга хоста, по п. 3.8 ТЗ.
Уникальный индекс (host_identifier, source) — под upsert при синхронизации
с Zabbix/Kaspersky (см. B11-B13, B19-B20): запись обновляется по этому ключу,
а не создаётся заново при каждом опросе.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MonitoringHealthStatus(str, enum.Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MonitoringSource(str, enum.Enum):
    ZABBIX = "zabbix"
    KASPERSKY = "kaspersky"


class MonitoringStatus(Base):
    __tablename__ = "monitoring_status"
    __table_args__ = (
        Index("ux_monitoring_status_host_source", "host_identifier", "source", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id"), nullable=True
    )
    asset: Mapped["Asset | None"] = relationship()

    host_identifier: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[MonitoringHealthStatus] = mapped_column(
        Enum(
            MonitoringHealthStatus,
            name="monitoring_health_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )

    last_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[MonitoringSource] = mapped_column(
        Enum(MonitoringSource, name="monitoring_source", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<MonitoringStatus id={self.id} host={self.host_identifier!r} status={self.status}>"