"""Сервисный слой для агрегированного дашборда руководства — B13a.
Framework-agnostic, только чтение (без коммитов) — по аналогии с
monitoring_service.get_summary().
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketPriority, TicketStatus

_AVERAGE_RESOLUTION_WINDOW_DAYS = 30


def get_executive_summary(db: Session) -> dict:
    """Возвращает {open_tickets, average_resolution_hours, priority_breakdown}
    для GET /api/dashboard/executive."""

    open_tickets = db.scalar(
        select(func.count()).select_from(Ticket).where(
            Ticket.status.in_([TicketStatus.NEW, TicketStatus.IN_PROGRESS])
        )
    )

    window_start = datetime.now(timezone.utc) - timedelta(days=_AVERAGE_RESOLUTION_WINDOW_DAYS)
    avg_seconds = db.scalar(
        select(func.avg(func.extract("epoch", Ticket.closed_at - Ticket.created_at)))
        .where(
            Ticket.status == TicketStatus.DONE,
            Ticket.closed_at.is_not(None),
            Ticket.closed_at >= window_start,
        )
    )
    average_resolution_hours = round(avg_seconds / 3600, 1) if avg_seconds is not None else 0.0

    priority_rows = db.execute(
        select(Ticket.priority, func.count())
        .where(Ticket.status.notin_([TicketStatus.DONE, TicketStatus.REJECTED]))
        .group_by(Ticket.priority)
    ).all()
    priority_counts = {row[0].value: row[1] for row in priority_rows}

    return {
        "open_tickets": open_tickets or 0,
        "average_resolution_hours": average_resolution_hours,
        "priority_breakdown": {
            "low": priority_counts.get(TicketPriority.LOW.value, 0),
            "medium": priority_counts.get(TicketPriority.MEDIUM.value, 0),
            "high": priority_counts.get(TicketPriority.HIGH.value, 0),
            "critical": priority_counts.get(TicketPriority.CRITICAL.value, 0),
        },
    }
