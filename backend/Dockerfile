# === Стадия сборки зависимостей ===
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# === Runtime-стадия ===
FROM python:3.12-slim
WORKDIR /app

# LibreOffice headless — конвертация .docx -> .pdf для ОРД (docxtpl + soffice,
# раздел 8 ТЗ, сессия B15). Один и тот же образ используется и для backend,
# и для worker (docker-compose: build context ../backend для обоих) — backend
# сам LibreOffice не запускает (docx собирается через docxtpl без soffice),
# но проще держать одну спецификацию на оба контейнера, чем поддерживать два
# Dockerfile. Устанавливается ДО useradd/USER — apt-get требует root.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libreoffice \
    && rm -rf /var/lib/apt/lists/*

# Непривилегированный пользователь — не запускаем процесс от root
RUN useradd --create-home --shell /bin/bash appuser

# Копируем установленные пакеты в домашнюю директорию appuser (не root!),
# чтобы у него были права на чтение и исполнение
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]