"""
SQLAlchemy 2.0 engine, declarative Base и sessionmaker.
Подключение к БД настраивается через переменную окружения DATABASE_URL.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: выдаёт сессию БД и гарантированно закрывает её после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()