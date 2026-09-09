"""
API-роут дашборда руководства — B13a (неплановая мини-сессия после B13,
найдена по факту сверки контракта с Dev2 для F06).

GET /api/dashboard/executive — агрегат {open_tickets, average_resolution_hours,
    priority_breakdown} для карточек «Открытые заявки»/SLA/«Топ-3 проблемные
    категории» (последнее — суррогат через priority, см. schemas/dashboard.py).

Доступ: Executive+ (Executive, IT-Head, Admin) — тот же паттерн, что у
GET /api/monitoring/summary (п. 1.3 ТЗ).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import UserRole
from app.schemas.dashboard import ExecutiveSummary
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/executive",
    response_model=ExecutiveSummary,
    dependencies=[Depends(require_role(UserRole.EXECUTIVE, UserRole.IT_HEAD, UserRole.ADMIN))],
)
def get_executive_dashboard(db: Session = Depends(get_db)) -> ExecutiveSummary:
    return ExecutiveSummary(**dashboard_service.get_executive_summary(db))
