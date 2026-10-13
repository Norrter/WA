from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WorkoutStatus(str, Enum):
    planned = "planned"
    completed = "completed"
    skipped = "skipped"


class ScheduledWorkout(Base):
    __tablename__ = "scheduled_workouts"

    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'completed', 'skipped')",
            name="ck_scheduled_workouts_status",
        ),
        CheckConstraint(
            "wellbeing BETWEEN 1 AND 5",
            name="ck_scheduled_workouts_wellbeing",
        ),
        CheckConstraint(
            "difficulty BETWEEN 1 AND 10",
            name="ck_scheduled_workouts_difficulty",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Владелец тренировки. Хранится отдельно от программы, чтобы история
    # оставалась у человека, даже если программу удалили
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Пусто, если программу или день потом удалили
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
    )

    program_day_id: Mapped[int | None] = mapped_column(
        ForeignKey("program_days.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Названия на момент тренировки — на случай, если программу удалят
    program_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    day_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    # Обратная связь клиента после тренировки
    # самочувствие: 1 — плохо ... 5 — отлично
    wellbeing: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # субъективная сложность: 1 — очень легко ... 10 — на пределе
    difficulty: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="planned",
    )

    program: Mapped["Program | None"] = relationship(
        back_populates="scheduled_workouts",
    )

    program_day: Mapped["ProgramDay | None"] = relationship(
        back_populates="scheduled_workouts",
    )

    workout_sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="scheduled_workout",
        cascade="all, delete-orphan",
    )
