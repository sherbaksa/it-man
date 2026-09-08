"""Модель MonitoringStatusHistory — append-only журнал изменений статуса хоста.

В отличие от MonitoringStatus (текущий снимок — одна строка на host_identifier+source,
перезаписывается при каждом опросе, см. B02/B11), сюда пишется новая строка на
КАЖДЫЙ опрос (не только на смену статуса) — обоснование объёма данных см. в
отчёте сессии B12: при небольшом числе хостов в организации нагрузка на БД
незначительна, а график истории получается непрерывным.

Глубина хранения регулируется отдельно (settings.MONITORING_HISTORY_DEFAULT_RETENTION_HOURS
по умолчанию, либо MonitoringStatus.history_retention_hours для конкретного хоста) и
чистится периодической Celery-задачей cleanup_monitoring_history (см. app/tasks/monitoring_tasks.py).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource


class MonitoringStatusHistory(Base):
    __tablename__ = "monitoring_status_history"
    __table_args__ = (
        # Основной паттерн выборки — "история конкретного хоста за период",
        # см. GET /api/monitoring/status/{host_identifier}/history
        Index("ix_monitoring_status_history_host_checked", "host_identifier", "checked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    host_identifier: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[MonitoringHealthStatus] = mapped_column(
        Enum(
            MonitoringHealthStatus,
            name="monitoring_health_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            create_type=False,  # тип уже создан для monitoring_status в B02
        ),
        nullable=False,
    )

    last_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[MonitoringSource] = mapped_column(
        Enum(
            MonitoringSource,
            name="monitoring_source",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            create_type=False,  # тип уже создан для monitoring_status в B02
        ),
        nullable=False,
    )

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return (
            f"<MonitoringStatusHistory host={self.host_identifier!r} "
            f"status={self.status} checked_at={self.checked_at}>"
        )
