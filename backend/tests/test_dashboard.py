"""
Тесты для GET /api/dashboard/executive — сессия B13a (неплановая мини-сессия
после B13, найдена по факту сверки с Dev2 по контракту F06).

Покрывает: доступ (403 для Engineer, 200 для Executive/IT-Head), подсчёт
open_tickets, priority_breakdown, average_resolution_hours (включая случай
"нет закрытых тикетов за 30 дней" -> 0.0, и случай с реальным средним).
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.security import hash_password
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.user import User, UserRole

DASHBOARD_URL = "/api/dashboard/executive"


def _make_ticket(
    db_session, author_id, *, priority: TicketPriority, status: TicketStatus,
    created_at: datetime | None = None, closed_at: datetime | None = None,
) -> Ticket:
    ticket = Ticket(
        title="Тестовая заявка",
        priority=priority,
        status=status,
        author_id=author_id,
        source=TicketSource.WEB,
        created_at=created_at or datetime.now(timezone.utc),
        closed_at=closed_at,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def _executive_headers(client, db_session, department) -> dict:
    user = User(
        full_name="Тестовый Руководитель",
        department_id=department.id,
        role=UserRole.EXECUTIVE,
        login="test_dashboard_executive",
        password_hash=hash_password("TestExecutive123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    response = client.post(
        "/api/auth/login",
        json={"login": "test_dashboard_executive", "password": "TestExecutive123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_forbidden_for_engineer(client, db_session, engineer_user):
    login = client.post(
        "/api/auth/login",
        json={"login": engineer_user.login, "password": "TestEngineer123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(DASHBOARD_URL, headers=headers)
    assert response.status_code == 403


def test_dashboard_counts_open_tickets_and_priority_breakdown(
    client, db_session, department, engineer_user
):
    _make_ticket(db_session, engineer_user.id, priority=TicketPriority.HIGH, status=TicketStatus.NEW)
    _make_ticket(db_session, engineer_user.id, priority=TicketPriority.LOW, status=TicketStatus.IN_PROGRESS)
    # Закрытый тикет НЕ должен попадать ни в open_tickets, ни в priority_breakdown
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.CRITICAL, status=TicketStatus.DONE,
        closed_at=datetime.now(timezone.utc),
    )

    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["open_tickets"] == 2
    assert body["priority_breakdown"] == {"low": 1, "medium": 0, "high": 1, "critical": 0}


def test_dashboard_average_resolution_hours_computed_from_recent_done_tickets(
    client, db_session, department, engineer_user
):
    now = datetime.now(timezone.utc)
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.MEDIUM, status=TicketStatus.DONE,
        created_at=now - timedelta(hours=4), closed_at=now,
    )
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.MEDIUM, status=TicketStatus.DONE,
        created_at=now - timedelta(hours=8), closed_at=now,
    )

    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)

    assert response.status_code == 200
    assert response.json()["average_resolution_hours"] == 6.0


def test_dashboard_ignores_done_tickets_older_than_30_days(
    client, db_session, department, engineer_user
):
    old_closed_at = datetime.now(timezone.utc) - timedelta(days=45)
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.MEDIUM, status=TicketStatus.DONE,
        created_at=old_closed_at - timedelta(hours=2), closed_at=old_closed_at,
    )

    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)

    assert response.status_code == 200
    assert response.json()["average_resolution_hours"] == 0.0


def test_dashboard_returns_zero_average_when_no_done_tickets(
    client, db_session, department
):
    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["open_tickets"] == 0
    assert body["average_resolution_hours"] == 0.0
    assert body["priority_breakdown"] == {"low": 0, "medium": 0, "high": 0, "critical": 0}

def test_dashboard_ticket_trend_length_and_last_day_is_today(client, db_session, department):
    """7 точек, последняя — сегодняшний день по DEFAULT_TIMEZONE, первая — 6 дней назад."""
    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)

    trend = response.json()["ticket_trend"]
    assert len(trend) == 7

    tz = ZoneInfo(settings.DEFAULT_TIMEZONE)
    today_local = datetime.now(tz).date()
    assert trend[-1]["date"] == today_local.isoformat()
    assert trend[0]["date"] == (today_local - timedelta(days=6)).isoformat()


def test_dashboard_ticket_trend_buckets_by_local_calendar_day(
    client, db_session, department, engineer_user
):
    """Ключевой тест часового пояса: тикет за минуту до местной полуночи и за
    минуту после должны попасть в РАЗНЫЕ бакеты (вчера/сегодня), даже если по
    UTC они могут оказаться в одних сутках."""
    tz = ZoneInfo(settings.DEFAULT_TIMEZONE)
    today_local = datetime.now(tz).date()
    local_midnight_utc = datetime.combine(
        today_local, datetime.min.time(), tzinfo=tz
    ).astimezone(timezone.utc)

    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.LOW, status=TicketStatus.NEW,
        created_at=local_midnight_utc - timedelta(minutes=1),
    )
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.LOW, status=TicketStatus.NEW,
        created_at=local_midnight_utc + timedelta(minutes=1),
    )

    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)
    trend = {point["date"]: point for point in response.json()["ticket_trend"]}

    yesterday_local = today_local - timedelta(days=1)
    assert trend[yesterday_local.isoformat()]["created"] == 1
    assert trend[today_local.isoformat()]["created"] == 1


def test_dashboard_ticket_trend_excludes_tickets_outside_window(
    client, db_session, department, engineer_user
):
    old_created_at = datetime.now(timezone.utc) - timedelta(days=10)
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.LOW, status=TicketStatus.NEW,
        created_at=old_created_at,
    )

    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)

    assert sum(point["created"] for point in response.json()["ticket_trend"]) == 0


def test_dashboard_ticket_trend_counts_closed_tickets(
    client, db_session, department, engineer_user
):
    now = datetime.now(timezone.utc)
    _make_ticket(
        db_session, engineer_user.id, priority=TicketPriority.LOW, status=TicketStatus.DONE,
        created_at=now - timedelta(hours=2), closed_at=now,
    )

    headers = _executive_headers(client, db_session, department)
    response = client.get(DASHBOARD_URL, headers=headers)
    trend = response.json()["ticket_trend"]

    tz = ZoneInfo(settings.DEFAULT_TIMEZONE)
    today_local = datetime.now(tz).date().isoformat()
    today_point = next(p for p in trend if p["date"] == today_local)
    assert today_point["closed"] == 1
