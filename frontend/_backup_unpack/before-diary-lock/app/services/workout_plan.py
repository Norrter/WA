"""Свой план тренировки: правки во время тренировки без изменения программы."""

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout
from app.models.workout_exercise import WorkoutExercise
from app.models.workout_set import WorkoutSet


async def workout_items(session: AsyncSession, workout_id: int) -> list[WorkoutExercise]:
    return list(
        (
            await session.scalars(
                select(WorkoutExercise)
                .where(WorkoutExercise.scheduled_workout_id == workout_id)
                .order_by(WorkoutExercise.order_index, WorkoutExercise.id)
            )
        ).all()
    )


async def customize(session: AsyncSession, workout: ScheduledWorkout) -> None:
    """Скопировать план дня в саму тренировку (если ещё не скопирован).

    Уже записанные подходы привязываются к своим строкам. Подходы по
    упражнениям, которых в плане нет, становятся отдельными строками.
    """
    if workout.custom_plan:
        return

    plan: list[ProgramExercise] = []

    if workout.program_day_id is not None:
        plan = list(
            (
                await session.scalars(
                    select(ProgramExercise)
                    .where(ProgramExercise.program_day_id == workout.program_day_id)
                    .order_by(ProgramExercise.order_index, ProgramExercise.id)
                )
            ).all()
        )

    order = 0

    for item in plan:
        row = WorkoutExercise(
            scheduled_workout_id=workout.id,
            exercise_id=item.exercise_id,
            program_exercise_id=item.id,
            order_index=order,
            sets=max(1, min(item.sets, 20)),
            target_reps=item.target_reps,
            target_reps_max=item.target_reps_max,
            target_weight=item.target_weight,
            rest_seconds=item.rest_seconds,
            notes=item.notes,
        )
        session.add(row)
        await session.flush()
        order += 1

        await session.execute(
            update(WorkoutSet)
            .where(
                WorkoutSet.scheduled_workout_id == workout.id,
                WorkoutSet.program_exercise_id == item.id,
                WorkoutSet.workout_exercise_id.is_(None),
            )
            .values(workout_exercise_id=row.id)
        )

    # Подходы вне плана: каждое упражнение — своя строка
    leftovers = (
        await session.execute(
            select(WorkoutSet.exercise_id, func.count())
            .where(
                WorkoutSet.scheduled_workout_id == workout.id,
                WorkoutSet.workout_exercise_id.is_(None),
            )
            .group_by(WorkoutSet.exercise_id)
            .order_by(func.min(WorkoutSet.id))
        )
    ).all()

    for exercise_id, count in leftovers:
        row = WorkoutExercise(
            scheduled_workout_id=workout.id,
            exercise_id=exercise_id,
            order_index=order,
            sets=max(1, min(count, 20)),
        )
        session.add(row)
        await session.flush()
        order += 1

        await session.execute(
            update(WorkoutSet)
            .where(
                WorkoutSet.scheduled_workout_id == workout.id,
                WorkoutSet.exercise_id == exercise_id,
                WorkoutSet.workout_exercise_id.is_(None),
            )
            .values(workout_exercise_id=row.id)
        )

    workout.custom_plan = True
    await session.flush()


async def get_item(
    session: AsyncSession,
    workout: ScheduledWorkout,
    item_id: int,
) -> WorkoutExercise:
    item = await session.get(WorkoutExercise, item_id)

    if item is None or item.scheduled_workout_id != workout.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout exercise not found",
        )

    return item


async def item_has_sets(session: AsyncSession, item: WorkoutExercise) -> bool:
    found = await session.scalar(
        select(WorkoutSet.id).where(WorkoutSet.workout_exercise_id == item.id).limit(1)
    )
    return found is not None


async def renumber(session: AsyncSession, workout_id: int) -> None:
    for index, item in enumerate(await workout_items(session, workout_id)):
        item.order_index = index
    await session.flush()
