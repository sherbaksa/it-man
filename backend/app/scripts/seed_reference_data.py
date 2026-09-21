"""Скрипт наполнения справочных данных для локальной разработки (сессия B02).
Идемпотентен: повторный запуск не создаёт дублей — каждая запись проверяется
по уникальному полю перед вставкой.

Хеширование пароля: hash_password() из app.core.security (argon2id) —
единая точка хеширования во всём проекте (техдолг снят в сессии B03).

B15: TEMPLATES_DIR переехал в backend/app/templates/orders/ — теперь это
настоящие .docx-шаблоны с Jinja2-плейсхолдерами, версионируемые в git и
попадающие в образ через существующий `COPY . .` в Dockerfile (без отдельного
volume/COPY — см. решение сессии B15: build context backend/worker не
включает docs/ из корня репозитория, поэтому путь из раздела 8 ТЗ
(docs/templates/ + /app/templates/orders/ volume) заменён на этот, с тем же
результатом). Раньше (B02) здесь были .docx-заглушки, генерируемые в рантайме
в backend/storage/ (не в git) — то временное решение снято.

Запуск (внутри контейнера backend):
    python -m app.scripts.seed_reference_data
"""
import secrets
import string
from pathlib import Path

from docx import Document
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.department import Department
from app.models.document_template import DocumentTemplate, DocumentTemplateType
from app.models.equipment_type import EquipmentType
from app.models.user import User, UserRole

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "orders"

DEPARTMENTS = ["ИТ-отдел", "Бухгалтерия", "Регистратура", "Административно-хозяйственная часть"]

EQUIPMENT_TYPES = [
    "Компьютер",
    "Принтер",
    "Сетевое оборудование",
    "Сервер",
    "МФУ",
    "Прочее",
]

# Реальные field_schema для purchase_request/write_off_act — введены в B15
# (см. document_render_service.py и docs/templates-эквивалент в
# backend/app/templates/orders/). Ключи и порядок полей взяты из уже
# реализованной формы Dev2 (frontend/src/api/orders.ts, orderTemplates) —
# чтобы при переходе с мока на реальный API форма F07 не менялась.
_PURCHASE_REQUEST_FIELDS = [
    {"key": "recipientTitle", "label": "Должность и организация адресата", "type": "text",
     "required": True, "defaultValue": "Руководителю организации"},
    {"key": "recipientName", "label": "Ф.И.О. адресата", "type": "text",
     "required": True, "defaultValue": "Фамилия И.О."},
    {"key": "authorPosition", "label": "Должность автора (после «от»)", "type": "text",
     "required": True, "defaultValue": "программиста"},
    {"key": "authorDisplayName", "label": "Ф.И.О. автора для документа", "type": "text",
     "placeholder": "Если не заполнено, используется имя текущего пользователя"},
    {"key": "department", "label": "Подразделение", "type": "text",
     "required": True, "placeholder": "Например, регистратура"},
    {"key": "itemName", "label": "Наименование оборудования", "type": "text", "required": True},
    {"key": "quantity", "label": "Количество", "type": "number", "required": True},
    {"key": "estimatedCost", "label": "Ориентировочная стоимость, ₽", "type": "number"},
    {"key": "requiredDate", "label": "Требуемая дата", "type": "date", "required": True},
    {"key": "justification", "label": "Обоснование закупки", "type": "textarea", "required": True},
]

_WRITE_OFF_ACT_FIELDS = [
    {"key": "inventoryNumber", "label": "Инвентарный номер", "type": "text",
     "required": True, "placeholder": "INV-00000"},
    {"key": "equipmentName", "label": "Наименование оборудования", "type": "text", "required": True},
    {"key": "commissionDate", "label": "Дата ввода в эксплуатацию", "type": "date"},
    {"key": "reason", "label": "Причина списания", "type": "select", "required": True,
     "options": ["Физический износ", "Моральное устаревание", "Неремонтопригодность", "Утрата"]},
    {"key": "technicalConclusion", "label": "Техническое заключение", "type": "textarea", "required": True},
]


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def seed_departments(db: Session) -> dict[str, Department]:
    result = {}
    for name in DEPARTMENTS:
        existing = db.scalar(select(Department).where(Department.name == name))
        if existing:
            result[name] = existing
            continue
        dept = Department(name=name)
        db.add(dept)
        db.flush()
        result[name] = dept
        print(f"  + Department: {name}")
    return result


