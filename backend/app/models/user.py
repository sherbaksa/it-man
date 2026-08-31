"""Модель User — по п. 3.1 ТЗ. Роли: Admin, IT-Head, Engineer, Executive, User.
Бизнес-правило (реализуется на уровне auth в B03): роль User не может логиниться в веб —
для неё запись создаётся автоматически при первом обращении через MAX-бота.

B10: добавлено поле max_user_id — основной идентификатор теневого пользователя из MAX
(в отличие от phone, которого MAX не передаёт). department_id/login/password_hash
стали nullable: у теневого пользователя из MAX этих данных нет и не должно быть —
без синтетических заглушек (решение B10, вариант B).
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    IT_HEAD = "IT-Head"
    ENGINEER = "Engineer"
    EXECUTIVE = "Executive"
    USER = "User"

if TYPE_CHECKING:
    from app.models.department import Department

class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        {"comment": "Пользователи системы (сотрудники учреждения)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("department.id"), nullable=True, index=True
    )
    department: Mapped["Department | None"] = relationship()

    position: Mapped[str | None] = mapped_column(String(150), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    max_user_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    login: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    espocrm_contact_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} login={self.login!r} role={self.role}>"
