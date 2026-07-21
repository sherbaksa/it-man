"""
Криптографические примитивы для аутентификации.

- hash_password/verify_password: argon2id через passlib (см. ТЗ раздел 7).
- create_access_token/create_refresh_token/decode_token: JWT на python-jose.

Payload токенов:
  access:  {"sub": <user_id str>, "role": <str>, "type": "access", "exp": ...}
  refresh: {"sub": <user_id str>, "type": "refresh", "jti": <uuid str>, "exp": ...}

"jti" в refresh-токене зарезервирован под будущую ротацию/чёрный список
(инвалидация конкретного refresh-токена при /refresh и /logout) — на этом
этапе (B03) фактическая инвалидация делается только "по факту выдачи нового"
на уровне cookie (перезапись), полноценный server-side revocation list —
из области будущих сессий, если понадобится (см. риски B03 в плане).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

JWT_ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    """Хеширует пароль по argon2id (дефолт passlib для схемы 'argon2')."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Сверяет пароль с хешем. Не бросает исключений на некорректном хеше — возвращает False."""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except ValueError:
        return False


def _create_token(
    subject: str,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Access-токен, TTL берётся из settings.JWT_ACCESS_TTL_MIN (см. .env)."""
    return _create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.JWT_ACCESS_TTL_MIN),
        extra_claims={"role": role},
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Refresh-токен, TTL берётся из settings.JWT_REFRESH_TTL_DAYS. jti — под будущую ротацию/revocation."""
    return _create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.JWT_REFRESH_TTL_DAYS),
        extra_claims={"jti": str(uuid.uuid4())},
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Декодирует и валидирует токен (подпись + exp). Возвращает payload или None, если невалиден."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
