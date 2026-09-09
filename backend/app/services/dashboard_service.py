"""Сервисный слой для агрегированного дашборда руководства — B13a.
Framework-agnostic, только чтение (без коммитов) — по аналогии с
monitoring_service.get_summary().
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ticket import Ticket, TicketPriority, TicketStatus

_AVERAGE_RESOLUTION_WINDOW_DAYS = 30
_TREND_WINDOW_DAYS = 7


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
        "ticket_trend": _get_ticket_trend(db),
    }

def _get_ticket_trend(db: Session) -> list[dict]:
    """7 точек «Динамика заявок» (F06) по календарным дням в
    settings.DEFAULT_TIMEZONE (B13b) — не UTC. Достаёт из БД только колонки
    created_at/closed_at (не полные заявки), группировка по локальной дате —
    в Python, т.к. конвертация часового пояса на уровне SQL для Postgres
    менее прозрачна, чем zoneinfo."""
    tz = ZoneInfo(settings.DEFAULT_TIMEZONE)
    today_local = datetime.now(tz).date()
    start_local = today_local - timedelta(days=_TREND_WINDOW_DAYS - 1)

    # Границы окна в UTC для запроса — с часовым запасом на случай сдвига
    # суток часовым поясом (например, начало локального дня во Владивостоке
    # UTC+10 — это ещё предыдущий день по UTC).
    window_start_utc = datetime.combine(start_local, time.min, tzinfo=tz).astimezone(timezone.utc) - timedelta(hours=1)
    window_end_utc = datetime.now(timezone.utc) + timedelta(hours=1)

    created_at_values = db.scalars(
        select(Ticket.created_at).where(
            Ticket.created_at >= window_start_utc, Ticket.created_at <= window_end_utc
        )
    ).all()
    closed_at_values = db.scalars(
        select(Ticket.closed_at).where(
            Ticket.closed_at.is_not(None),
            Ticket.closed_at >= window_start_utc,
            Ticket.closed_at <= window_end_utc,
        )
    ).all()

    created_counts: dict[date, int] = defaultdict(int)
    for created_at in created_at_values:
        local_date = created_at.astimezone(tz).date()
        if start_local <= local_date <= today_local:
            created_counts[local_date] += 1

    closed_counts: dict[date, int] = defaultdict(int)
    for closed_at in closed_at_values:
        if closed_at is None:  # для mypy — SQL уже отфильтровал None, это просто type narrowing
            continue
        local_date = closed_at.astimezone(tz).date()
        if start_local <= local_date <= today_local:
            closed_counts[local_date] += 1

    return [
        {
            "date": (start_local + timedelta(days=offset)).isoformat(),
            "created": created_counts.get(start_local + timedelta(days=offset), 0),
            "closed": closed_counts.get(start_local + timedelta(days=offset), 0),
        }
        for offset in range(_TREND_WINDOW_DAYS)
    ]
