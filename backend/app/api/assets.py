"""
API-роуты для Asset (оборудование) — по п. 4.2 ТЗ.

GET /api/assets — список с фильтрами (status, type_id, location, search) и пагинацией.
GET /api/assets/{id} — детальная карточка с movements[]/repairs[].
POST /api/assets — создание.

Доступ: Engineer+ (Engineer, IT-Head, Admin) — см. п. 1.3 ТЗ "Роли и права доступа".
DELETE и PATCH — появятся в сессии B07.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.asset import AssetStatus
from app.models.user import UserRole
from app.schemas.asset import AssetCreate, AssetDetail, AssetListResponse, AssetRead
from app.services import asset_service

router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
    dependencies=[Depends(require_role(UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.ADMIN))],
)


@router.get("", response_model=AssetListResponse)
def get_assets(
    status_: AssetStatus | None = Query(None, alias="status"),
    type_id: uuid.UUID | None = None,
    location: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AssetListResponse:
    items, total = asset_service.list_assets(
        db,
        status=status_,
        type_id=type_id,
        location=location,
        search=search,
        page=page,
        page_size=page_size,
    )
    return AssetListResponse(items=[AssetRead.model_validate(item) for item in items], total=total)


@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> AssetDetail:
    asset = asset_service.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Актив не найден")
    return AssetDetail.model_validate(asset)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(data: AssetCreate, db: Session = Depends(get_db)) -> AssetRead:
    asset = asset_service.create_asset(db, data)
    return AssetRead.model_validate(asset)
