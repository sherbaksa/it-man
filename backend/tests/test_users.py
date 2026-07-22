"""
Тесты /api/users (ТЗ раздел 4 «/api/users... только Admin», раздел 3.1):
- полный CRUD под Admin
- 403 под другими ролями
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.department import Department
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_list_users_as_admin(client: TestClient, admin_user: User, engineer_user: User) -> None:
    response = client.get("/api/users", headers=_auth_headers(admin_user))

    assert response.status_code == 200
    logins = [u["login"] for u in response.json()]
    assert admin_user.login in logins
    assert engineer_user.login in logins
    # password_hash не должен утекать ни в одном элементе списка
    assert all("password_hash" not in u for u in response.json())


def test_list_users_forbidden_for_engineer(client: TestClient, engineer_user: User) -> None:
    response = client.get("/api/users", headers=_auth_headers(engineer_user))

    assert response.status_code == 403


def test_get_user_by_id_as_admin(client: TestClient, admin_user: User, engineer_user: User) -> None:
    response = client.get(f"/api/users/{engineer_user.id}", headers=_auth_headers(admin_user))

    assert response.status_code == 200
    assert response.json()["id"] == str(engineer_user.id)
    assert "password_hash" not in response.json()


def test_get_user_not_found(client: TestClient, admin_user: User) -> None:
    response = client.get(f"/api/users/{uuid.uuid4()}", headers=_auth_headers(admin_user))

    assert response.status_code == 404


def test_create_user_as_admin(client: TestClient, admin_user: User, department: Department) -> None:
    payload = {
        "full_name": "Новый Инженер",
        "department_id": str(department.id),
        "role": UserRole.ENGINEER.value,
        "login": "new_engineer",
        "password": "NewEngineer123!",
    }

    response = client.post("/api/users", json=payload, headers=_auth_headers(admin_user))

    assert response.status_code == 201
    body = response.json()
    assert body["login"] == "new_engineer"
    assert body["is_active"] is True
    assert "password_hash" not in body
    assert "password" not in body


def test_create_user_duplicate_login_conflict(
    client: TestClient, admin_user: User, engineer_user: User, department: Department
) -> None:
    payload = {
        "full_name": "Дубликат Логина",
        "department_id": str(department.id),
        "role": UserRole.ENGINEER.value,
        "login": engineer_user.login,  # уже занят фикстурой engineer_user
        "password": "Whatever123!",
    }

    response = client.post("/api/users", json=payload, headers=_auth_headers(admin_user))

    assert response.status_code == 409


def test_create_user_forbidden_for_engineer(client: TestClient, engineer_user: User, department: Department) -> None:
    payload = {
        "full_name": "Попытка Создания",
        "department_id": str(department.id),
        "role": UserRole.ENGINEER.value,
        "login": "should_not_be_created",
        "password": "Whatever123!",
    }

    response = client.post("/api/users", json=payload, headers=_auth_headers(engineer_user))

    assert response.status_code == 403


def test_update_user_partial_as_admin(client: TestClient, admin_user: User, engineer_user: User) -> None:
    response = client.patch(
        f"/api/users/{engineer_user.id}",
        json={"position": "Ведущий инженер"},
        headers=_auth_headers(admin_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["position"] == "Ведущий инженер"
    # остальные поля не должны были затронуться при частичном обновлении
    assert body["login"] == engineer_user.login
    assert body["full_name"] == engineer_user.full_name


def test_update_user_forbidden_for_engineer(client: TestClient, engineer_user: User) -> None:
    response = client.patch(
        f"/api/users/{engineer_user.id}",
        json={"position": "Попытка самоизменения"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 403


def test_deactivate_and_reactivate_user_as_admin(client: TestClient, admin_user: User, engineer_user: User) -> None:
    headers = _auth_headers(admin_user)

    deactivate_response = client.delete(f"/api/users/{engineer_user.id}", headers=headers)
    assert deactivate_response.status_code == 204

    get_response = client.get(f"/api/users/{engineer_user.id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["is_active"] is False

    reactivate_response = client.patch(
        f"/api/users/{engineer_user.id}",
        json={"is_active": True},
        headers=headers,
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True


def test_deactivated_user_cannot_login(
    client: TestClient, db_session: Session, admin_user: User, engineer_user: User
) -> None:
    """Сквозная проверка: деактивация через /api/users реально блокирует вход через /api/auth/login."""
    client.delete(f"/api/users/{engineer_user.id}", headers=_auth_headers(admin_user))

    login_response = client.post(
        "/api/auth/login",
        json={"login": engineer_user.login, "password": "TestEngineer123!"},
    )

    assert login_response.status_code == 401