def seed_equipment_types(db: Session) -> None:
    for name in EQUIPMENT_TYPES:
        existing = db.scalar(select(EquipmentType).where(EquipmentType.name == name))
        if existing:
            continue
        db.add(EquipmentType(name=name))
        print(f"  + EquipmentType: {name}")


def seed_admin_user(db: Session, it_department: Department) -> None:
    existing = db.scalar(select(User).where(User.login == "admin"))
    if existing:
        print("  = Admin user already exists, skipping")
        return

    password = generate_password()
    admin = User(
        full_name="Администратор Системы",
        department_id=it_department.id,
        position="Системный администратор",
        role=UserRole.ADMIN,
        login="admin",
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(admin)
    print("  + Admin user created")
    print("  " + "=" * 50)
    print("  login:    admin")
    print(f"  password: {password}")
    print("  Сохрани этот пароль — он больше не будет показан!")
    print("  " + "=" * 50)


def create_stub_docx(path: Path, title: str) -> None:
    """Заглушка используется только для work_order — его реального шаблона
    с плейсхолдерами пока нет (не входило в область B15, см. известные
    проблемы отчёта B14a про min_approver_role этого же шаблона)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = Document()
    document.add_heading(title, level=1)
    document.add_paragraph("Заглушка шаблона — реальные плейсхолдеры будут добавлены позже.")
    document.save(str(path))


def seed_document_templates(db: Session) -> None:
    templates = [
        ("Заявка на закупку", DocumentTemplateType.PURCHASE_REQUEST, "purchase_request.docx",
         UserRole.IT_HEAD, _PURCHASE_REQUEST_FIELDS),
        ("Акт списания", DocumentTemplateType.WRITE_OFF_ACT, "write_off_act.docx",
         UserRole.IT_HEAD, _WRITE_OFF_ACT_FIELDS),
        ("Наряд на работу", DocumentTemplateType.WORK_ORDER, "work_order.docx",
         UserRole.ENGINEER, []),
    ]
    for name, doc_type, filename, min_role, field_schema in templates:
        existing = db.scalar(select(DocumentTemplate).where(DocumentTemplate.name == name))
        if existing:
            continue

        file_path = TEMPLATES_DIR / filename
        if not file_path.exists():
            # Реальные purchase_request.docx/write_off_act.docx должны быть
            # в репозитории (backend/app/templates/orders/) — если их здесь
            # нет, это ошибка деплоя/сборки, а не повод сгенерировать заглушку
            # поверх настоящего шаблона. Заглушку создаём только для
            # work_order, у которого реального шаблона ещё нет.
            if doc_type == DocumentTemplateType.WORK_ORDER:
                create_stub_docx(file_path, name)
            else:
                raise FileNotFoundError(
                    f"Ожидался настоящий шаблон {file_path}, но файл не найден. "
                    "Проверь, что backend/app/templates/orders/ скопирован в образ."
                )

        db.add(
            DocumentTemplate(
                name=name,
                type=doc_type,
                file_path=str(file_path),
                field_schema=field_schema,
                min_approver_role=min_role,
            )
        )
        print(f"  + DocumentTemplate: {name} ({file_path})")


def main() -> None:
    db = SessionLocal()
    try:
        print("Departments:")
        departments = seed_departments(db)

        print("Equipment types:")
        seed_equipment_types(db)

        print("Admin user:")
        seed_admin_user(db, departments["ИТ-отдел"])

        print("Document templates:")
        seed_document_templates(db)

        db.commit()
        print("Готово.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
