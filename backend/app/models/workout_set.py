from sqlalchemy import Boolean, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    __table_args__ = (
        UniqueConstraint(
            "scheduled_workout_id",
            "program_exercise_id",
            "set_number",
            name="uq_workout_sets_workout_exercise_set_number",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    scheduled_workout_id: Mapped[int] = mapped_column(
        ForeignKey("scheduled_workouts.id", ondelete="CASCADE"),
        nullable=False,
    )

    program_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("program_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )

    set_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    weight: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    reps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    scheduled_workout: Mapped["ScheduledWorkout"] = relationship(
        back_populates="workout_sets",
    )

    program_exercise: Mapped["ProgramExercise"] = relationship(
        back_populates="workout_sets",
    )
