"""
Pydantic-схемы пользователя — по п. 3.1 ТЗ.

UserCreate — тело POST /api/users (создание, включая пароль в открытом виде,
который будет захеширован в сервисном слое).
UserUpdate — тело PATCH /api/users/{id} (все поля опциональны, включая пароль).
UserRead — тело ответа (без password_hash!).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str
    department_id: uuid.UUID
    position: str | None = None
    role: UserRole
    phone: str | None = None
    email: EmailStr | None = None
    login: str
    password: str
    espocrm_contact_id: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    department_id: uuid.UUID | None = None
    position: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    espocrm_contact_id: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    department_id: uuid.UUID
    position: str | None
    role: UserRole
    phone: str | None
    email: str | None
    login: str
    espocrm_contact_id: str | None
    is_active: bool
    created_at: datetime