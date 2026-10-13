from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import (
    apply_changes,
    drop_unstarted_workouts,
    get_owned_program,
    get_owned_program_day,
)
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.user import User
from app.schemas.common import ReorderRequest
from app.schemas.program_day import (
    ProgramDayCreate,
    ProgramDayPatch,
    ProgramDayResponse,
    ProgramDayUpdate,
)


router = APIRouter(
    prefix="/programs/{program_id}/days",
    tags=["Program Days"],
)


async def load_days(
    program_id: int,
    session: AsyncSession,
) -> list[ProgramDay]:
    result = await session.execute(
        select(ProgramDay)
        .options(
            selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )
        .where(
            ProgramDay.program_id == program_id
        )
        .order_by(ProgramDay.order_index, ProgramDay.id)
        .execution_options(populate_existing=True)
    )

    return list(result.scalars().all())


async def load_day(
    day_id: int,
    session: AsyncSession,
) -> ProgramDay:
    result = await session.execute(
        select(ProgramDay)
        .options(
            selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )
        .where(ProgramDay.id == day_id)
        .execution_options(populate_existing=True)
    )

    return result.scalar_one()


@router.post(
    "",
    response_model=ProgramDayResponse,
)
async def create_program_day(
    program_id: int,
    data: ProgramDayCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program(
        program_id,
        session,
        current_user,
    )

    day = ProgramDay(
        program_id=program_id,
        name=data.name,
        order_index=data.order_index,
    )

    session.add(day)

    await session.commit()

    return await load_day(day.id, session)


@router.get(
    "",
    response_model=list[ProgramDayResponse],
)
async def get_program_days(
    program_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program(
        program_id,
        session,
        current_user,
        edit=False,
    )

    return await load_days(program_id, session)


@router.post(
    "/reorder",
    response_model=list[ProgramDayResponse],
)
async def reorder_program_days(
    program_id: int,
    data: ReorderRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Задать новый порядок дней: ids всех дней программы сверху вниз.
    order_index проставляется как 1, 2, 3..."""
    await get_owned_program(
        program_id,
        session,
        current_user,
    )

    result = await session.execute(
        select(ProgramDay).where(
            ProgramDay.program_id == program_id
        )
    )

    days_by_id = {day.id: day for day in result.scalars().all()}

    if set(days_by_id) != set(data.ids):
        raise HTTPException(
            status_code=400,
            detail="ids must contain every day of this program exactly once",
        )

    for position, day_id in enumerate(data.ids, start=1):
        days_by_id[day_id].order_index = position

    await session.commit()

    return await load_days(program_id, session)


@router.get(
    "/{day_id}",
    response_model=ProgramDayResponse,
)
async def get_program_day(
    program_id: int,
    day_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
        with_exercises=True,
        edit=False,
    )


@router.put(
    "/{day_id}",
    response_model=ProgramDayResponse,
)
async def update_program_day(
    program_id: int,
    day_id: int,
    data: ProgramDayUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    day = await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    apply_changes(day, data, partial=False)

    await session.commit()

    return await load_day(day_id, session)


@router.patch(
    "/{day_id}",
    response_model=ProgramDayResponse,
)
async def patch_program_day(
    program_id: int,
    day_id: int,
    data: ProgramDayPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    day = await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    apply_changes(day, data, partial=True)

    await session.commit()

    return await load_day(day_id, session)


@router.delete(
    "/{day_id}",
    status_code=204,
)
async def delete_program_day(
    program_id: int,
    day_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    day = await get_owned_program_day(
        program_id,
        day_id,
        session,
        current_user,
    )

    # Выполненные тренировки этого дня остаются в истории
    await drop_unstarted_workouts(session, day_id=day.id)

    await session.delete(day)
    await session.commit()
