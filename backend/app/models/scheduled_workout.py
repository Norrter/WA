from datetime import date
from enum import Enum

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
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
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )

    program_day_id: Mapped[int] = mapped_column(
        ForeignKey("program_days.id", ondelete="CASCADE"),
        nullable=False,
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

    program: Mapped["Program"] = relationship(
        back_populates="scheduled_workouts",
    )

    program_day: Mapped["ProgramDay"] = relationship(
        back_populates="scheduled_workouts",
    )

    workout_sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="scheduled_workout",
        cascade="all, delete-orphan",
    )
