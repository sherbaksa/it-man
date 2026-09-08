"""
Тесты /api/monitoring (п. 4.5 ТЗ, сессия B12):
- /status: доступ Engineer+, кэш в Redis на 60с (повторный запрос не бьёт в БД)
- /status/{host}/history: отдаёт записи из append-only MonitoringStatusHistory,
  фильтрация по from/to
- /summary: доступ Executive+ (Engineer — 403), агрегат {ok, warning, critical, unknown}
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.redis_client import get_redis
from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
from app.models.department import Department
from app.models.monitoring_status import MonitoringHealthStatus, MonitoringSource, MonitoringStatus
from app.models.monitoring_status_history import MonitoringStatusHistory
from app.models.user import User, UserRole


class FakeRedis:
    """Минимальный in-memory заменитель redis.Redis для тестов — только get/set,
    TTL (ex=) игнорируется, т.к. в рамках одного теста истечение не проверяется."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_user(db_session: Session, department: Department, role: UserRole) -> User:
    user = User(
        full_name=f"Тестовый {role.value}",
        department_id=department.id,
        role=role,
        login=f"test_{role.name.lower()}_mon",
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _override_redis(fake: FakeRedis):
    def _get() -> FakeRedis:
        return fake

    return _get


def test_status_forbidden_for_executive(
    client: TestClient, db_session: Session, department: Department
) -> None:
    executive = _make_user(db_session, department, UserRole.EXECUTIVE)

    response = client.get("/api/monitoring/status", headers=_auth_headers(executive))

    assert response.status_code == 403


def test_status_returns_items_and_uses_cache(
    client: TestClient, engineer_user: User, db_session: Session
) -> None:
    db_session.add(
        MonitoringStatus(
            host_identifier="srv-01",
            source=MonitoringSource.ZABBIX,
            status=MonitoringHealthStatus.OK,
            last_value=None,
            checked_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    fake_redis = FakeRedis()
    fastapi_app.dependency_overrides[get_redis] = _override_redis(fake_redis)
    try:
        first = client.get("/api/monitoring/status", headers=_auth_headers(engineer_user))
        assert first.status_code == 200
        assert first.json()["total"] == 1
        assert "monitoring:status:all" in fake_redis._store

        # Второй запрос — данные меняются в БД напрямую, но ответ должен остаться
        # прежним, т.к. берётся из кэша (не бьёт в БД повторно).
        db_session.add(
            MonitoringStatus(
                host_identifier="srv-02",
                source=MonitoringSource.ZABBIX,
                status=MonitoringHealthStatus.CRITICAL,
                last_value=None,
                checked_at=datetime.now(timezone.utc),
            )
        )
        db_session.commit()

        second = client.get("/api/monitoring/status", headers=_auth_headers(engineer_user))
        assert second.status_code == 200
        assert second.json()["total"] == 1  # из кэша, а не 2
    finally:
        del fastapi_app.dependency_overrides[get_redis]


def test_history_filters_by_period(client: TestClient, engineer_user: User, db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            MonitoringStatusHistory(
                host_identifier="srv-01",
                source=MonitoringSource.ZABBIX,
                status=MonitoringHealthStatus.OK,
                last_value=None,
                checked_at=now - timedelta(hours=48),
            ),
            MonitoringStatusHistory(
                host_identifier="srv-01",
                source=MonitoringSource.ZABBIX,
                status=MonitoringHealthStatus.WARNING,
                last_value=None,
                checked_at=now - timedelta(hours=1),
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/monitoring/status/srv-01/history",
        params={"from": (now - timedelta(hours=24)).isoformat()},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "warning"


def test_summary_forbidden_for_engineer(client: TestClient, engineer_user: User) -> None:
    response = client.get("/api/monitoring/summary", headers=_auth_headers(engineer_user))

    assert response.status_code == 403


def test_summary_counts_by_status(
    client: TestClient, db_session: Session, department: Department
) -> None:
    admin = _make_user(db_session, department, UserRole.ADMIN)
    db_session.add_all(
        [
            MonitoringStatus(
                host_identifier="srv-01",
                source=MonitoringSource.ZABBIX,
                status=MonitoringHealthStatus.OK,
                last_value=None,
                checked_at=datetime.now(timezone.utc),
            ),
            MonitoringStatus(
                host_identifier="srv-02",
                source=MonitoringSource.ZABBIX,
                status=MonitoringHealthStatus.CRITICAL,
                last_value=None,
                checked_at=datetime.now(timezone.utc),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/monitoring/summary", headers=_auth_headers(admin))

    assert response.status_code == 200
    body = response.json()
    assert body == {"ok": 1, "warning": 0, "critical": 1, "unknown": 0}
