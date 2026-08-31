"""
Роутер аутентификации: /api/auth/login, /refresh, /logout.

Согласно ТЗ (раздел 4.1, раздел 7):
- access_token отдаётся в теле ответа (фронтенд хранит его в памяти, не в localStorage);
- refresh_token живёт только в HttpOnly+Secure+SameSite=Strict cookie, недоступен из JS;
- при /refresh refresh-токен ротируется (выдаётся новый, cookie перезаписывается).

Бизнес-правило (п. 3.1 ТЗ): роль User не может логиниться в веб — 403.

⚠️ Известное ограничение локальной разработки: cookie ставится с флагом Secure=True
(обязательное требование ТЗ раздел 7). Браузер не примет такую cookie по обычному
http://localhost без TLS — полноценная browser-проверка /refresh станет доступна
после HTTPS (сессии деплоя D01/D02). Через Swagger UI и pytest/httpx.Client это
не блокирует проверку критерия готовности B03.
"""
import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"  # cookie отправляется только на /api/auth/*, не на весь сайт


class LoginRequest(BaseModel):
    login: str
    password: str


class UserPublic(BaseModel):
    id: uuid.UUID
    role: UserRole
    full_name: str


class LoginResponse(BaseModel):
    access_token: str
    user: UserPublic


class AccessTokenResponse(BaseModel):
    access_token: str


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.JWT_REFRESH_TTL_DAYS * 24 * 60 * 60,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    """Проверяет логин/пароль, выдаёт access_token в теле ответа и refresh_token в cookie."""
    user = db.scalar(select(User).where(User.login == payload.login))

    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    # Бизнес-правило п. 3.1 ТЗ: роль User не может логиниться в веб
    if user.role == UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль User не имеет доступа к веб-интерфейсу",
        )

    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh_token)

    return LoginResponse(
        access_token=access_token,
        user=UserPublic(id=user.id, role=user.role, full_name=user.full_name),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    """Читает refresh_token из cookie, валидирует, ротирует (новый access + новый refresh)."""
    if refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh-токен отсутствует")

    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh-токен недействителен")

    user_id = payload.get("sub")
    user = db.get(User, uuid.UUID(user_id)) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или деактивирован",
        )

    # Ротация: cookie перезаписывается новым refresh-токеном, старое значение больше
    # не переиспользуется клиентом (единственная копия была в cookie, которую мы сейчас заменяем)
    new_access_token = create_access_token(user.id, user.role.value)
    new_refresh_token = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh_token)

    return AccessTokenResponse(access_token=new_access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Очищает refresh_token cookie."""
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)

@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """Текущий пользователь по access-токену — для восстановления профиля после reload страницы."""
    return UserPublic(id=current_user.id, role=current_user.role, full_name=current_user.full_name)
