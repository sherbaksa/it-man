# Платформа управления IT-инфраструктурой

Веб-приложение для управления IT-инфраструктурой медицинской организации:
инвентаризация оборудования, заявки, ОРД, мониторинг (Zabbix/Kaspersky),
интеграции с OpenProject/EspoCRM/n8n.

## Стек

- **Backend:** FastAPI, SQLAlchemy 2.0 (sync), PostgreSQL 16, Alembic, Celery + Redis, MinIO (S3-совместимое хранилище вложений)
- **Frontend:** React + TypeScript
- **Инфраструктура:** Docker Compose (разработка), деплой — RedOS-сервер

## Требования к окружению

- **Docker Desktop с бэкендом WSL2** (не Hyper-V) — обязательно на Windows.
- Backend разрабатывается и тестируется в контейнере / внутри WSL2. Нативный запуск backend (включая `pytest`) прямо на Windows-Python возможен, но не является основным сценарием и может потребовать дополнительной настройки окружения (см. раздел «Локальный запуск тестов на Windows» ниже) — рекомендуем контейнер как основной путь, чтобы не наступать на одни и те же грабли повторно.
- Свободные порты на хосте: `8000` (backend), `3000` (frontend), `5432` (Postgres), `6379` (Redis), `9000`/`9001` (MinIO). Если на машине уже установлен и запущен локальный PostgreSQL — остановите его службу перед стартом Docker-версии, иначе будет конфликт порта `5432` (см. раздел ниже).

## Быстрый старт

1. Скопируйте `.env.example` → `.env` и заполните значения (пароли, `SECRET_KEY` — сгенерируйте самостоятельно, не используйте `changeme` в проде).

2. Поднимите стек **с обязательным флагом `--env-file`** — Docker Compose не подхватывает `.env` из корня репозитория автоматически, когда compose-файл лежит в `infrastructure/`:

```bash
docker compose --env-file .env -f infrastructure/docker-compose.dev.yml up -d
```

3. Проверьте здоровье сервисов:

```bash
docker compose -f infrastructure/docker-compose.dev.yml ps
curl http://localhost:8000/health
```

Ожидается `{"status": "ok"}` и все сервисы (`db`, `redis`, `minio`, `backend`, `frontend`) в состоянии `healthy`/`Up`.

4. Примените миграции и заполните справочники:

```bash
docker compose -f infrastructure/docker-compose.dev.yml exec backend alembic upgrade head
docker compose -f infrastructure/docker-compose.dev.yml exec backend python -m app.scripts.seed_reference_data
```

5. Swagger UI: http://localhost:8000/api/docs

## `DATA_DISK_PATH`

Все volumes сервисов (`db`, `minio`) — bind-mount на путь, заданный переменной `DATA_DISK_PATH` в `.env`, а **не** анонимные Docker-volumes. Это сделано намеренно: на проде (RedOS-сервер) данные должны физически лежать на отдельном смонтированном диске, а не в дефолтном месте Docker — при переносе конфигурации на прод достаточно подставить путь к этому диску, не переписывая `docker-compose.*.yml`. Не оставляйте `DATA_DISK_PATH` пустым/дефолтным — иначе данные Postgres/MinIO окажутся в неожиданном месте на диске Docker.

## Тестовые данные

### Первый запуск — пароль admin выводится один раз

`seed_reference_data.py` при первом запуске создаёт пользователя `admin` со случайно сгенерированным паролем и печатает его в консоль:

```
  + Admin user created
  ==================================================
  login:    admin
  password: <случайно сгенерированный пароль>
  Сохрани этот пароль — он больше не будет показан!
  ==================================================
```

**Пароль нигде не сохраняется в открытом виде** — ни в БД (только хеш через `hash_password()`, argon2id), ни в файлах репозитория. Скопируйте его из вывода консоли при первом запуске сида. Повторный запуск `seed_reference_data.py` идемпотентен и не создаёт нового admin/пароль, если пользователь `admin` уже существует.

### Если пароль admin утерян

Если пароль был потерян (консоль не сохранена, БД пересоздана без повторного запуска сида и т.п.) — сбросьте его вручную через `hash_password()`, зайдя в контейнер backend:

```bash
docker compose -f infrastructure/docker-compose.dev.yml exec backend python
```

```python
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

db = SessionLocal()
admin = db.query(User).filter(User.login == "admin").one()
admin.password_hash = hash_password("НОВЫЙ_ПАРОЛЬ_ЗДЕСЬ")
db.commit()
```

### Тестовые роли

Для ручной проверки ролевой модели через Swagger создайте пользователей других ролей (`IT-Head`, `Engineer`, `Executive`) через `POST /api/users` под `admin` — см. `docs/api/openapi.json` за актуальным контрактом. Роль `User` не может логиниться в веб (создаётся автоматически через MAX-бота в будущей интеграции B18).

## Как обновить `docs/api/openapi.json`

После любой сессии, меняющей роуты или Pydantic-схемы, перегенерируйте контракт API — фронтенд (Dev2) ориентируется именно на этот файл, а не на пересказ в чате:

```bash
docker compose -f infrastructure/docker-compose.dev.yml exec backend python -m app.scripts.export_openapi
```

Локально (вне контейнера, например на Windows) — из корня репозитория, с `backend` в `PYTHONPATH`:

```powershell
$env:PYTHONPATH="backend"
python -m app.scripts.export_openapi
```

Закоммитьте изменённый `docs/api/openapi.json` вместе с кодом сессии.

## Локальный запуск тестов на Windows (вне контейнера)

Основной сценарий — тесты гоняются в контейнере/WSL2. Если всё же нужно запустить `pytest` локально из Windows-`.venv` (например, для быстрой итерации без пересборки образа):

1. Убедитесь, что контейнер `db` поднят и порт `5432` проброшен на хост (`docker compose -f infrastructure/docker-compose.dev.yml ps db`).
2. Если на машине установлен и запущен локальный PostgreSQL (частая ситуация после других проектов) — он может перехватывать порт `5432` раньше Docker. Проверьте:
   ```powershell
   netstat -ano | findstr :5432
   ```
   Если строк больше одной — остановите локальную службу Postgres на время работы (`Get-Service | Where-Object {$_.DisplayName -like "*postgres*"}`, затем `Stop-Service -Name "<имя>"`).
3. Переопределите хост БД (в `.env` для контейнеров используется имя сервиса `db`, недоступное с хоста напрямую):
   ```powershell
   $env:POSTGRES_HOST="localhost"
   pytest backend/tests/ -v
   ```
4. Установите зависимости backend в свой `.venv`, если ещё не сделано: `pip install -r backend/requirements.txt`.

Тесты используют отдельную БД `<POSTGRES_DB>_test` на том же сервере Postgres (создаётся автоматически, не пересекается с dev-данными).

## Структура репозитория

```
backend/           # FastAPI-приложение
  app/
    api/            # роутеры (auth, users, ...)
    models/         # SQLAlchemy-модели
    schemas/        # Pydantic-схемы
    services/       # бизнес-логика
    integrations/    # клиенты внешних систем (Zabbix, EspoCRM, ...)
    tasks/          # Celery-задачи
    core/           # конфиг, БД, безопасность, зависимости
    scripts/        # разовые скрипты (seed, export_openapi, ...)
  alembic/          # миграции БД
  tests/            # pytest
frontend/           # React + TypeScript SPA
infrastructure/     # docker-compose.dev.yml
deploy/             # прод-конфигурация (RedOS)
docs/
  api/openapi.json  # актуальный контракт API
  templates/        # .docx-шаблоны ОРД
.github/workflows/  # CI
```