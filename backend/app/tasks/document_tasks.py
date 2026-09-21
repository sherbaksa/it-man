"""Celery-задача конвертации ОРД-документа (Order) в PDF — раздел 8 ТЗ,
сессия B15.

Вынесена в отдельный модуль от monitoring_tasks.py по смыслу (документы, а
не мониторинг), по аналогии с разделением services (order_service отдельно
от monitoring_service).

Решение B15 (см. decisions.md): рендер PDF асинхронный — 202 + отдельный
эндпоинт статуса (а не синхронное ожидание внутри HTTP-запроса), т.к.
конвертация через LibreOffice — не быстрая операция (эмпирически в этой
сессии — ~5-30с в зависимости от загрузки машины) и не должна занимать поток
backend-процесса. Задача возвращает результат в виде base64-строки — так он
попадает в Celery result backend (Redis) как обычный JSON-совместимый тип,
без необходимости в общем volume между backend и worker контейнерами для
передачи файла (у worker вообще нет volumes — см. решение B15 про build
context)."""
import base64
import uuid

from app.core.database import SessionLocal
from app.services import document_render_service, order_service
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True)
def render_order_pdf(self, order_id: str) -> dict:
    """Рендерит Order в .docx (docxtpl) и конвертирует в .pdf (LibreOffice
    headless). Возвращает {"filename": ..., "content_b64": ...} — читается
    эндпоинтом статуса (GET /api/orders/{id}/render/status/{task_id})."""
    db = SessionLocal()
    try:
        order = order_service.get_order(db, uuid.UUID(order_id))
        if order is None:
            raise LookupError(f"Order {order_id} не найден на момент рендера")

        docx_bytes = document_render_service.render_order_docx(order)
        pdf_bytes = document_render_service.convert_docx_to_pdf(docx_bytes)

        return {
            "filename": f"{order.id}.pdf",
            "content_b64": base64.b64encode(pdf_bytes).decode("ascii"),
        }
    finally:
        db.close()
