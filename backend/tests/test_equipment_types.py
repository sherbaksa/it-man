"""
Тесты /api/equipment-types (мини-сессия B09a):
- доступ по ролям: Engineer/IT-Head/Admin — 200, Executive — 403
- список отсортирован по name
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.department import Department
from app.models.equipment_type import EquipmentType
from app.models.user import User, UserRole


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_user(db_session: Session, department: Department, role: UserRole) -> User:
    user = User(
        full_name=f"Тестовый {role.value}",
        department_id=department.id,
        role=role,
        login=f"test_{role.name.lower()}",
        password_hash=hash_password("TestPassword123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_list_equipment_types_as_engineer(
    client: TestClient, engineer_user: User, equipment_type: EquipmentType
) -> None:
    response = client.get("/api/equipment-types", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == str(equipment_type.id) for item in body)
    assert set(body[0].keys()) == {"id", "name"}


def test_list_equipment_types_as_admin(
    client: TestClient, admin_user: User, equipment_type: EquipmentType
) -> None:
    response = client.get("/api/equipment-types", headers=_auth_headers(admin_user))

    assert response.status_code == 200


def test_list_equipment_types_as_it_head(
    client: TestClient, db_session: Session, department: Department, equipment_type: EquipmentType
) -> None:
    it_head = _make_user(db_session, department, UserRole.IT_HEAD)

    response = client.get("/api/equipment-types", headers=_auth_headers(it_head))

    assert response.status_code == 200


def test_list_equipment_types_forbidden_for_executive(
    client: TestClient, db_session: Session, department: Department, equipment_type: EquipmentType
) -> None:
    executive = _make_user(db_session, department, UserRole.EXECUTIVE)

    response = client.get("/api/equipment-types", headers=_auth_headers(executive))

    assert response.status_code == 403


def test_list_equipment_types_sorted_by_name(
    client: TestClient, db_session: Session, engineer_user: User
) -> None:
    zebra = EquipmentType(name="Я-тип-последний")
    alpha = EquipmentType(name="А-тип-первый")
    db_session.add_all([zebra, alpha])
    db_session.commit()

    response = client.get("/api/equipment-types", headers=_auth_headers(engineer_user))

    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert names == sorted(names)
