from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import (
    apply_changes,
    get_owned_program_day,
    get_visible_exercise,
)
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.program_exercise import ProgramExercise
from app.models.user import User
from app.schemas.common import ReorderRequest
from app.schemas.program_exercise import (
    ProgramExerciseCreate,
    ProgramExercisePatch,
    ProgramExerciseResponse,
    ProgramExerciseUpdate,
)


router = APIRouter(
    prefix="/programs/{program_id}/days/{day_id}/exercises",
    tags=["Program Exercises"],
)


def check_reps_range(program_exercise: ProgramExercise) -> None:
    """Диапазон повторов: верхняя граница есть только вместе с нижней
    и не меньше её."""
    low = program_exercise.target_reps
    high = program_exercise.target_reps_max

    if high is not None and (low is None or high < low):
        raise HTTPException(
            status_code=422,
            detail="target_reps_max must be greater than or equal to target_reps",
        )


async def load_program_exercises(
    day_id: int,
    session: AsyncSession,
) -> list[ProgramExercise]:
    result = await session.execute(
        select(ProgramExercise)
        .options(
            selectinload(ProgramExercise.exercise)
        )
        .where(
            ProgramExercise.program_day_id == day_id
        )
        .order_by(
            ProgramExercise.order_index,
            ProgramExercise.id,
        )
        .execution_options(populate_existing=True)
    )

    return list(result.scalars().all())


async def load_program_exercise(
    program_exercise_id: int,
    day_id: int,
    session: AsyncSession,
) -> ProgramExercise:
    result = await session.execute(
        select(ProgramExercise)
        .options(
            selectinload(ProgramExercise.exercise)
        )
        .where(
            ProgramExercise.id == program_exercise_id,
            ProgramExercise.program_day_id == day_id,
        )
        .execution_options(populate_existing=True)
    )

    program_exercise = result.scalar_one_or_none()

    if program_exercise is None:
        raise HTTPException(
            status_code=404,
            detail="Program exercise not found",
        )

    return program_exercise


@router.post(
    "",
    response_model=ProgramExerciseResponse,
)
async def create_program_exercise(
    program_id: int,
    day_id: int,
    data: ProgramExerciseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    await get_visible_exercise(
        data.exercise_id,
        session,
        current_user,
    )

    program_exercise = ProgramExercise(
        program_day_id=day_id,
        exercise_id=data.exercise_id,
        order_index=data.order_index,
        sets=data.sets,
        target_reps=data.target_reps,
        target_reps_max=data.target_reps_max,
        target_weight=data.target_weight,
        rest_seconds=data.rest_seconds,
        notes=data.notes,
    )

    check_reps_range(program_exercise)

    session.add(program_exercise)

    await session.commit()

    return await load_program_exercise(
        program_exercise.id,
        day_id,
        session,
    )


@router.get(
    "",
    response_model=list[ProgramExerciseResponse],
)
async def get_program_exercises(
    program_id: int,
    day_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    return await load_program_exercises(day_id, session)


@router.post(
    "/reorder",
    response_model=list[ProgramExerciseResponse],
)
async def reorder_program_exercises(
    program_id: int,
    day_id: int,
    data: ReorderRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Задать новый порядок упражнений дня: ids всех упражнений
    сверху вниз. order_index проставляется как 1, 2, 3..."""
    await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    result = await session.execute(
        select(ProgramExercise).where(
            ProgramExercise.program_day_id == day_id
        )
    )

    items_by_id = {item.id: item for item in result.scalars().all()}

    if set(items_by_id) != set(data.ids):
        raise HTTPException(
            status_code=400,
            detail="ids must contain every exercise of this day exactly once",
        )

    for position, item_id in enumerate(data.ids, start=1):
        items_by_id[item_id].order_index = position

    await session.commit()

    return await load_program_exercises(day_id, session)


@router.get(
    "/{program_exercise_id}",
    response_model=ProgramExerciseResponse,
)
async def get_program_exercise(
    program_id: int,
    day_id: int,
    program_exercise_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    return await load_program_exercise(
        program_exercise_id,
        day_id,
        session,
    )


async def update_program_exercise_common(
    program_id: int,
    day_id: int,
    program_exercise_id: int,
    data: ProgramExerciseUpdate | ProgramExercisePatch,
    session: AsyncSession,
    current_user: User,
    *,
    partial: bool,
) -> ProgramExercise:
    await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    program_exercise = await load_program_exercise(
        program_exercise_id,
        day_id,
        session,
    )

    if data.exercise_id is not None:
        await get_visible_exercise(
            data.exercise_id,
            session,
            current_user,
        )

    apply_changes(program_exercise, data, partial=partial)
    check_reps_range(program_exercise)

    await session.commit()

    return await load_program_exercise(
        program_exercise_id,
        day_id,
        session,
    )


@router.put(
    "/{program_exercise_id}",
    response_model=ProgramExerciseResponse,
)
async def update_program_exercise(
    program_id: int,
    day_id: int,
    program_exercise_id: int,
    data: ProgramExerciseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_program_exercise_common(
        program_id,
        day_id,
        program_exercise_id,
        data,
        session,
        current_user,
        partial=False,
    )


@router.patch(
    "/{program_exercise_id}",
    response_model=ProgramExerciseResponse,
)
async def patch_program_exercise(
    program_id: int,
    day_id: int,
    program_exercise_id: int,
    data: ProgramExercisePatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await update_program_exercise_common(
        program_id,
        day_id,
        program_exercise_id,
        data,
        session,
        current_user,
        partial=True,
    )


@router.delete(
    "/{program_exercise_id}",
    status_code=204,
)
async def delete_program_exercise(
    program_id: int,
    day_id: int,
    program_exercise_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    program_exercise = await load_program_exercise(
        program_exercise_id,
        day_id,
        session,
    )

    await session.delete(program_exercise)
    await session.commit()
