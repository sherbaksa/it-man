"""
Тесты Celery-задачи render_order_pdf (раздел 8 ТЗ, сессии B15, B16).

Задача запускается через .apply() — выполнение в текущем процессе без Redis и
воркера; результат и состояние приходят в EagerResult. БД не используется:
SessionLocal подменяется фейком, а order_service.get_order и функции
document_render_service — заглушками. Реальный LibreOffice не запускается.
"""
import base64
import uuid
from types import SimpleNamespace

import pytest

from app.services.document_render_service import (
    DocumentConversionError,
    TemplateFileNotFoundError,
)
from app.tasks import document_tasks
from app.tasks.celery_app import celery_app
from app.tasks.document_tasks import render_order_pdf


class _FakeDb:
    """Заменяет сессию БД: задача обязана закрыть её в finally."""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def fake_db(monkeypatch: pytest.MonkeyPatch) -> _FakeDb:
    db = _FakeDb()
    monkeypatch.setattr(document_tasks, "SessionLocal", lambda: db)
    return db


def _patch_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    *,
    order: SimpleNamespace | None,
    docx_bytes: bytes = b"PK fake docx",
    pdf_bytes: bytes = b"%PDF-1.4 fake pdf",
    render_error: Exception | None = None,
    convert_error: Exception | None = None,
) -> dict[str, list]:
    """Подменяет get_order и обе функции рендера. Возвращает журнал вызовов."""
    calls: dict[str, list] = {"get_order": [], "render": [], "convert": []}

    def _get_order(db: object, order_id: uuid.UUID) -> SimpleNamespace | None:
        calls["get_order"].append((db, order_id))
        return order

    def _render(order_arg: object) -> bytes:
        calls["render"].append(order_arg)
        if render_error is not None:
            raise render_error
        return docx_bytes

    def _convert(docx_arg: bytes) -> bytes:
        calls["convert"].append(docx_arg)
        if convert_error is not None:
            raise convert_error
        return pdf_bytes

    monkeypatch.setattr(document_tasks.order_service, "get_order", _get_order)
    monkeypatch.setattr(document_tasks.document_render_service, "render_order_docx", _render)
    monkeypatch.setattr(document_tasks.document_render_service, "convert_docx_to_pdf", _convert)
    return calls


def test_render_order_pdf_returns_filename_and_base64_pdf(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeDb
) -> None:
    order = SimpleNamespace(id=uuid.uuid4())
    pdf_bytes = b"%PDF-1.4 fake pdf"
    docx_bytes = b"PK rendered docx"
    calls = _patch_pipeline(monkeypatch, order=order, docx_bytes=docx_bytes, pdf_bytes=pdf_bytes)

    eager = render_order_pdf.apply(args=[str(order.id)])

    assert eager.state == "SUCCESS"
    assert eager.result == {
        "filename": f"{order.id}.pdf",
        "content_b64": base64.b64encode(pdf_bytes).decode("ascii"),
    }
    # Заказ ищется той же сессией и по UUID из строки; в конвертацию уходит
    # ровно результат docxtpl-рендера
    assert calls["get_order"] == [(fake_db, order.id)]
    assert calls["render"] == [order]
    assert calls["convert"] == [docx_bytes]
    assert fake_db.closed is True


def test_render_order_pdf_fails_when_order_not_found(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeDb
) -> None:
    calls = _patch_pipeline(monkeypatch, order=None)
    missing_id = uuid.uuid4()

    eager = render_order_pdf.apply(args=[str(missing_id)])

    assert eager.state == "FAILURE"
    assert isinstance(eager.result, LookupError)
    assert str(missing_id) in str(eager.result)
    assert calls["render"] == []
    assert calls["convert"] == []
    assert fake_db.closed is True


def test_render_order_pdf_fails_when_conversion_fails(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeDb
) -> None:
    """Ошибка LibreOffice -> задача в FAILURE (эндпоинт статуса отдаст 500)."""
    order = SimpleNamespace(id=uuid.uuid4())
    _patch_pipeline(
        monkeypatch, order=order, convert_error=DocumentConversionError("soffice упал")
    )

    eager = render_order_pdf.apply(args=[str(order.id)])

    assert eager.state == "FAILURE"
    assert isinstance(eager.result, DocumentConversionError)
    assert "soffice упал" in str(eager.result)
    assert fake_db.closed is True


def test_render_order_pdf_fails_when_template_file_is_missing(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeDb
) -> None:
    order = SimpleNamespace(id=uuid.uuid4())
    calls = _patch_pipeline(
        monkeypatch, order=order, render_error=TemplateFileNotFoundError("нет шаблона")
    )

    eager = render_order_pdf.apply(args=[str(order.id)])

    assert eager.state == "FAILURE"
    assert isinstance(eager.result, TemplateFileNotFoundError)
    assert calls["convert"] == []  # до конвертации дело не дошло
    assert fake_db.closed is True


def test_render_order_pdf_fails_on_invalid_order_id(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeDb
) -> None:
    calls = _patch_pipeline(monkeypatch, order=None)

    eager = render_order_pdf.apply(args=["not-a-uuid"])

    assert eager.state == "FAILURE"
    assert isinstance(eager.result, ValueError)
    assert calls["get_order"] == []
    assert fake_db.closed is True


def test_render_order_pdf_is_registered_in_celery_app() -> None:
    """Регрессия на готчу B11: autodiscover_tasks для этой структуры пакетов не
    работает, модули задач регистрируются явно через conf.imports. Без этого
    воркер не узнает задачу, а вызов из API молча зависнет в PENDING."""
    assert "app.tasks.document_tasks" in celery_app.conf.imports
    assert "app.tasks.document_tasks.render_order_pdf" in celery_app.tasks
