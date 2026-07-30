"""
API-роуты для Repair (ремонты оборудования) — по п. 4.2 ТЗ (в части
/api/assets/{asset_id}/repairs) и сессии B08 посессионного плана.

GET  /api/assets/{asset_id}/repairs — список ремонтов актива.
POST /api/assets/{asset_id}/repairs — создание записи о ремонте (стартует со status=planned).
PATCH /api/repairs/{id} — частичное обновление, включая переходы статуса
    (planned→in_progress→done/cancelled); недопустимый переход → 409.

Доступ: Engineer+ (Engineer, IT-Head, Admin) — как и у /api/assets, см. п. 1.3 ТЗ.
Роутер без общего prefix — пути смешаны между /api/assets/... и /api/repairs/...,
поэтому prefix задан бы неверно; каждый путь прописан полностью.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import UserRole
from app.schemas.repair import RepairCreate, RepairRead, RepairUpdate
from app.services import asset_service, repair_service
from app.services.repair_service import RepairInvalidTransitionError

router = APIRouter(
    tags=["repairs"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


@router.get("/api/assets/{asset_id}/repairs", response_model=list[RepairRead])
def get_asset_repairs(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> list[RepairRead]:
    asset = asset_service.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Актив не найден")
    repairs = repair_service.list_repairs_for_asset(db, asset_id)
    return [RepairRead.model_validate(r) for r in repairs]


@router.post(
    "/api/assets/{asset_id}/repairs",
    response_model=RepairRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_repair(
    asset_id: uuid.UUID, data: RepairCreate, db: Session = Depends(get_db)
) -> RepairRead:
    asset = asset_service.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Актив не найден")
    repair = repair_service.create_repair(db, asset_id, data)
    return RepairRead.model_validate(repair)


@router.patch("/api/repairs/{repair_id}", response_model=RepairRead)
def patch_repair(repair_id: uuid.UUID, data: RepairUpdate, db: Session = Depends(get_db)) -> RepairRead:
    repair = repair_service.get_repair(db, repair_id)
    if repair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись о ремонте не найдена")
    try:
        updated = repair_service.update_repair(db, repair, data)
    except RepairInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return RepairRead.model_validate(updated)
