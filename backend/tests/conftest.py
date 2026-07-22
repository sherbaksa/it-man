"""
Общая тестовая инфраструктура для backend/tests.

Использует отдельную тестовую БД Postgres (создаётся автоматически на том же
сервере, что и dev-БД, под именем "<POSTGRES_DB>_test") — тесты не трогают
dev-данные, риск из плана B05 закрыт.

Стек синхронный (SQLAlchemy sync engine, обычный TestClient), pytest-asyncio
не используется — соответствует фактической sync-архитектуре backend,
заложенной в B01/B03 (план B05 упоминал pytest-asyncio, но фактический код
репозитория синхронный — приоритет отдан коду, как договорились).
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  регистрирует все модели в Base.metadata
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app as fastapi_app
from app.models.department import Department
from app.models.user import User, UserRole

# Тестовая БД — отдельное имя на том же сервере Postgres, чтобы не задеть dev-данные.
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/itplatform_test"


def _create_test_database() -> None:
    """Создаёт тестовую БД, если она ещё не существует (idempotent)."""
    admin_url = settings.DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    test_db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    except ProgrammingError:
        pass  # БД уже существует — нормальная ситуация при повторных запусках
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def test_engine():
    """Engine на тестовую БД: создаёт БД (если нужно) и все таблицы один раз на сессию тестов."""
    _create_test_database()
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Изолированная сессия на тест: внешняя транзакция + SAVEPOINT.
    После commit() внутри тестируемого кода SAVEPOINT переоткрывается,
    а в конце теста внешняя транзакция откатывается целиком —
    dev-БД и другие тесты не затрагиваются.
    """
    connection = test_engine.connect()
    outer_transaction = connection.begin()
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = session_factory()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session: Session, transaction: object) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient с подменённой зависимостью get_db на тестовую сессию.

    base_url="https://testserver" — иначе httpx-клиент не примет и не будет
    хранить refresh_token cookie (Secure=True, см. auth.py), т.к. по умолчанию
    TestClient работает на http://testserver, а Secure-cookie не действуют
    на не-TLS соединениях даже в тестовом ASGI-транспорте.
    """

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app, base_url="https://testserver") as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()

@pytest.fixture()
def department(db_session: Session) -> Department:
    dept = Department(name="IT-отдел (тест)")
    db_session.add(dept)
    db_session.commit()
    db_session.refresh(dept)
    return dept


@pytest.fixture()
def admin_user(db_session: Session, department: Department) -> User:
    user = User(
        full_name="Тестовый Админ",
        department_id=department.id,
        role=UserRole.ADMIN,
        login="test_admin",
        password_hash=hash_password("TestAdmin123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def engineer_user(db_session: Session, department: Department) -> User:
    user = User(
        full_name="Тестовый Инженер",
        department_id=department.id,
        role=UserRole.ENGINEER,
        login="test_engineer",
        password_hash=hash_password("TestEngineer123!"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
