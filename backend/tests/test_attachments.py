"""
Тесты для Attachment (вложения к заявкам, MinIO) — сессия B10a.

MinIO не поднимается в юнит-тестах — все вызовы app.core.storage подменяются
monkeypatch'ем (upload_file/delete_file — через сервисный слой, get_presigned_url —
напрямую в api/attachments.py, куда импортирован по имени).
"""
import io
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.department import Department
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


def _create_ticket(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/tickets", json={"title": "Заявка для теста вложений"}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture(autouse=True)
def _mock_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Подменяет все обращения к MinIO — тесты не должны требовать реального MinIO."""
    monkeypatch.setattr(
        "app.services.attachment_service.storage.upload_file",
        lambda file_bytes, key, content_type: key,
    )
    monkeypatch.setattr(
        "app.services.attachment_service.storage.delete_file", lambda storage_key: None
    )
    monkeypatch.setattr(
        "app.api.attachments.get_presigned_url",
        lambda storage_key, expires_seconds=300: f"http://mock-presigned/{storage_key}",
    )


def test_upload_attachment_success(client: TestClient, engineer_user: User) -> None:
    headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, headers)

    response = client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_name"] == "photo.png"
    assert body["content_type"] == "image/png"
    assert body["download_url"].startswith("http://mock-presigned/tickets/")
    assert body["can_delete"] is True  # свой файл — Engineer видит право на удаление


def test_upload_attachment_rejects_disallowed_type(client: TestClient, engineer_user: User) -> None:
    headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, headers)

    response = client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=headers,
        files={"file": ("virus.exe", io.BytesIO(b"MZ-fake-exe"), "application/x-msdownload")},
    )

    assert response.status_code == 422


def test_upload_attachment_rejects_oversized_file(
    client: TestClient, engineer_user: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "MAX_ATTACHMENT_SIZE_MB", 1)
    headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, headers)
    oversized = b"0" * (2 * 1024 * 1024)  # 2 МБ при лимите 1 МБ

    response = client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=headers,
        files={"file": ("big.png", io.BytesIO(oversized), "image/png")},
    )

    assert response.status_code == 422


def test_upload_attachment_ticket_not_found(client: TestClient, engineer_user: User) -> None:
    headers = _auth_headers(engineer_user)

    response = client.post(
        f"/api/tickets/{uuid.uuid4()}/attachments",
        headers=headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )

    assert response.status_code == 404


def test_list_attachments_returns_uploaded_files(client: TestClient, engineer_user: User) -> None:
    headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, headers)
    client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )

    response = client.get(f"/api/tickets/{ticket_id}/attachments", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["file_name"] == "photo.png"


def test_list_attachments_ticket_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.get(
        f"/api/tickets/{uuid.uuid4()}/attachments", headers=_auth_headers(engineer_user)
    )

    assert response.status_code == 404


def test_delete_attachment_by_uploader_succeeds(client: TestClient, engineer_user: User) -> None:
    headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, headers)
    upload_response = client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    attachment_id = upload_response.json()["id"]

    response = client.delete(f"/api/attachments/{attachment_id}", headers=headers)

    assert response.status_code == 204
    list_response = client.get(f"/api/tickets/{ticket_id}/attachments", headers=headers)
    assert list_response.json() == []


def test_engineer_cannot_delete_others_attachment(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    owner_headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, owner_headers)
    upload_response = client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=owner_headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    attachment_id = upload_response.json()["id"]

    other_engineer = _make_user(db_session, department, UserRole.ENGINEER)
    response = client.delete(
        f"/api/attachments/{attachment_id}", headers=_auth_headers(other_engineer)
    )

    assert response.status_code == 403


def test_it_head_can_delete_others_attachment(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    owner_headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, owner_headers)
    upload_response = client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=owner_headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    attachment_id = upload_response.json()["id"]

    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    response = client.delete(
        f"/api/attachments/{attachment_id}", headers=_auth_headers(it_head)
    )

    assert response.status_code == 204


def test_delete_attachment_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.delete(
        f"/api/attachments/{uuid.uuid4()}", headers=_auth_headers(engineer_user)
    )

    assert response.status_code == 404

def test_list_attachments_can_delete_reflects_permissions(
    client: TestClient, db_session: Session, department: Department, engineer_user: User
) -> None:
    owner_headers = _auth_headers(engineer_user)
    ticket_id = _create_ticket(client, owner_headers)
    client.post(
        f"/api/tickets/{ticket_id}/attachments",
        headers=owner_headers,
        files={"file": ("photo.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )

    other_engineer = _make_user(db_session, department, UserRole.ENGINEER)
    other_response = client.get(
        f"/api/tickets/{ticket_id}/attachments", headers=_auth_headers(other_engineer)
    )
    assert other_response.json()[0]["can_delete"] is False

    it_head = _make_user(db_session, department, UserRole.IT_HEAD)
    it_head_response = client.get(
        f"/api/tickets/{ticket_id}/attachments", headers=_auth_headers(it_head)
    )
    assert it_head_response.json()[0]["can_delete"] is True
