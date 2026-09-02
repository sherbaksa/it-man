"""
Схема справочника исполнителей заявок — мини-сессия B10b.

TicketAssigneeRead — узкая проекция User (id, full_name), НЕ полная UserRead:
намеренно не отдаём phone/email/login/role и т.д. Engineer/IT-Head через этот
эндпоинт — только то, что нужно для выбора исполнителя в UI (см. риск в ТЗ
раздел 7: доступ к таблице User по ролям Admin/IT-Head — этот эндпоинт не
нарушает принцип, т.к. отдаёт не всю сущность, а минимальную проекцию).
"""
import uuid

from pydantic import BaseModel, ConfigDict


class TicketAssigneeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
