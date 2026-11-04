"""Пересчёт нагрузки подходов, когда меняется тип упражнения или
человек впервые указывает вес тела."""

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exercise import Exercise
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.models.workout_set import WorkoutSet


def load_expression(load_type: str):
    """SQL-выражение нагрузки — то же, что app.core.load.compute_load."""
    if load_type == "bodyweight":
        return func.coalesce(WorkoutSet.body_weight, 0) + WorkoutSet.weight

    if load_type == "assisted":
        return case(
            (WorkoutSet.body_weight.is_(None), 0.0),
            else_=func.greatest(0.0, WorkoutSet.body_weight - WorkoutSet.weight),
        )

    return WorkoutSet.weight


async def recalc_exercise(session: AsyncSession, exercise: Exercise) -> None:
    """Тип нагрузки упражнения поменяли — пересчитать его подходы."""
    await session.execute(
        update(WorkoutSet)
        .where(WorkoutSet.exercise_id == exercise.id)
        .values(load=load_expression(exercise.load_type))
        .execution_options(synchronize_session=False)
    )


async def fill_body_weight(session: AsyncSession, user: User) -> None:
    """Человек указал вес тела: подходы со своим весом, записанные
    без него, получают этот вес и пересчитываются."""
    if user.body_weight is None:
        return

    for load_type in ("bodyweight", "assisted"):
        exercise_ids = select(Exercise.id).where(Exercise.load_type == load_type)
        workout_ids = select(ScheduledWorkout.id).where(ScheduledWorkout.user_id == user.id)

        await session.execute(
            update(WorkoutSet)
            .where(
                WorkoutSet.body_weight.is_(None),
                WorkoutSet.exercise_id.in_(exercise_ids),
                WorkoutSet.scheduled_workout_id.in_(workout_ids),
            )
            .values(body_weight=user.body_weight)
            .execution_options(synchronize_session=False)
        )

        await session.execute(
            update(WorkoutSet)
            .where(
                WorkoutSet.exercise_id.in_(exercise_ids),
                WorkoutSet.scheduled_workout_id.in_(workout_ids),
            )
            .values(load=load_expression(load_type))
            .execution_options(synchronize_session=False)
        )
