"""
Тесты /api/assets/{asset_id}/repairs и /api/repairs/{id} (ТЗ раздел 3.4):
- создание ремонта (стартует со status=planned)
- список ремонтов актива
- допустимые переходы статуса (planned→in_progress→done)
- недопустимый переход (done→in_progress) → 409
- 404 на несуществующий asset_id/repair_id
"""
import uuid

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.asset import Asset
from app.models.user import User


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_create_repair_starts_as_planned(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    payload = {"repair_type": "Замена термопасты", "cost": "1500.00"}

    response = client.post(
        f"/api/assets/{asset.id}/repairs", json=payload, headers=_auth_headers(engineer_user)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["asset_id"] == str(asset.id)
    assert body["status"] == "planned"
    assert body["cost"] == "1500.00"


def test_create_repair_for_unknown_asset_returns_404(
    client: TestClient, engineer_user: User
) -> None:
    response = client.post(
        f"/api/assets/{uuid.uuid4()}/repairs",
        json={"repair_type": "Диагностика"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 404


def test_list_repairs_for_asset(client: TestClient, engineer_user: User, asset: Asset) -> None:
    client.post(
        f"/api/assets/{asset.id}/repairs",
        json={"repair_type": "Чистка"},
        headers=_auth_headers(engineer_user),
    )

    response = client.get(f"/api/assets/{asset.id}/repairs", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["repair_type"] == "Чистка"


def test_repair_status_transition_planned_to_in_progress_to_done(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    headers = _auth_headers(engineer_user)
    create_response = client.post(
        f"/api/assets/{asset.id}/repairs",
        json={"repair_type": "Замена матрицы"},
        headers=headers,
    )
    repair_id = create_response.json()["id"]

    in_progress_response = client.patch(
        f"/api/repairs/{repair_id}", json={"status": "in_progress"}, headers=headers
    )
    assert in_progress_response.status_code == 200
    assert in_progress_response.json()["status"] == "in_progress"

    done_response = client.patch(
        f"/api/repairs/{repair_id}", json={"status": "done"}, headers=headers
    )
    assert done_response.status_code == 200
    assert done_response.json()["status"] == "done"


def test_repair_status_invalid_transition_from_done_is_rejected(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    headers = _auth_headers(engineer_user)
    create_response = client.post(
        f"/api/assets/{asset.id}/repairs",
        json={"repair_type": "Ремонт блока питания"},
        headers=headers,
    )
    repair_id = create_response.json()["id"]

    client.patch(f"/api/repairs/{repair_id}", json={"status": "in_progress"}, headers=headers)
    client.patch(f"/api/repairs/{repair_id}", json={"status": "done"}, headers=headers)

    response = client.patch(
        f"/api/repairs/{repair_id}", json={"status": "in_progress"}, headers=headers
    )

    assert response.status_code == 409


def test_patch_repair_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.patch(
        f"/api/repairs/{uuid.uuid4()}",
        json={"status": "in_progress"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 404
