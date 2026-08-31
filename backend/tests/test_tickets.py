"""
Тесты /api/tickets (п. 3.5, 4.3 ТЗ, сессия B09) и /api/my/tickets (сессия B10):
- создание заявки (POST), source всегда WEB
- доступ по ролям: Engineer/IT-Head/Admin — 200/201, Executive — 403
- правило: нельзя закрыть заявку (status=done) без resolution — 422
- Engineer может менять только свои назначенные заявки — 403 на чужие
- 404 на несуществующий ticket_id
- /api/my/tickets: аутентификация через X-Webhook-Secret (не JWT), find-or-create
  теневого пользователя по max_user_id, возврат только его заявок
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.department import Department
from app.models.ticket import Ticket, TicketSource
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_user(db_session: Session, department: Department, role: UserRole) -> User:
    user = User(
        full_name=f"Тестовый {role.value}",
        department_id=department.id,
        role=role,
        login=f"test_{role.name.lower()}_{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_ticket_sets_source_web(client: TestClient, engineer_user: User) -> None:
    response = client.post(
        "/api/tickets",
        json={"title": "Не работает принтер"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "web"
    assert body["status"] == "new"
    assert body["author"]["id"] == str(engineer_user.id)


def test_list_tickets_forbidden_for_executive(
    client: TestClient, db_session: Session, department: Department
) -> None:
    executive = _make_user(db_session, department, UserRole.EXECUTIVE)

    response = client.get("/api/tickets", headers=_auth_headers(executive))

    assert response.status_code == 403


def test_patch_ticket_to_done_requires_resolution(
    client: TestClient, engineer_user: User
) -> None:
    headers = _auth_headers(engineer_user)
    create_response = client.post(
        "/api/tickets", json={"title": "Завис компьютер"}, headers=headers
    )
    ticket_id = create_response.json()["id"]
    client.patch(f"/api/tickets/{ticket_id}", json={"assignee_id": str(engineer_user.id)}, headers=headers)

    response = client.patch(f"/api/tickets/{ticket_id}", json={"status": "done"}, headers=headers)

    assert response.status_code == 422


def test_patch_ticket_to_done_with_resolution_succeeds(
    client: TestClient, engineer_user: User
) -> None:
    headers = _auth_headers(engineer_user)
    create_response = client.post(
        "/api/tickets", json={"title": "Не включается монитор"}, headers=headers
    )
    ticket_id = create_response.json()["id"]
    client.patch(f"/api/tickets/{ticket_id}", json={"assignee_id": str(engineer_user.id)}, headers=headers)

    response = client.patch(
        f"/api/tickets/{ticket_id}",
        json={"status": "done", "resolution": "Заменён кабель питания"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["closed_at"] is not None


def test_engineer_cannot_patch_ticket_assigned_to_another_engineer(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    other_engineer = _make_user(db_session, department, UserRole.ENGINEER)
    headers_owner = _auth_headers(engineer_user)
    create_response = client.post(
        "/api/tickets", json={"title": "Не печатает принтер"}, headers=headers_owner
    )
    ticket_id = create_response.json()["id"]
    client.patch(
        f"/api/tickets/{ticket_id}", json={"assignee_id": str(engineer_user.id)}, headers=headers_owner
    )

    response = client.patch(
        f"/api/tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers=_auth_headers(other_engineer),
    )

    assert response.status_code == 403


def test_patch_ticket_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.patch(
        f"/api/tickets/{uuid.uuid4()}",
        json={"status": "in_progress"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 404


def test_get_ticket_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.get(f"/api/tickets/{uuid.uuid4()}", headers=_auth_headers(engineer_user))

    assert response.status_code == 404


# --- /api/my/tickets (B10) ---

MAX_USER_ID = "19731057"


def _webhook_headers() -> dict[str, str]:
    return {"X-Webhook-Secret": settings.WEBHOOK_SECRET}


def test_my_tickets_requires_webhook_secret(client: TestClient) -> None:
    response = client.get(f"/api/my/tickets?max_user_id={MAX_USER_ID}")

    assert response.status_code == 401


def test_my_tickets_rejects_wrong_webhook_secret(client: TestClient) -> None:
    response = client.get(
        f"/api/my/tickets?max_user_id={MAX_USER_ID}", headers={"X-Webhook-Secret": "wrong"}
    )

    assert response.status_code == 401


def test_my_tickets_requires_max_user_id(client: TestClient) -> None:
    response = client.get("/api/my/tickets", headers=_webhook_headers())

    assert response.status_code == 422


def test_my_tickets_creates_shadow_user_on_first_call(
    client: TestClient, db_session: Session
) -> None:
    response = client.get(
        f"/api/my/tickets?max_user_id={MAX_USER_ID}&full_name=Сергей Щербак",
        headers=_webhook_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}

    shadow_user = db_session.query(User).filter(User.max_user_id == MAX_USER_ID).one()
    assert shadow_user.full_name == "Сергей Щербак"
    assert shadow_user.role == UserRole.USER
    assert shadow_user.login is None
    assert shadow_user.department_id is None
    assert shadow_user.password_hash is None


def test_my_tickets_second_call_does_not_duplicate_shadow_user(
    client: TestClient, db_session: Session
) -> None:
    client.get(f"/api/my/tickets?max_user_id={MAX_USER_ID}", headers=_webhook_headers())
    client.get(f"/api/my/tickets?max_user_id={MAX_USER_ID}", headers=_webhook_headers())

    count = db_session.query(User).filter(User.max_user_id == MAX_USER_ID).count()
    assert count == 1


def test_my_tickets_returns_only_own_tickets(
    client: TestClient, db_session: Session
) -> None:
    # Первый вызов создаёт теневого пользователя MAX_USER_ID
    client.get(f"/api/my/tickets?max_user_id={MAX_USER_ID}", headers=_webhook_headers())
    shadow_user = db_session.query(User).filter(User.max_user_id == MAX_USER_ID).one()

    # Заявка нашего теневого пользователя
    own_ticket = Ticket(
        title="Заявка от MAX", author_id=shadow_user.id, source=TicketSource.MAX
    )
    # Заявка постороннего пользователя (другой теневой MAX-юзер)
    other_shadow = User(
        full_name="Другой пользователь MAX",
        role=UserRole.USER,
        max_user_id="00000001",
    )
    db_session.add(other_shadow)
    db_session.commit()
    db_session.refresh(other_shadow)
    other_ticket = Ticket(
        title="Чужая заявка", author_id=other_shadow.id, source=TicketSource.MAX
    )
    db_session.add_all([own_ticket, other_ticket])
    db_session.commit()

    response = client.get(f"/api/my/tickets?max_user_id={MAX_USER_ID}", headers=_webhook_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Заявка от MAX"
