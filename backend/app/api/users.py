"""
Роутер управления пользователями: /api/users.

Согласно ТЗ (раздел 4, «/api/users... только Admin»): полный CRUD доступен
исключительно роли Admin. Удаление — мягкое, через is_active=False (сама запись
не удаляется физически, чтобы не терять историю в связанных сущностях — Ticket,
Order, AuditLog и т.д., которые ссылаются на User).

Бизнес-правило (план B04, шаг 4): для роли User запись создаётся автоматически
при первом обращении через MAX (реализуется в B18) — здесь POST не блокирует
создание User с минимальным набором полей, специальной логики под MAX пока нет.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


def _get_user_or_404(user_id: uuid.UUID, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Список всех пользователей (включая деактивированных — фильтрацию делает фронтенд)."""
    return list(db.scalars(select(User)))


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> User:
    return _get_user_or_404(user_id, db)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.login == payload.login))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Логин уже занят")

    user = User(
        full_name=payload.full_name,
        department_id=payload.department_id,
        position=payload.position,
        role=payload.role,
        phone=payload.phone,
        email=payload.email,
        login=payload.login,
        password_hash=hash_password(payload.password),
        espocrm_contact_id=payload.espocrm_contact_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = _get_user_or_404(user_id, db)

    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password:
        user.password_hash = hash_password(password)

    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Мягкое удаление — is_active=False, запись не удаляется физически."""
    user = _get_user_or_404(user_id, db)
    user.is_active = False
    db.commit()