"""Сервисный слой для User — вне обычного CRUD (B04): здесь только логика,
специфичная для MAX-интеграции (B10). Обычный CRUD пользователей живёт в
app/api/users.py напрямую (см. B04), т.к. там нет сложной бизнес-логики,
которая оправдывала бы отдельный сервисный слой.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def get_or_create_shadow_user(
    db: Session,
    *,
    max_user_id: str,
    full_name: str | None = None,
    phone: str | None = None,
) -> User:
    """Находит существующего пользователя по max_user_id или phone, либо создаёт
    теневого пользователя (роль User, без department_id/login/password_hash — см. B10).

    Порядок поиска:
    1. По max_user_id — уже привязанный MAX-аккаунт.
    2. По phone (если передан и не пуст) — например, у сотрудника с существующей
       веб-учёткой уже указан телефон, совпадающий с тем, что передал MAX; в этом
       случае просто дозаполняем max_user_id у найденной записи, не создавая дубль.
    3. Если не найден нигде — создаём нового теневого пользователя.
    """
    user = db.scalar(select(User).where(User.max_user_id == max_user_id))
    if user is not None:
        return user

    if phone:
        user = db.scalar(select(User).where(User.phone == phone))
        if user is not None:
            user.max_user_id = max_user_id
            db.commit()
            db.refresh(user)
            return user

    user = User(
        full_name=full_name or "Пользователь MAX",
        role=UserRole.USER,
        max_user_id=max_user_id,
        phone=phone,
        department_id=None,
        login=None,
        password_hash=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
