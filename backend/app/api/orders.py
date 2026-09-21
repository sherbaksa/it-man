"""
API-роуты для Order (ОРД — организационно-распорядительные документы) — по
п. 4.4 и разделу 8 ТЗ.

GET /api/orders — список с фильтрами (status, type) и пагинацией.
POST /api/orders — создание черновика, статус всегда draft, автор — current_user.
PATCH /api/orders/{id} — частичное обновление: правка fields (только автор),
    смена status (автор — pending_approval/executed, согласующий — approved/rejected,
    в зависимости от DocumentTemplate.min_approver_role). Вся логика допустимости
    конкретного действия для конкретной роли — внутри order_service, здесь только
    маппинг исключений в HTTP-коды (по аналогии с api/tickets.py).
GET /api/orders/{id}/history — версии документа для Timeline (B14a).

GET /api/orders/{id}/render?format=docx|pdf — рендер документа (B15, раздел 8 ТЗ):
    - format=docx: синхронно, docxtpl работает в памяти (доли секунды) —
      сразу отдаёт файл, 200.
    - format=pdf: конвертация через LibreOffice headless — тяжёлая операция
      (эмпирически 5-30с), поэтому НЕ выполняется внутри HTTP-запроса —
      ставится в очередь Celery (render_order_pdf.delay), эндпоинт сразу
      отвечает 202 с task_id и ссылкой на статус (см. decisions.md, решение
      сессии B15: "202 + отдельный эндпоинт статуса", а не синхронное ожидание).
GET /api/orders/{id}/render/status/{task_id} — опрашивается фронтом до
    готовности: 202 (ещё не готово) -> 200 с бинарным PDF (готово) -> 500
    (конвертация упала).

Доступ: Engineer+ (Engineer, IT-Head, Executive, Admin) — п. 1.3 ТЗ. В отличие
от tickets.py, сюда дополнительно включён Executive — он может быть
согласующим для Order с DocumentTemplate.min_approver_role=Executive (см.
order_service._APPROVER_RANKS), и без доступа к роутеру never смог бы дойти
до PATCH, чтобы согласовать документ. Тот же уровень доступа сохранён и для
render/render-status — Executive должен иметь возможность посмотреть/скачать
документ, который согласовывает.
"""
import base64
import uuid
from typing import Literal

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.document_template import DocumentTemplateType
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import (
    OrderCreate,
    OrderHistoryRead,
    OrderListResponse,
    OrderRead,
    OrderUpdate,
)
from app.services import document_render_service, order_service
from app.services.order_service import OrderInvalidTransitionError, OrderPermissionError
from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import render_order_pdf

router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
    dependencies=[
        Depends(
            require_role(
                UserRole.ENGINEER, UserRole.IT_HEAD, UserRole.EXECUTIVE, UserRole.ADMIN
            )
        )
    ],
)


@router.get("", response_model=OrderListResponse)
def get_orders(
    status_: OrderStatus | None = Query(None, alias="status"),
    type_: DocumentTemplateType | None = Query(None, alias="type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    items, total = order_service.list_orders(
        db,
        status=status_,
        type_=type_,
        page=page,
        page_size=page_size,
    )
    return OrderListResponse(items=[OrderRead.model_validate(item) for item in items], total=total)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderRead:
    order = order_service.create_order(db, data, author_id=current_user.id)
    return OrderRead.model_validate(order)


@router.patch("/{order_id}", response_model=OrderRead)
def patch_order(
    order_id: uuid.UUID,
    data: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderRead:
    """Роль Engineer+ (включая Executive) уже обеспечена dependencies роутера;
    точечная проверка "кто именно может это конкретное действие" (автор vs
    согласующий, с учётом min_approver_role) выполняется внутри order_service."""
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    try:
        updated = order_service.update_order(db, order, data, current_user=current_user)
    except OrderPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except OrderInvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return OrderRead.model_validate(updated)


@router.get("/{order_id}/history", response_model=list[OrderHistoryRead])
def get_order_history(order_id: uuid.UUID, db: Session = Depends(get_db)) -> list[OrderHistoryRead]:
    """Версии документа в хронологическом порядке — для Timeline на карточке (F07)."""
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")
    history = order_service.get_order_history(db, order_id)
    return [OrderHistoryRead.model_validate(item) for item in history]


@router.get("/{order_id}/render")
def render_order(
    order_id: uuid.UUID,
    format: Literal["docx", "pdf"] = Query(...),
    db: Session = Depends(get_db),
) -> Response:
    """format=docx — синхронный рендер (docxtpl, в памяти). format=pdf —
    тяжёлая конвертация уходит в Celery, эндпоинт сразу отвечает 202 (см.
    decisions.md, решение B15)."""
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    if format == "docx":
        try:
            docx_bytes = document_render_service.render_order_docx(order)
        except document_render_service.TemplateFileNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{order.id}.docx"'},
        )

    # format == "pdf"
    task = render_order_pdf.delay(str(order.id))
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "task_id": task.id,
            "status_url": f"/api/orders/{order.id}/render/status/{task.id}",
        },
    )


@router.get("/{order_id}/render/status/{task_id}")
def get_render_status(order_id: uuid.UUID, task_id: str, db: Session = Depends(get_db)) -> Response:
    """Опрашивается фронтом после 202 от /render?format=pdf. Проверка
    order_id (а не только task_id) — чтобы эндпоинт был осмысленно привязан
    к конкретному документу, а не принимал произвольный task_id без контекста."""
    order = order_service.get_order(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    result = AsyncResult(task_id, app=celery_app)

    if result.state in ("PENDING", "STARTED", "RETRY"):
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": "pending"})

    if result.state == "FAILURE":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка конвертации в PDF: {result.result}",
        )

    if result.state == "SUCCESS":
        payload = result.result
        pdf_bytes = base64.b64decode(payload["content_b64"])
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
        )

    # Неизвестное промежуточное состояние Celery — трактуем как "ещё не готово"
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"status": result.state.lower()})
