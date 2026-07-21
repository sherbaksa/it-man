"""
FastAPI-зависимости для аутентификации/авторизации.

get_current_user — парсит access-токен из заголовка Authorization: Bearer,
возвращает текущего пользователя из БД. Используется как Depends(...) во
всех защищённых эндпоинтах.

require_role(...) появится в сессии B04 (Users CRUD + ролевая модель) —
здесь сознательно не добавляется, чтобы не выходить за рамки артефактов B03.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Валидирует access-токен из заголовка Authorization и возвращает пользователя.

    401, если токен отсутствует/невалиден/не access-токен, пользователь не найден
    или деактивирован (is_active=False).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен недействителен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = db.get(User, uuid.UUID(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
