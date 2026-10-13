from datetime import datetime

from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.models.base import Base


class UserRole(str, Enum):
    user = "user"
    # Тренер видит статистику всех пользователей
    coach = "coach"


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'coach')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Роль назначается по списку COACH_EMAILS при запуске сервера
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.user.value,
        server_default=UserRole.user.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def is_admin(self) -> bool:
        """Администратор задаётся списком ADMIN_EMAILS."""
        return self.email.strip().lower() in settings.admin_emails

    programs: Mapped[list["Program"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Program.user_id",
    )