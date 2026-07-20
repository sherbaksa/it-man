"""Модель Ticket — заявки (инциденты/запросы), по п. 3.5 ТЗ.
merged_into_ticket_id — задел под правило слияния дублирующих заявок (п. 6.6 ТЗ),
логика слияния будет реализована позже (не в B02).
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, enum.Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    REJECTED = "rejected"


class TicketSource(str, enum.Enum):
    WEB = "web"
    MAX = "max"
    ZABBIX_AUTO = "zabbix_auto"


class Ticket(Base):
    __tablename__ = "ticket"
    __table_args__ = (
        Index("ix_ticket_status_priority", "status", "priority"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=TicketPriority.MEDIUM,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=TicketStatus.NEW,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=False
    )
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id"), nullable=True, index=True
    )
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset.id"), nullable=True
    )
    asset: Mapped["Asset | None"] = relationship()

    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[TicketSource] = mapped_column(
        Enum(TicketSource, name="ticket_source", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )

    external_op_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    external_espo_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    merged_into_ticket_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ticket.id"), nullable=True
    )
    merged_into_ticket: Mapped["Ticket | None"] = relationship(remote_side=[id])

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} title={self.title!r} status={self.status}>"