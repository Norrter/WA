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

    # Строка плана, по которой сделан подход. Пусто, если упражнение
    # потом убрали из программы — подход при этом остаётся в истории
    program_exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("program_exercises.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Само упражнение: по нему считаются история и рекорды. Упражнение
    # с записанными подходами удалить нельзя. Проверка отложена до конца
    # транзакции, поэтому удаление аккаунта целиком проходит
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", deferrable=True, initially="DEFERRED"),
        nullable=False,
        index=True,
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

    program_exercise: Mapped["ProgramExercise | None"] = relationship(
        back_populates="workout_sets",
    )
