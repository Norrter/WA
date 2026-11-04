"""Связь тренера с клиентом и заметки тренера."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CoachingStatus(str, Enum):
    # тренер добавил email, который ещё не зарегистрирован
    invited = "invited"
    # клиент закреплён за тренером, тренер видит его данные
    active = "active"
    # закрыта без сотрудничества (старые приглашения)
    declined = "declined"
    # сотрудничество завершено, история тренировок остаётся у клиента
    ended = "ended"


class CoachClient(Base):
    __tablename__ = "coach_clients"

    __table_args__ = (
        CheckConstraint(
            "status IN ('invited', 'active', 'declined', 'ended')",
            name="ck_coach_clients_status",
        ),
        # У клиента не больше одного активного тренера
        Index(
            "uq_coach_clients_one_active_coach",
            "client_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        # Один тренер не добавляет один адрес дважды
        Index(
            "uq_coach_clients_one_pending_invite",
            "coach_id",
            func.lower(text("invited_email")),
            unique=True,
            postgresql_where=text("status = 'invited'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    coach_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Пусто, пока человек с этим email не зарегистрировался
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    invited_email: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CoachingStatus.invited.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Когда связь стала активной (или была закрыта)
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    coach: Mapped["User"] = relationship(foreign_keys=[coach_id])
    client: Mapped["User | None"] = relationship(foreign_keys=[client_id])


class CoachNote(Base):
    """Заметка тренера о работе с клиентом. Клиент видит только
    заметки с shared = true («Видна клиенту»)."""

    __tablename__ = "coach_notes"

    id: Mapped[int] = mapped_column(primary_key=True)

    coach_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    client_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Заметка видна клиенту (в профиле и на главной)
    shared: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
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

    __table_args__ = (
        Index("ix_coach_notes_coach_client", "coach_id", "client_id"),
    )
