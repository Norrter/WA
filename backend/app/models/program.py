from datetime import datetime

from sqlalchemy import DateTime, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # NULL — общий шаблон: его видят все, а себе берут копию
    # через POST /programs/{id}/copy
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    # Программу назначил тренер: пока сотрудничество активно, менять её
    # может только он, клиент — смотреть, заниматься и копировать
    assigned_by_coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Из какой программы сделана копия
    source_program_id: Mapped[int | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    days: Mapped[list["ProgramDay"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramDay.order_index",
    )

    user: Mapped["User | None"] = relationship(
        back_populates="programs",
        foreign_keys=[user_id],
    )

    # Тренировки не удаляются вместе с программой: выполненные остаются
    # в истории, у них program_id становится пустым (ON DELETE SET NULL)
    scheduled_workouts: Mapped[list["ScheduledWorkout"]] = relationship(
        back_populates="program",
        passive_deletes=True,
    )