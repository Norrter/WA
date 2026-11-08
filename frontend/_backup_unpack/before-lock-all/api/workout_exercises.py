"""Правки плана во время тренировки.

Добавить, заменить, убрать упражнение, поменять число подходов или
порядок. Меняется только эта тренировка — программа остаётся прежней.
Каждый запрос возвращает тренировку целиком.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import apply_changes, get_owned_workout, get_visible_exercise
from app.api.scheduled_workouts import workout_detail
from app.core.dependencies import get_current_user, require_open_diary
from app.database.session import get_session
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.models.workout_exercise import WorkoutExercise
from app.schemas.scheduled_workout import ScheduledWorkoutDetailResponse
from app.schemas.workout_exercise import (
    WorkoutExerciseCreate,
    WorkoutExerciseMove,
    WorkoutExercisePatch,
)
from app.services.workout_plan import (
    customize,
    get_item,
    item_has_sets,
    renumber,
    workout_items,
)


router = APIRouter(
    prefix="/scheduled-workouts/{scheduled_workout_id}",
    tags=["Workout Exercises"],
    # с неподтверждённой почтой — только просмотр
    dependencies=[Depends(require_open_diary)],
)


async def editable_workout(
    scheduled_workout_id: int,
    session: AsyncSession,
    user: User,
) -> ScheduledWorkout:
    workout = await get_owned_workout(scheduled_workout_id, session, user)
    await customize(session, workout)
    return workout


async def finish(session: AsyncSession, workout: ScheduledWorkout) -> dict:
    await session.commit()
    await session.refresh(workout)
    return await workout_detail(session, workout)


@router.post("/customize", response_model=ScheduledWorkoutDetailResponse)
async def customize_workout(
    scheduled_workout_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Скопировать план дня в тренировку, чтобы его можно было менять.
    Повторный вызов ничего не меняет."""
    workout = await editable_workout(scheduled_workout_id, session, current_user)
    return await finish(session, workout)


@router.post(
    "/exercises",
    response_model=ScheduledWorkoutDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_exercise(
    scheduled_workout_id: int,
    data: WorkoutExerciseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Добавить упражнение в конец тренировки."""
    workout = await editable_workout(scheduled_workout_id, session, current_user)
    await get_visible_exercise(data.exercise_id, session, current_user)

    last = await session.scalar(
        select(func.max(WorkoutExercise.order_index)).where(
            WorkoutExercise.scheduled_workout_id == workout.id
        )
    )

    session.add(
        WorkoutExercise(
            scheduled_workout_id=workout.id,
            exercise_id=data.exercise_id,
            order_index=(last + 1) if last is not None else 0,
            sets=data.sets,
            target_reps=data.target_reps,
            target_reps_max=data.target_reps_max,
            target_weight=data.target_weight,
            rest_seconds=data.rest_seconds,
        )
    )

    return await finish(session, workout)


@router.patch(
    "/exercises/{item_id}",
    response_model=ScheduledWorkoutDetailResponse,
)
async def change_exercise(
    scheduled_workout_id: int,
    item_id: int,
    data: WorkoutExercisePatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Поменять число подходов или цель, заменить упражнение. Заменить
    можно, пока по упражнению не записано ни одного подхода."""
    workout = await editable_workout(scheduled_workout_id, session, current_user)
    item = await get_item(session, workout, item_id)

    if data.exercise_id is not None and data.exercise_id != item.exercise_id:
        if await item_has_sets(session, item):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Exercise already has sets in this workout",
            )

        await get_visible_exercise(data.exercise_id, session, current_user)

    apply_changes(item, data, partial=True)

    if (
        item.target_reps is not None
        and item.target_reps_max is not None
        and item.target_reps_max < item.target_reps
    ):
        item.target_reps_max = None

    await session.flush()
    session.expire(item, ["exercise"])

    return await finish(session, workout)


@router.post(
    "/exercises/{item_id}/move",
    response_model=ScheduledWorkoutDetailResponse,
)
async def move_exercise(
    scheduled_workout_id: int,
    item_id: int,
    data: WorkoutExerciseMove,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Поднять или опустить упражнение на одну позицию."""
    workout = await editable_workout(scheduled_workout_id, session, current_user)
    await get_item(session, workout, item_id)

    items = await workout_items(session, workout.id)
    index = next(i for i, item in enumerate(items) if item.id == item_id)
    other = index - 1 if data.direction == "up" else index + 1

    if 0 <= other < len(items):
        items[index], items[other] = items[other], items[index]

        for position, item in enumerate(items):
            item.order_index = position

    return await finish(session, workout)


@router.delete(
    "/exercises/{item_id}",
    response_model=ScheduledWorkoutDetailResponse,
)
async def remove_exercise(
    scheduled_workout_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Убрать упражнение из тренировки вместе с его подходами."""
    workout = await editable_workout(scheduled_workout_id, session, current_user)
    item = await get_item(session, workout, item_id)

    await session.delete(item)
    await session.flush()
    await renumber(session, workout.id)

    return await finish(session, workout)
