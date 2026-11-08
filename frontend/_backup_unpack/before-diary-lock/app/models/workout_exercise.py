"""Упражнение в конкретной тренировке.

Пока человек ничего не менял, тренировка идёт по дню программы и этих
строк у неё нет. Как только он во время тренировки добавил, заменил,
убрал упражнение или поменял число подходов, план дня копируется сюда
(scheduled_workouts.custom_plan = true) и дальше тренировка живёт по
своему списку. Сама программа при этом не меняется.
"""

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    __table_args__ = (
        CheckConstraint("sets BETWEEN 1 AND 20", name="ck_workout_exercises_sets"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    scheduled_workout_id: Mapped[int] = mapped_column(
        ForeignKey("scheduled_workouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Строка программы, из которой пришло упражнение. Пусто, если его
    # добавили во время тренировки или строку потом удалили из программы
    program_exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("program_exercises.id", ondelete="SET NULL"),
        nullable=True,
    )

    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sets: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    exercise: Mapped["Exercise"] = relationship(lazy="joined")
