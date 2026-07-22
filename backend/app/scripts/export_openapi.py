"""
Экспорт актуальной OpenAPI-схемы приложения в docs/api/openapi.json.

Запуск: python -m app.scripts.export_openapi
Фиксирует контракт API для фронтенда (Dev2) — обновлять после любой сессии,
меняющей роуты/схемы (см. Посессионный_план_IT_Platform.md, раздел 7,
«Сохранение контекста между сессиями»).
"""
import json
from pathlib import Path

from app.main import app

# docs/api/ — на два уровня выше backend/app/scripts/ (корень репозитория)
OUTPUT_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"


def export_openapi() -> None:
    schema = app.openapi()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OpenAPI-схема сохранена: {OUTPUT_PATH}")
