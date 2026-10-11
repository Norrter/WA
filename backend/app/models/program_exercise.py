from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProgramExercise(Base):
    __tablename__ = "program_exercises"

    __table_args__ = (
        UniqueConstraint(
            "program_day_id",
            "order_index",
            name="uq_program_exercises_program_day_id_order_index",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    program_day_id: Mapped[int] = mapped_column(
        ForeignKey("program_days.id", ondelete="CASCADE"),
        nullable=False,
    )

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
    )

    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    sets: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    target_reps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    target_weight: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    rest_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    program_day: Mapped["ProgramDay"] = relationship(
        back_populates="exercises",
    )

    exercise: Mapped["Exercise"] = relationship(
        back_populates="program_exercises",
    )

    workout_sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="program_exercise",
        cascade="all, delete-orphan",
    )