"""
Pydantic-схема DocumentTemplate — по п. 3.7 ТЗ, сессия B14a (справочник
шаблонов для формы создания Order на фронте, F07).

DocumentTemplateRead включает field_schema (нужен фронту для динамической
генерации формы) и min_approver_role (нужен фронту, чтобы понимать заранее,
кто должен согласовывать документ этого типа) — но не file_path, это
внутренняя деталь рендера (B15), фронту не нужна и не должна быть публичной.

field_schema — list[dict], не dict (исправлено в B15, см. models/document_template.py).
"""
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.document_template import DocumentTemplateType
from app.models.user import UserRole


class DocumentTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: DocumentTemplateType
    field_schema: list[dict]
    min_approver_role: UserRole
