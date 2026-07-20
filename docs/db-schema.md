# Схема базы данных

Актуально на сессию **B02** (миграции `c8ee68f1a13f` + `564fc4e19487`).

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
        string role
        string login UK
        string phone UK
        string email UK
        string password_hash
        string espocrm_contact_id
        bool is_active
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
| `user` | Пользователи системы | B01 |
| `asset` | Единицы оборудования (инвентаризация) | B01 |
| `movement` | История перемещений оборудования | B02 |
| `repair` | Учёт ремонтов | B02 |
| `ticket` | Заявки (инциденты/запросы) | B02 |
| `attachment` | Вложения к заявкам (MinIO), сверх ТЗ | B02 |
| `document_template` | Шаблоны документов ОРД | B02 |
| `order` | Заявки на согласование документов ОРД | B02 |
| `order_history` | История версий Order | B02 |
| `monitoring_status` | Текущий статус мониторинга хоста (Zabbix/Kaspersky) | B02 |
| `integration_log` | Журнал запросов к внешним системам | B02 |
| `audit_log` | Журнал аудита действий пользователей | B02 |

## Известные технические детали / договорённости

- `document_template.type` (тип `document_template_type`) переиспользуется в `order.type` — один и тот же enum-тип Postgres на две таблицы.
- `document_template.min_approver_role` переиспользует `user_role` (тот же enum-тип, что и `user.role`), а не заводит отдельный.
- Все Postgres enum-типы, кроме `user_role` и `asset_status` (принадлежат миграции `c8ee68f1a13f`, B01), удаляются вручную в `downgrade()` миграции `564fc4e19487` — `op.drop_table()` сам их не удаляет.
- `attachment` — сущность сверх базового ТЗ, введена под хранение вложений к заявкам через MinIO (сессия B10a).