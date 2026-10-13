from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import apply_changes, get_owned_workout
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.models.workout_set import WorkoutSet
from app.schemas.workout_set import (
    WorkoutSetCreate,
    WorkoutSetPatch,
    WorkoutSetResponse,
    WorkoutSetUpdate,
)


router = APIRouter(
    prefix="/scheduled-workouts/{scheduled_workout_id}/sets",
    tags=["Workout Sets"],
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

    program_exercise = await get_valid_program_exercise(
        workout,
        data.program_exercise_id,
        session,
    )

    workout_set = WorkoutSet(
        scheduled_workout_id=scheduled_workout_id,
        program_exercise_id=data.program_exercise_id,
        exercise_id=program_exercise.exercise_id,
        set_number=data.set_number,
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
