"""
Сервисный слой для Asset — по п. 4.2 ТЗ и сессии B06 посессионного плана.

list_assets() — листинг с фильтрами (status, type_id, location, search) и пагинацией.
get_asset() — получение одного актива с подгруженными movements/repairs.
create_asset() — создание нового актива.
"""
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import Asset, AssetStatus
from app.models.movement import Movement
from app.schemas.asset import AssetCreate


def _apply_filters(
    query: Any,
    *,
    status: AssetStatus | None,
    type_id: uuid.UUID | None,
    location: str | None,
    search: str | None,
) -> Any:
    """Применяет общий набор фильтров и к count-запросу, и к запросу за данными —
    чтобы условия не расходились между total и items."""
    if status is not None:
        query = query.where(Asset.status == status)
    if type_id is not None:
        query = query.where(Asset.type_id == type_id)
    if location is not None:
        query = query.where(Asset.location == location)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Asset.inventory_number.ilike(pattern),
                Asset.model.ilike(pattern),
                Asset.serial_number.ilike(pattern),
            )
        )
    return query


def list_assets(
    db: Session,
    *,
    status: AssetStatus | None = None,
    type_id: uuid.UUID | None = None,
    location: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Asset], int]:
    """Возвращает (items, total) с учётом фильтров и пагинации.

    search ищет по inventory_number/model/serial_number через ILIKE (регистронезависимо).
    total считается отдельным агрегатным запросом (SELECT count(*)), без подгрузки строк —
    не тянет из БД полные объекты Asset только ради подсчёта количества.
    """
    count_query = _apply_filters(
        select(func.count()).select_from(Asset),
        status=status, type_id=type_id, location=location, search=search,
    )
    total = db.execute(count_query).scalar_one()

    query = select(Asset).options(
        selectinload(Asset.type), selectinload(Asset.responsible_user)
    )
    query = _apply_filters(
        query, status=status, type_id=type_id, location=location, search=search
    )
    query = query.order_by(Asset.inventory_number).offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(query).scalars().all())

    return items, total


def get_asset(db: Session, asset_id: uuid.UUID) -> Asset | None:
    """Возвращает актив по id с подгруженными type, responsible_user, movements, repairs."""
    query = (
        select(Asset)
        .where(Asset.id == asset_id)
        .options(
            selectinload(Asset.type),
            selectinload(Asset.responsible_user),
            selectinload(Asset.movements).selectinload(Movement.initiator),
            selectinload(Asset.repairs),
        )
    )
    return db.execute(query).scalar_one_or_none()


def create_asset(db: Session, data: AssetCreate) -> Asset:
    """Создаёт новый актив. Валидацию существования type_id оставляем БД (FK constraint)."""
    asset = Asset(
        inventory_number=data.inventory_number,
        type_id=data.type_id,
        serial_number=data.serial_number,
        model=data.model,
        purchase_date=data.purchase_date,
        location=data.location,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
