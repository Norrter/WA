"""Общая настройка тестов.

Тесты работают с ОТДЕЛЬНОЙ базой: к имени основной базы добавляется
"_test" (workout_db -> workout_db_test). Она создаётся автоматически,
а перед каждым тестом все её таблицы очищаются. Основная база с вашими
данными не затрагивается.

Адрес можно задать явно переменной TEST_DATABASE_URL.
"""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url


DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://workout_user:workout_password"
    "@localhost:5432/workout_db"
)


def resolve_test_database_url() -> str:
    explicit = os.environ.get("TEST_DATABASE_URL")

    if explicit:
        return explicit

    env_file = Path(__file__).resolve().parents[2] / ".env"

    base = (
        os.environ.get("DATABASE_URL")
        or dotenv_values(env_file).get("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )

    url = make_url(base)

    return url.set(database=f"{url.database}_test").render_as_string(
        hide_password=False
    )


TEST_DATABASE_URL = resolve_test_database_url()

# Важно: выставить окружение ДО импорта приложения,
# чтобы оно подключилось к тестовой базе
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-0123456789"
os.environ["SQL_ECHO"] = "false"

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.database.session import AsyncSessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Exercise  # noqa: E402
from tests.helpers import register_and_login  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Создать тестовую базу (если её нет) и таблицы в ней."""
    url = make_url(TEST_DATABASE_URL)

    admin_engine = create_async_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )

    async with admin_engine.connect() as connection:
        exists = await connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )

        if not exists:
            await connection.execute(
                text(f'CREATE DATABASE "{url.database}"')
            )

    await admin_engine.dispose()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(prepare_database):
    """Перед каждым тестом база пустая, id начинаются с 1."""
    tables = ", ".join(
        f'"{table.name}"' for table in Base.metadata.sorted_tables
    )

    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")
        )


@pytest_asyncio.fixture
async def client():
    """HTTP-клиент, который ходит в приложение напрямую, без сети."""
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def alice(client):
    """Заголовки авторизации первого пользователя."""
    return await register_and_login(client, "alice")


@pytest_asyncio.fixture
async def bob(client):
    """Заголовки авторизации второго пользователя (чужой)."""
    return await register_and_login(client, "bob")


@pytest_asyncio.fixture
async def shared_exercise():
    """Общее упражнение без автора — как те, что были в базе раньше."""
    async with AsyncSessionLocal() as session:
        exercise = Exercise(
            name="Приседания со штангой",
            muscle_group="Ноги",
            equipment="Штанга",
        )

        session.add(exercise)
        await session.commit()

        return exercise.id
