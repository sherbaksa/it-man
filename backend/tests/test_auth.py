"""
Тесты /api/auth/* (ТЗ раздел 4.1, раздел 7):
- успешный логин, неверный пароль → 401, роль User → 403
- refresh-флоу с ротацией
- logout
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.department import Department
from app.models.user import User, UserRole


def test_login_success(client: TestClient, admin_user: User) -> None:
    response = client.post(
        "/api/auth/login",
        json={"login": admin_user.login, "password": "TestAdmin123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["id"] == str(admin_user.id)
    assert body["user"]["role"] == UserRole.ADMIN.value
    assert body["user"]["full_name"] == admin_user.full_name
    # password_hash не должен утекать ни при каких обстоятельствах
    assert "password_hash" not in body["user"]
    # refresh_token должен быть выставлен как cookie, а не в теле ответа
    assert "refresh_token" in response.cookies


def test_login_wrong_password(client: TestClient, admin_user: User) -> None:
    response = client.post(
        "/api/auth/login",
        json={"login": admin_user.login, "password": "WrongPassword!"},
    )

    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"login": "no_such_login", "password": "whatever"},
    )

    assert response.status_code == 401


def test_login_role_user_forbidden(client: TestClient, db_session: Session, department: Department) -> None:
    """Бизнес-правило п. 3.1 ТЗ: роль User не может логиниться в веб — 403."""
    shadow_user = User(
        full_name="Теневой пользователь MAX",
        department_id=department.id,
        role=UserRole.USER,
        login="test_shadow_user",
        password_hash=hash_password("Whatever123!"),
        is_active=True,
    )
    db_session.add(shadow_user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"login": shadow_user.login, "password": "Whatever123!"},
    )

    assert response.status_code == 403


def test_login_inactive_user(client: TestClient, db_session: Session, department: Department) -> None:
    inactive_user = User(
        full_name="Деактивированный пользователь",
        department_id=department.id,
        role=UserRole.ENGINEER,
        login="test_inactive",
        password_hash=hash_password("Whatever123!"),
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"login": inactive_user.login, "password": "Whatever123!"},
    )

    assert response.status_code == 401


def test_refresh_rotates_token(client: TestClient, admin_user: User) -> None:
    login_response = client.post(
        "/api/auth/login",
        json={"login": admin_user.login, "password": "TestAdmin123!"},
    )
    assert login_response.status_code == 200
    first_refresh_cookie = login_response.cookies["refresh_token"]

    # TestClient хранит cookies между запросами автоматически (та же сессия),
    # поэтому refresh_token из /login уже прикреплён к следующему запросу.
    refresh_response = client.post("/api/auth/refresh")

    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    second_refresh_cookie = refresh_response.cookies["refresh_token"]
    # jti в payload refresh-токена рандомный при каждой генерации — гарантированно
    # другое значение при ротации, в отличие от access_token (см. примечание к security.py:
    # iat/exp усечены до целых секунд, поэтому access_token в пределах той же секунды
    # теоретически может совпасть — не проверяем его на неравенство, чтобы не ловить flaky-тест).
    assert second_refresh_cookie != first_refresh_cookie


def test_refresh_without_cookie_unauthorized(client: TestClient) -> None:
    response = client.post("/api/auth/refresh")

    assert response.status_code == 401


def test_logout_clears_cookie(client: TestClient, admin_user: User) -> None:
    client.post(
        "/api/auth/login",
        json={"login": admin_user.login, "password": "TestAdmin123!"},
    )

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    # После logout cookie должна быть очищена — повторный /refresh снова 401
    refresh_response = client.post("/api/auth/refresh")
    assert refresh_response.status_code == 401
