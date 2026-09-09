"""
Pydantic-схемы для агрегированного дашборда руководства — B13a (неплановая
мини-сессия, найдена по факту межкомандной сверки с Dev2 после B13).

Причина появления: Executive получает 403 на /api/tickets (Engineer+ по
п. 4.3 ТЗ), поэтому фронт не может посчитать «Открытые заявки»/SLA сам —
нужен отдельный агрегированный эндпоинт, как и предполагалось риском
сессии F06 в посессионном плане.

priority_breakdown используется как временная замена отсутствующих в модели
Ticket "категорий" (п. 5 ТЗ упоминает «Топ-3 проблемные категории», но в
модели Ticket, п. 3.5 ТЗ, поля category/type нет — согласовано с Dev2 как
осознанный суррогат до возможного расширения ТЗ).
"""
from pydantic import BaseModel


class TicketPriorityBreakdown(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class ExecutiveSummary(BaseModel):
    """Ответ GET /api/dashboard/executive.

    open_tickets — count(status IN (new, in_progress)).
    average_resolution_hours — среднее (closed_at - created_at) в часах по
        тикетам со status=done, closed_at за последние 30 дней (фиксированное
        окно, согласовано в B13a — без query-параметра периода).
    priority_breakdown — разбивка по priority среди тикетов, ещё не закрытых
        (status NOT IN (done, rejected)).
    """

    open_tickets: int
    average_resolution_hours: float
    priority_breakdown: TicketPriorityBreakdown
