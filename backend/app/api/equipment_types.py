"""
API-роут для EquipmentType (справочник типов оборудования) — мини-сессия B09a.

GET /api/equipment-types — список всех типов, отсортированный по name.
Нужен фронтенду для реального выбора type_id при создании/редактировании Asset
(вместо мокового справочника).

Доступ: Engineer+ (Engineer, IT-Head, Admin) — см. п. 1.3 ТЗ "Роли и права доступа".
Executive не нуждается в этом справочнике (работает с агрегированными дашбордами).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.equipment_type import EquipmentType
from app.models.user import UserRole
from app.schemas.equipment_type import EquipmentTypeRead

router = APIRouter(
    prefix="/api/equipment-types",
    tags=["equipment-types"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


@router.get("", response_model=list[EquipmentTypeRead])
def get_equipment_types(db: Session = Depends(get_db)) -> list[EquipmentType]:
    stmt = select(EquipmentType).order_by(EquipmentType.name)
    return list(db.scalars(stmt).all())
