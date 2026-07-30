"""
Сервисный слой для Repair — по п. 3.4 ТЗ и сессии B08 посессионного плана.

list_repairs_for_asset() — список ремонтов актива (для GET /api/assets/{asset_id}/repairs).
get_repair() — получение одной записи по id.
create_repair() — создание записи, всегда стартует со status=planned.
update_repair() — PATCH-семантика (exclude_unset), с проверкой допустимости
    перехода status по таблице _ALLOWED_TRANSITIONS.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.repair import Repair, RepairStatus
from app.schemas.repair import RepairCreate, RepairUpdate


class RepairInvalidTransitionError(Exception):
    """Поднимается при недопустимом переходе status (например done → in_progress).
    Обрабатывается в api/repairs.py как 409 Conflict — сервисный слой framework-агностичен,
    по аналогии с AssetHasOpenTicketsError/AssetDuplicateError из asset_service.py."""


_ALLOWED_TRANSITIONS: dict[RepairStatus, set[RepairStatus]] = {
    RepairStatus.PLANNED: {RepairStatus.IN_PROGRESS, RepairStatus.CANCELLED},
    RepairStatus.IN_PROGRESS: {RepairStatus.DONE, RepairStatus.CANCELLED},
    RepairStatus.DONE: set(),
    RepairStatus.CANCELLED: set(),
}


def list_repairs_for_asset(db: Session, asset_id: uuid.UUID) -> list[Repair]:
    query = (
        select(Repair)
        .where(Repair.asset_id == asset_id)
        .order_by(Repair.started_at.desc().nullslast())
    )
    return list(db.execute(query).scalars().all())


def get_repair(db: Session, repair_id: uuid.UUID) -> Repair | None:
    return db.get(Repair, repair_id)


def create_repair(db: Session, asset_id: uuid.UUID, data: RepairCreate) -> Repair:
    """Создаёт запись о ремонте. status всегда planned — клиент его не передаёт
    (см. RepairCreate, там нет поля status)."""
    repair = Repair(
        asset_id=asset_id,
        repair_type=data.repair_type,
        cost=data.cost,
        executor=data.executor,
        started_at=data.started_at,
        status=RepairStatus.PLANNED,
    )
    db.add(repair)
    db.commit()
    db.refresh(repair)
    return repair


def update_repair(db: Session, repair: Repair, data: RepairUpdate) -> Repair:
    """Частично обновляет ремонт. Если среди переданных полей есть status и оно
    реально меняется — проверяет допустимость перехода по _ALLOWED_TRANSITIONS;
    при нарушении поднимает RepairInvalidTransitionError без изменений в БД."""
    update_data = data.model_dump(exclude_unset=True)

    new_status = update_data.get("status")
    if new_status is not None and new_status != repair.status:
        allowed = _ALLOWED_TRANSITIONS.get(repair.status, set())
        if new_status not in allowed:
            raise RepairInvalidTransitionError(
                f"Недопустимый переход статуса ремонта: {repair.status.value} → {new_status.value}"
            )

    for field, value in update_data.items():
        setattr(repair, field, value)

    db.commit()
    db.refresh(repair)
    return repair
