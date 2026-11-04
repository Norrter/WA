import json
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


# .env лежит в корне проекта (на уровень выше backend/),
# путь не зависит от того, из какой папки запущено приложение
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str

    # Секрет для подписи JWT. Обязателен: задаётся в .env
    secret_key: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Адреса фронтенда, которым разрешено обращаться к API.
    # В .env задаётся как JSON: CORS_ORIGINS=["http://localhost:5173"]
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Email-адреса тренеров через запятую:
    # COACH_EMAILS=coach@example.com,second@example.com
    # Тренер видит статистику всех пользователей. Роли выставляются
    # при каждом запуске сервера
    coach_emails: Annotated[list[str], NoDecode] = []

    # Email-адреса администраторов через запятую:
    # ADMIN_EMAILS=me@example.com
    # Администратор видит админ-панель и может менять любые данные
    admin_emails: Annotated[list[str], NoDecode] = []

    # Пороги для меток в кабинете тренера:
    # «Проверить» — выполнение плана ниже порога или долго нет тренировок;
    # «Оценить прогресс» — тренируется, но новых рекордов давно нет
    coach_adherence_threshold: float = Field(0.7, ge=0, le=1)
    coach_inactive_days: int = Field(5, ge=1)
    coach_stagnation_days: int = Field(28, ge=7)

    # Печатать ли SQL-запросы в консоль
    sql_echo: bool = False

    # ----- Почта -----
    # Адрес сайта: из него собираются ссылки в письмах
    frontend_url: str = "http://localhost:5173"

    # SMTP-сервер для писем (подтверждение почты, заявки).
    # Пока SMTP_HOST пустой, письма не отправляются, а печатаются
    # в консоль сервера — удобно при разработке.
    smtp_host: str = ""
    # 465 — шифрование сразу (SSL), 587 — через STARTTLS
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    # Адрес отправителя; по умолчанию — SMTP_USER
    smtp_from: str = ""
    smtp_from_name: str = "Greek's Gym"

    # Сколько часов действует ссылка подтверждения почты
    email_verify_hours: int = Field(48, ge=1)

    # Куда присылать новые заявки с главной. Пусто — тренерам (COACH_EMAILS)
    lead_notify_emails: Annotated[list[str], NoDecode] = []

    @field_validator("database_url")
    @classmethod
    def use_asyncpg_driver(cls, value: str) -> str:
        # Хостинги (например, Render) выдают адрес вида postgresql://...
        # или postgres://..., а приложению нужен драйвер asyncpg
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix):]

        return value

    @field_validator("coach_emails", "admin_emails", "lead_notify_emails", mode="before")
    @classmethod
    def split_coach_emails(cls, value):
        # Принимаем и строку через запятую, и JSON-список
        if isinstance(value, str):
            value = value.strip()

            if value.startswith("["):
                value = json.loads(value)
            else:
                value = value.split(",")

        return [
            email.strip().lower()
            for email in value
            if email and email.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
