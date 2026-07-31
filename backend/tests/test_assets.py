"""
Тесты /api/assets (ТЗ раздел 3.2, раздел 4.2):
- создание, дубликат inventory_number → 409
- фильтрация по status/search
- получение детальной карточки (movements[]/repairs[])
- PATCH меняет location/status и создаёт запись Movement
- DELETE запрещён для Engineer (только IT-Head/Admin)
- правило: нельзя списать актив с открытой заявкой → 409
- экспорт .xlsx — корректный content-type
"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.asset import Asset, AssetStatus
from app.models.equipment_type import EquipmentType
from app.models.ticket import Ticket, TicketSource, TicketStatus
from app.models.user import User


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_create_asset_as_engineer(
    client: TestClient, engineer_user: User, equipment_type: EquipmentType
) -> None:
    payload = {
        "inventory_number": "INV-0100",
        "type_id": str(equipment_type.id),
        "model": "ThinkPad T14",
    }

    response = client.post("/api/assets", json=payload, headers=_auth_headers(engineer_user))

    assert response.status_code == 201
    body = response.json()
    assert body["inventory_number"] == "INV-0100"
    assert body["type"]["id"] == str(equipment_type.id)
    assert body["status"] == AssetStatus.IN_STOCK.value


def test_create_asset_duplicate_inventory_number_conflict(
    client: TestClient, engineer_user: User, asset: Asset, equipment_type: EquipmentType
) -> None:
    payload = {
        "inventory_number": asset.inventory_number,  # уже занят фикстурой asset
        "type_id": str(equipment_type.id),
    }

    response = client.post("/api/assets", json=payload, headers=_auth_headers(engineer_user))

    assert response.status_code == 409


def test_list_assets_with_search_filter(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    response = client.get(
        f"/api/assets?search={asset.inventory_number}", headers=_auth_headers(engineer_user)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["inventory_number"] == asset.inventory_number


def test_list_assets_search_filter_no_match(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    response = client.get("/api/assets?search=НЕТ-ТАКОГО", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_get_asset_detail(client: TestClient, engineer_user: User, asset: Asset) -> None:
    response = client.get(f"/api/assets/{asset.id}", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(asset.id)
    assert body["movements"] == []
    assert body["repairs"] == []


def test_patch_asset_location_creates_movement(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    response = client.patch(
        f"/api/assets/{asset.id}",
        json={"location": "Каб. 305"},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["location"] == "Каб. 305"
    assert len(body["movements"]) == 1
    assert body["movements"][0]["to_location"] == "Каб. 305"
    assert body["movements"][0]["from_location"] is None

def test_patch_asset_clear_location_does_not_create_movement(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    """Регресс-тест на баг из ревью Dev2 (после B08): из-за приоритета `and` над `or`
    в условии `location_changed or status_changed and asset.location is not None`
    очистка существующего location (PATCH {"location": null}) приводила к попытке
    создать Movement(to_location=None) при NOT NULL в БД. Сценарий: сначала задаём
    location (создаёт Movement №1), затем очищаем его — должно пройти 200 и НЕ
    создать второй Movement с пустым to_location."""
    first = client.patch(
        f"/api/assets/{asset.id}",
        json={"location": "Каб. 100"},
        headers=_auth_headers(engineer_user),
    )
    assert first.status_code == 200

    response = client.patch(
        f"/api/assets/{asset.id}",
        json={"location": None},
        headers=_auth_headers(engineer_user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["location"] is None
    assert len(body["movements"]) == 1  # только от первого изменения, не от очистки

def test_delete_asset_forbidden_for_engineer(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    response = client.delete(f"/api/assets/{asset.id}", headers=_auth_headers(engineer_user))

    assert response.status_code == 403


def test_delete_asset_as_admin(client: TestClient, admin_user: User, asset: Asset) -> None:
    response = client.delete(f"/api/assets/{asset.id}", headers=_auth_headers(admin_user))

    assert response.status_code == 204

    get_response = client.get(f"/api/assets/{asset.id}", headers=_auth_headers(admin_user))
    assert get_response.json()["status"] == AssetStatus.WRITTEN_OFF.value


def test_write_off_blocked_by_open_ticket(
    client: TestClient, db_session: Session, admin_user: User, asset: Asset
) -> None:
    """Основной кейс из рекомендаций B07: 409 при попытке списать актив,
    по которому есть незакрытая заявка."""
    ticket = Ticket(
        title="Не включается",
        author_id=admin_user.id,
        asset_id=asset.id,
        source=TicketSource.WEB,
        status=TicketStatus.NEW,
    )
    db_session.add(ticket)
    db_session.commit()

    response = client.patch(
        f"/api/assets/{asset.id}",
        json={"status": AssetStatus.WRITTEN_OFF.value},
        headers=_auth_headers(admin_user),
    )

    assert response.status_code == 409

    # актив не должен был измениться
    get_response = client.get(f"/api/assets/{asset.id}", headers=_auth_headers(admin_user))
    assert get_response.json()["status"] == AssetStatus.IN_STOCK.value


def test_export_assets_returns_xlsx(
    client: TestClient, engineer_user: User, asset: Asset
) -> None:
    response = client.get("/api/assets/export", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers["content-disposition"]


def test_get_asset_not_found(client: TestClient, engineer_user: User) -> None:
    response = client.get(f"/api/assets/{uuid.uuid4()}", headers=_auth_headers(engineer_user))

    assert response.status_code == 404
