# Схема базы данных

Актуально на сессию **B16** (миграции `c8ee68f1a13f` + `564fc4e19487` + `d9c574f44d1f` + `e8cff9f59e6b`).

## ER-диаграмма

```mermaid
erDiagram
    DEPARTMENT ||--o{ USER : "department_id"
    EQUIPMENT_TYPE ||--o{ ASSET : "type_id"
    USER ||--o{ ASSET : "responsible_user_id"
    ASSET ||--o{ MOVEMENT : "asset_id"
    USER ||--o{ MOVEMENT : "initiator_id"
    ASSET ||--o{ REPAIR : "asset_id"
    USER ||--o{ TICKET : "author_id"
    USER ||--o{ TICKET : "assignee_id"
    ASSET ||--o{ TICKET : "asset_id"
    TICKET ||--o{ TICKET : "merged_into_ticket_id"
    TICKET ||--o{ ATTACHMENT : "ticket_id"
    USER ||--o{ ATTACHMENT : "uploaded_by"
    DOCUMENT_TEMPLATE ||--o{ ORDER : "template_id"
    USER ||--o{ ORDER : "author_id"
    USER ||--o{ ORDER : "approver_id"
    ORDER ||--o{ ORDER_HISTORY : "order_id"
    USER ||--o{ ORDER_HISTORY : "changed_by"
    ASSET ||--o{ MONITORING_STATUS : "asset_id"
    USER ||--o{ AUDIT_LOG : "user_id"

    DEPARTMENT {
        uuid id PK
        string name
    }
    EQUIPMENT_TYPE {
        uuid id PK
        string name
    }
    USER {
        uuid id PK
        string full_name
        uuid department_id FK
        string position
        string role
        string login UK
        string phone UK
        string max_user_id UK
        string email UK
        string password_hash
        string espocrm_contact_id
        bool is_active
        timestamptz created_at
    }
    ASSET {
        uuid id PK
        string inventory_number UK
        uuid type_id FK
        string serial_number
        string model
        date purchase_date
        string status
        string location
        uuid responsible_user_id FK
        string ip_address
        string hostname
    }
    MOVEMENT {
        uuid id PK
        uuid asset_id FK
        string from_location
        string to_location
        uuid initiator_id FK
        timestamptz moved_at
        string comment
    }
    REPAIR {
        uuid id PK
        uuid asset_id FK
        string repair_type
        numeric cost
        string executor
        string executor_espocrm_id
        string status
        timestamptz started_at
        timestamptz finished_at
    }
    TICKET {
        uuid id PK
        string title
        string priority
        string status
        uuid author_id FK
        uuid assignee_id FK
        uuid asset_id FK
        string source
        string external_op_id
        string external_espo_id
        uuid merged_into_ticket_id FK
        timestamptz created_at
        timestamptz closed_at
    }
    ATTACHMENT {
        uuid id PK
        uuid ticket_id FK
        string file_name
        string content_type
        int size_bytes
        string storage_key
        uuid uploaded_by FK
    }
    DOCUMENT_TEMPLATE {
        uuid id PK
        string name
        string type
        string file_path
        jsonb field_schema
        string min_approver_role
    }
    ORDER {
        uuid id PK
        string type
        uuid template_id FK
        jsonb fields
        string status
        uuid author_id FK
        uuid approver_id FK
        timestamptz created_at
        timestamptz approved_at
        int version
    }
    ORDER_HISTORY {
        uuid id PK
        uuid order_id FK
        int version
        jsonb fields
        uuid changed_by FK
        timestamptz changed_at
    }
    MONITORING_STATUS {
        uuid id PK
        uuid asset_id FK
        string host_identifier
        string status
        string last_value
        string source
        timestamptz checked_at
        int history_retention_hours
    }
    MONITORING_STATUS_HISTORY {
        uuid id PK
        string host_identifier
        string status
        string last_value
        string source
        timestamptz checked_at
    }
    INTEGRATION_LOG {
        uuid id PK
        string system
        string direction
        string endpoint
        int status_code
        jsonb payload
        timestamptz created_at
    }
    AUDIT_LOG {
        uuid id PK
        uuid user_id FK
        string action
        string entity_type
        string entity_id
        timestamptz created_at
    }
```

## Таблицы

| Таблица | Назначение | Сессия |
|---|---|---|
| `department` | Справочник подразделений | B01 |
| `equipment_type` | Справочник типов оборудования | B01 |
| `user` | Пользователи системы | B01 (B10: `max_user_id`, nullable-поля) |
| `asset` | Единицы оборудования (инвентаризация) | B01 |
| `movement` | История перемещений оборудования | B02 |
| `repair` | Учёт ремонтов | B02 |
| `ticket` | Заявки (инциденты/запросы) | B02 |
| `attachment` | Вложения к заявкам (MinIO), сверх ТЗ | B02 |
| `document_template` | Шаблоны документов ОРД | B02 |
| `order` | Заявки на согласование документов ОРД | B02 |
| `order_history` | История версий Order | B02 |
| `monitoring_status` | Текущий статус мониторинга хоста (Zabbix/Kaspersky) | B02 (B12: `history_retention_hours`) |
| `monitoring_status_history` | Append-only журнал статусов хоста (запись на каждый опрос), сверх ТЗ | B12 |
| `integration_log` | Журнал запросов к внешним системам | B02 |
| `audit_log` | Журнал аудита действий пользователей | B02 |

## Известные технические детали / договорённости

- `document_template.type` (тип `document_template_type`) переиспользуется в `order.type` — один и тот же enum-тип Postgres на две таблицы.
- `document_template.min_approver_role` переиспользует `user_role` (тот же enum-тип, что и `user.role`), а не заводит отдельный.
- Все Postgres enum-типы, кроме `user_role` и `asset_status` (принадлежат миграции `c8ee68f1a13f`, B01), удаляются вручную в `downgrade()` миграции `564fc4e19487` — `op.drop_table()` сам их не удаляет.
- `attachment` — сущность сверх базового ТЗ, введена под хранение вложений к заявкам через MinIO (сессия B10a).
- `user` (B10): `department_id`, `login`, `password_hash` — nullable, потому что у «теневых» пользователей, автоматически создаваемых по обращению из MAX, этих данных нет (без синтетических заглушек). `max_user_id` (уникальный, nullable) — основной идентификатор такого пользователя; `phone` для этого не используется, т.к. MAX его не передаёт.
- `monitoring_status_history` (B12): append-only, без внешних ключей — связь с `monitoring_status` логическая, по паре `(host_identifier, source)`. Использует те же enum-типы `monitoring_health_status` и `monitoring_source`, что и `monitoring_status` (в модели `create_type=False`). Индекс `(host_identifier, checked_at)` под выборку истории хоста за период. Глубина хранения — `settings.MONITORING_HISTORY_DEFAULT_RETENTION_HOURS` либо `monitoring_status.history_retention_hours` для конкретного хоста; очистка — периодическая Celery-задача `cleanup_monitoring_history`.
- `document_template.field_schema` — `jsonb`; на уровне приложения это упорядоченный массив описаний полей (`list[dict]`, сессия B15), а не объект. Тип столбца в БД не менялся, миграции не было.
- Сессии B14–B16 (ОРД) не меняли схему БД: миграций нет.