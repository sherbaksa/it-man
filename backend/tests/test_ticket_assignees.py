"""
Тесты для справочника исполнителей заявок — мини-сессия B10b (unplanned).
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.department import Department
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_user(
    db_session: Session, department: Department, role: UserRole, full_name: str, is_active: bool = True
) -> User:
    user = User(
        full_name=full_name,
        department_id=department.id,
        role=role,
        login=f"test_{role.name.lower()}_{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("TestPassword123!"),
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_list_ticket_assignees_returns_engineers_and_it_heads(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    it_head = _make_user(db_session, department, UserRole.IT_HEAD, "Второй Б. Руководитель")
    _make_user(db_session, department, UserRole.ADMIN, "Админов А.А.")
    _make_user(db_session, department, UserRole.EXECUTIVE, "Директоров Д.Д.")

    response = client.get("/api/ticket-assignees", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert str(engineer_user.id) in ids
    assert str(it_head.id) in ids
    assert len(response.json()) == 2  # только Engineer + IT-Head, без Admin/Executive


def test_list_ticket_assignees_excludes_inactive(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    inactive_engineer = _make_user(
        db_session, department, UserRole.ENGINEER, "Неактивный Н.Н.", is_active=False
    )

    response = client.get("/api/ticket-assignees", headers=_auth_headers(engineer_user))

    ids = {item["id"] for item in response.json()}
    assert str(inactive_engineer.id) not in ids


def test_list_ticket_assignees_sorted_by_full_name(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    _make_user(db_session, department, UserRole.IT_HEAD, "Яковлев Я.Я.")
    _make_user(db_session, department, UserRole.IT_HEAD, "Антонов А.А.")

    response = client.get("/api/ticket-assignees", headers=_auth_headers(engineer_user))

    names = [item["full_name"] for item in response.json()]
    assert names == sorted(names)


def test_executive_forbidden(
    client: TestClient, db_session: Session, department: Department
) -> None:
    executive = _make_user(db_session, department, UserRole.EXECUTIVE, "Директоров Д.Д.")

    response = client.get("/api/ticket-assignees", headers=_auth_headers(executive))

    assert response.status_code == 403
