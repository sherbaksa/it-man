"""
API-роуты для Asset (оборудование) — по п. 4.2 ТЗ.

GET /api/assets — список с фильтрами (status, type_id, location, search) и пагинацией.
GET /api/assets/{id} — детальная карточка с movements[]/repairs[].
POST /api/assets — создание.
PATCH /api/assets/{id} — частичное обновление, автосоздаёт Movement при смене status/location.
DELETE /api/assets/{id} — мягкое удаление (status=written_off), с проверкой правила
    об открытых заявках; доступ уже, чем у остальных методов — только IT-Head/Admin.

Доступ: Engineer+ (Engineer, IT-Head, Admin) — см. п. 1.3 ТЗ "Роли и права доступа".
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.asset import AssetStatus
from app.models.user import User, UserRole
from app.schemas.asset import AssetCreate, AssetDetail, AssetListResponse, AssetRead, AssetUpdate
from app.services import asset_service
from app.services.asset_service import AssetDuplicateError, AssetHasOpenTicketsError

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

@router.get("/export")
def export_assets(
    status_: AssetStatus | None = Query(None, alias="status"),
    type_id: uuid.UUID | None = None,
    location: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Те же фильтры, что у GET /api/assets, но без пагинации — .xlsx-отчёт целиком."""
    items, _ = asset_service.list_assets(
        db,
        status=status_,
        type_id=type_id,
        location=location,
        search=search,
        page=1,
        page_size=100_000,
    )
    buffer = asset_service.export_assets_workbook(items)
    filename = f"assets-{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset(asset_id: uuid.UUID, db: Session = Depends(get_db)) -> AssetDetail:
    asset = asset_service.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Актив не найден")
    return AssetDetail.model_validate(asset)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(data: AssetCreate, db: Session = Depends(get_db)) -> AssetRead:
    try:
        asset = asset_service.create_asset(db, data)
    except AssetDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AssetRead.model_validate(asset)

@router.patch("/{asset_id}", response_model=AssetDetail)
def patch_asset(
    asset_id: uuid.UUID,
    data: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetDetail:
    """Роль — Engineer+ (уже обеспечено dependencies роутера)."""
    asset = asset_service.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Актив не найден")
    try:
        updated = asset_service.update_asset(db, asset, data, initiator_id=current_user.id)
    except AssetHasOpenTicketsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AssetDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AssetDetail.model_validate(updated)

@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.IT_HEAD, UserRole.ADMIN))],
)
def delete_asset(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Мягкое удаление: переводит актив в status=written_off через тот же сервис,
    что и PATCH — с той же проверкой правила об открытых заявках и с той же
    автозаписью Movement. Роль — IT-Head/Admin (уже, чем общий Engineer+ роутера)."""
    asset = asset_service.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Актив не найден")
    try:
        asset_service.update_asset(
            db, asset, AssetUpdate(status=AssetStatus.WRITTEN_OFF), initiator_id=current_user.id
        )
    except AssetHasOpenTicketsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
