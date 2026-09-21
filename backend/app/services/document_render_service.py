"""
Сервис рендера документов ОРД (Order) — docxtpl + LibreOffice headless, по
разделу 8 ТЗ, сессия B15 посессионного плана.

Два независимых шага:
  1. render_order_docx() — подстановка Order.fields в .docx-шаблон через
     docxtpl. Работает полностью в памяти, занимает доли секунды — вызывается
     СИНХРОННО прямо из api/orders.py для format=docx.
  2. convert_docx_to_pdf() — конвертация уже отрендеренного .docx в .pdf через
     LibreOffice headless (subprocess). Это тяжёлая операция (LibreOffice
     стартует не мгновенно) — вызывается ТОЛЬКО из Celery-задачи
     (app/tasks/document_tasks.py), никогда напрямую из HTTP-обработчика,
     чтобы не блокировать backend-процесс (решение B15: 202 + отдельный
     эндпоинт статуса, см. decisions.md).

Хранение: по разделу 8 ТЗ готовый .docx/.pdf нигде не кэшируется — рендерится
заново на каждый запрос, чтобы не рассинхронизироваться с Order.fields при
правках черновика. Постоянно хранится только сам шаблон
(DocumentTemplate.file_path, backend/app/templates/orders/ — версионируется
в git, см. решение B15 про build context backend/worker).
"""
import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from docxtpl import DocxTemplate

from app.models.order import Order


class TemplateFileNotFoundError(Exception):
    """DocumentTemplate.file_path указывает на несуществующий файл на диске —
    ошибка конфигурации данных/деплоя (шаблон не попал в образ), а не
    пользователя. Обрабатывается в api/orders.py как 500 Internal Server Error."""


class DocumentConversionError(Exception):
    """LibreOffice завершился с ненулевым кодом возврата, не создал ожидаемый
    .pdf-файл, либо не уложился в таймаут. Поднимается внутри Celery-задачи —
    задача переходит в состояние FAILURE, эндпоинт статуса отдаёт понятную
    ошибку (см. tasks/document_tasks.py)."""


# Таймаут на однократный запуск soffice. Раздел 8 ТЗ конкретное значение не
# оговаривает; 60с выбрано с большим запасом для текущих 1-страничных
# шаблонов (см. риск сессии B15 в посессионном плане про доустановку
# LibreOffice в образ — сам процесс конвертации для таких шаблонов занимает
# на практике 2-5с, запас нужен на случай холодного старта soffice).
_LIBREOFFICE_TIMEOUT_SECONDS = 120


def render_order_docx(order: Order) -> bytes:
    """Подставляет Order.fields в .docx-шаблон (Order.template.file_path)
    через docxtpl. Требует, чтобы order.template уже был подгружен
    (selectinload — см. order_service.get_order). Возвращает готовый .docx
    как bytes — не пишет на диск, чтобы не плодить временные файлы на
    синхронном (HTTP) пути."""
    template_path = Path(order.template.file_path)
    if not template_path.is_file():
        raise TemplateFileNotFoundError(
            f"Файл шаблона не найден: {template_path} (DocumentTemplate.id={order.template_id})"
        )

    doc = DocxTemplate(str(template_path))
    doc.render(order.fields)

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def convert_docx_to_pdf(docx_bytes: bytes) -> bytes:
    """Конвертирует .docx (bytes) в .pdf (bytes) через LibreOffice headless.

    ВАЖНО: вызывать только из Celery-задачи (worker), никогда из
    HTTP-обработчика — soffice стартует не мгновенно и на время конвертации
    блокирует процесс, в котором выполняется (см. шапку файла, decisions.md).

    -env:UserInstallation=... — обязателен: без явного профиля soffice
    пытается создать его в $HOME/.config/libreoffice, что в контейнере при
    первом запуске зависает намертво (ждёт диалог, которого headless-режим
    никогда не покажет) — воспроизведено эмпирически в этой же сессии B15.
    Профиль создаётся заново на каждый вызов (свой tempdir) — иначе
    параллельные вызовы (несколько заказов на рендер одновременно) будут
    ждать друг друга на общем lock-файле профиля.
    --norestore — отключает диалог восстановления документов после
    предыдущего аварийного завершения soffice (та же причина: диалог
    невозможно закрыть в headless-режиме, процесс зависнет)."""
    with (
        tempfile.TemporaryDirectory() as tmp_dir,
        tempfile.TemporaryDirectory() as profile_dir,
    ):
        tmp_dir_path = Path(tmp_dir)
        docx_path = tmp_dir_path / "source.docx"
        docx_path.write_bytes(docx_bytes)

        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--norestore",
                    f"-env:UserInstallation=file://{profile_dir}",
                    "--convert-to", "pdf",
                    "--outdir", str(tmp_dir_path),
                    str(docx_path),
                ],
                capture_output=True,
                timeout=_LIBREOFFICE_TIMEOUT_SECONDS,
                check=False,
                env={**os.environ, "SAL_USE_VCLPLUGIN": "svp"},
            )
        except subprocess.TimeoutExpired as exc:
            raise DocumentConversionError(
                f"LibreOffice не завершился за {_LIBREOFFICE_TIMEOUT_SECONDS}с"
            ) from exc

        pdf_path = tmp_dir_path / "source.pdf"
        if result.returncode != 0 or not pdf_path.is_file():
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise DocumentConversionError(
                f"LibreOffice завершился с кодом {result.returncode}: {stderr}"
            )

        return pdf_path.read_bytes()
