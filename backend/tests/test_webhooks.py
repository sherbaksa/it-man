"""
Тесты для POST /api/webhooks/zabbix — сессия B13, п. 4.6/6.1 ТЗ.

Покрывает: аутентификацию (401 без/с неверным секретом), маппинг severity ->
MonitoringStatus/Ticket.priority (согласовано в B13), правило "тикет создаётся
только при status=PROBLEM и severity >= High", RESOLVED -> ok, переиспользование
системного теневого пользователя между вызовами, запись в IntegrationLog.
"""
from sqlalchemy import select

from app.core.config import settings
from app.models.integration_log import IntegrationLog, IntegrationSystem
from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource, MonitoringStatus
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.user import User

WEBHOOK_URL = "/api/webhooks/zabbix"
VALID_HEADERS = {"X-Webhook-Secret": settings.WEBHOOK_SECRET}


def _payload(
    *, host: str = "test-host-01", severity: str = "high", status: str = "PROBLEM",
    problem_name: str = "Host unreachable",
) -> dict:
    return {"host": host, "severity": severity, "status": status, "problem_name": problem_name}


def test_zabbix_webhook_requires_secret(client, db_session):
    response = client.post(WEBHOOK_URL, json=_payload())
    assert response.status_code == 401


def test_zabbix_webhook_wrong_secret(client, db_session):
    response = client.post(
        WEBHOOK_URL, json=_payload(), headers={"X-Webhook-Secret": "wrong-secret"}
    )
    assert response.status_code == 401


def test_zabbix_webhook_warning_does_not_create_ticket(client, db_session):
    """severity=warning ниже порога High — обновляет MonitoringStatus, но не создаёт Ticket."""
    response = client.post(
        WEBHOOK_URL, json=_payload(severity="warning", problem_name="High CPU load"),
        headers=VALID_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() is None

    status_row = db_session.scalar(
        select(MonitoringStatus).where(
            MonitoringStatus.host_identifier == "test-host-01",
            MonitoringStatus.source == MonitoringSource.ZABBIX,
        )
    )
    assert status_row is not None
    assert status_row.status == MonitoringHealthStatus.WARNING
    assert status_row.last_value == "High CPU load"

    assert db_session.scalar(select(Ticket)) is None


def test_zabbix_webhook_high_severity_creates_ticket(client, db_session):
    """severity=high и status=PROBLEM -> Ticket(source=zabbix_auto, priority=high, status=in_progress)."""
    response = client.post(WEBHOOK_URL, json=_payload(), headers=VALID_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["source"] == "zabbix_auto"
    assert body["priority"] == "high"
    assert body["status"] == "in_progress"
    assert body["title"] == "Zabbix: Host unreachable (test-host-01)"

    ticket = db_session.get(Ticket, body["id"])
    assert ticket is not None
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.status == TicketStatus.IN_PROGRESS
    assert ticket.source == TicketSource.ZABBIX_AUTO

    status_row = db_session.scalar(
        select(MonitoringStatus).where(MonitoringStatus.host_identifier == "test-host-01")
    )
    assert status_row.status == MonitoringHealthStatus.CRITICAL


def test_zabbix_webhook_disaster_severity_sets_critical_priority(client, db_session):
    response = client.post(
        WEBHOOK_URL,
        json=_payload(severity="disaster", problem_name="UPS battery critical"),
        headers=VALID_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "critical"


def test_zabbix_webhook_resolved_sets_status_ok_and_no_ticket(client, db_session):
    """RESOLVED принудительно -> ok, независимо от severity; тикет не создаётся."""
    response = client.post(
        WEBHOOK_URL,
        json=_payload(severity="high", status="RESOLVED", problem_name="Host is back"),
        headers=VALID_HEADERS,
    )
    assert response.status_code == 200
    assert response.json() is None

    status_row = db_session.scalar(
        select(MonitoringStatus).where(MonitoringStatus.host_identifier == "test-host-01")
    )
    assert status_row.status == MonitoringHealthStatus.OK
    assert db_session.scalar(select(Ticket)) is None


def test_zabbix_webhook_reuses_system_shadow_user_across_calls(client, db_session):
    """Два разных события с severity=high на разных хостах создают два тикета,
    но ОДНОГО и того же системного автора (get_or_create_shadow_user идемпотентен)."""
    first = client.post(WEBHOOK_URL, json=_payload(host="host-a"), headers=VALID_HEADERS)
    second = client.post(WEBHOOK_URL, json=_payload(host="host-b"), headers=VALID_HEADERS)

    assert first.status_code == 200 and second.status_code == 200
    author_id_1 = first.json()["author"]["id"]
    author_id_2 = second.json()["author"]["id"]
    assert author_id_1 == author_id_2

    system_users = db_session.scalars(
        select(User).where(User.max_user_id == "system:zabbix")
    ).all()
    assert len(system_users) == 1
    assert system_users[0].full_name == "Zabbix (автоматически)"


def test_zabbix_webhook_logs_integration_call(client, db_session):
    client.post(WEBHOOK_URL, json=_payload(), headers=VALID_HEADERS)

    log_entry = db_session.scalar(
        select(IntegrationLog).where(IntegrationLog.system == IntegrationSystem.ZABBIX)
    )
    assert log_entry is not None
    assert log_entry.endpoint == "/api/webhooks/zabbix"
    assert log_entry.status_code == 200
    assert log_entry.payload["host"] == "test-host-01"


def test_zabbix_webhook_invalid_severity_returns_422(client, db_session):
    response = client.post(
        WEBHOOK_URL,
        json={"host": "test-host-01", "severity": "not-a-real-severity",
              "status": "PROBLEM", "problem_name": "Broken"},
        headers=VALID_HEADERS,
    )
    assert response.status_code == 422


def test_zabbix_webhook_missing_required_field_returns_422(client, db_session):
    response = client.post(
        WEBHOOK_URL,
        json={"severity": "high", "status": "PROBLEM", "problem_name": "No host field"},
        headers=VALID_HEADERS,
    )
    assert response.status_code == 422
