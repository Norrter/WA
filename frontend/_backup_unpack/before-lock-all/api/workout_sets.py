from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import apply_changes, get_owned_workout
from app.core.dependencies import get_current_user, require_open_diary
from app.core.load import compute_load, uses_body_weight
from app.database.session import get_session
from app.models.exercise import Exercise
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.models.workout_exercise import WorkoutExercise
from app.models.workout_set import WorkoutSet
from app.services.workout_plan import get_item
from app.schemas.workout_set import (
    WorkoutSetCreate,
    WorkoutSetPatch,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)


router = APIRouter(
    prefix="/scheduled-workouts/{scheduled_workout_id}/sets",
    tags=["Workout Sets"],
    # с неподтверждённой почтой — только просмотр
    dependencies=[Depends(require_open_diary)],
)


async def get_valid_program_exercise(
    workout: ScheduledWorkout,
    program_exercise_id: int,
    session: AsyncSession,
) -> ProgramExercise:
    result = await session.execute(
        select(ProgramExercise)
        .join(
            ProgramDay,
            ProgramExercise.program_day_id == ProgramDay.id,
        )
        .where(
            ProgramExercise.id == program_exercise_id,
            ProgramDay.id == workout.program_day_id,
        )
    )

    program_exercise = result.scalar_one_or_none()

    if not program_exercise:
        raise HTTPException(
            status_code=400,
            detail="Program exercise does not belong to this scheduled workout",
        )

    return program_exercise


async def get_workout_set_or_404(
    scheduled_workout_id: int,
    workout_set_id: int,
    session: AsyncSession,
) -> WorkoutSet:
    workout_set = await session.scalar(
        select(WorkoutSet).where(
            WorkoutSet.id == workout_set_id,
            WorkoutSet.scheduled_workout_id == scheduled_workout_id,
        )
    )

    if not workout_set:
        raise HTTPException(
            status_code=404,
            detail="Workout set not found",
        )

    return workout_set


@router.post(
    "",
    response_model=WorkoutSetResponse,
    status_code=201,
)
async def create_workout_set(
    scheduled_workout_id: int,
    data: WorkoutSetCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    if data.workout_exercise_id is not None:
        item = await get_item(session, workout, data.workout_exercise_id)
        exercise_id = item.exercise_id
        workout_exercise_id = item.id
        program_exercise_id = None

        # Строка программы остаётся у подхода, только если упражнение
        # не заменяли
        if item.program_exercise_id is not None:
            origin = await session.get(ProgramExercise, item.program_exercise_id)
            if origin is not None and origin.exercise_id == item.exercise_id:
                program_exercise_id = origin.id
    else:
        program_exercise = await get_valid_program_exercise(
            workout,
            data.program_exercise_id,
            session,
        )
        exercise_id = program_exercise.exercise_id
        program_exercise_id = program_exercise.id
        workout_exercise_id = None

        # План тренировки уже свой: найдём строку, пришедшую из программы
        if workout.custom_plan:
            workout_exercise_id = await session.scalar(
                select(WorkoutExercise.id).where(
                    WorkoutExercise.scheduled_workout_id == workout.id,
                    WorkoutExercise.program_exercise_id == program_exercise.id,
                    WorkoutExercise.exercise_id == program_exercise.exercise_id,
                )
            )

    exercise = await session.get(Exercise, exercise_id)
    load_type = exercise.load_type if exercise else "external"
    body_weight = current_user.body_weight if uses_body_weight(load_type) else None

    if load_type == "assisted" and body_weight is None:
        raise HTTPException(
            status_code=400,
            detail="Set your body weight in the profile first",
        )

    workout_set = WorkoutSet(
        scheduled_workout_id=scheduled_workout_id,
        program_exercise_id=program_exercise_id,
        workout_exercise_id=workout_exercise_id,
        exercise_id=exercise_id,
        set_number=data.set_number,
        body_weight=body_weight,
        load=compute_load(load_type, data.weight, body_weight),
        weight=data.weight,
        reps=data.reps,
        completed=data.completed,
    )

    session.add(workout_set)
    await session.commit()
    await session.refresh(workout_set)

    return workout_set


@router.get(
    "",
    response_model=list[WorkoutSetResponse],
)
async def get_workout_sets(
    scheduled_workout_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    result = await session.execute(
        select(WorkoutSet)
        .where(
            WorkoutSet.scheduled_workout_id == scheduled_workout_id
        )
        .order_by(
            WorkoutSet.exercise_id,
            WorkoutSet.set_number,
            WorkoutSet.id,
        )
    )

    return result.scalars().all()


@router.get(
    "/{workout_set_id}",
    response_model=WorkoutSetResponse,
)
async def get_workout_set(
    scheduled_workout_id: int,
    workout_set_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    return await get_workout_set_or_404(
        scheduled_workout_id,
        workout_set_id,
        session,
    )


async def update_workout_set_common(
    scheduled_workout_id: int,
    workout_set_id: int,
    data: WorkoutSetUpdate | WorkoutSetPatch,
    session: AsyncSession,
    current_user: User,
    *,
    partial: bool,
) -> WorkoutSet:
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    workout_set = await get_workout_set_or_404(
        scheduled_workout_id,
        workout_set_id,
        session,
    )

    if data.program_exercise_id is not None:
        program_exercise = await get_valid_program_exercise(
            workout,
            data.program_exercise_id,
            session,
        )
        workout_set.exercise_id = program_exercise.exercise_id

    apply_changes(workout_set, data, partial=partial)

    # Вес или упражнение поменялись — пересчитать нагрузку
    exercise = await session.get(Exercise, workout_set.exercise_id)
    load_type = exercise.load_type if exercise else "external"

    if uses_body_weight(load_type) and workout_set.body_weight is None:
        workout_set.body_weight = current_user.body_weight

    workout_set.load = compute_load(load_type, workout_set.weight, workout_set.body_weight)

    await session.commit()
    await session.refresh(workout_set)

    return workout_set


@router.put(
    "/{workout_set_id}",
    response_model=WorkoutSetResponse,
)
async def update_workout_set(
    scheduled_workout_id: int,
    workout_set_id: int,
    data: WorkoutSetUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_workout_set_common(
        scheduled_workout_id,
        workout_set_id,
        data,
        session,
        current_user,
        partial=False,
    )


@router.patch(
    "/{workout_set_id}",
    response_model=WorkoutSetResponse,
)
async def patch_workout_set(
    scheduled_workout_id: int,
    workout_set_id: int,
    data: WorkoutSetPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_workout_set_common(
        scheduled_workout_id,
        workout_set_id,
        data,
        session,
        current_user,
        partial=True,
    )


@router.delete(
    "/{workout_set_id}",
    status_code=204,
)
async def delete_workout_set(
    scheduled_workout_id: int,
    workout_set_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    workout_set = await get_workout_set_or_404(
        scheduled_workout_id,
        workout_set_id,
        session,
    )

    await session.delete(workout_set)
    await session.commit()
