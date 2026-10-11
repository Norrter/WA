from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import Pagination, apply_changes, get_owned_program
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.user import User
from app.schemas.program import (
    ProgramCreate,
    ProgramDetailResponse,
    ProgramPatch,
    ProgramResponse,
    ProgramUpdate,
)


router = APIRouter(
    prefix="/programs",
    tags=["Programs"],
)


@router.post("", response_model=ProgramResponse)
async def create_program(
    data: ProgramCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    program = Program(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
    )

    session.add(program)

    await session.commit()
    await session.refresh(program)

    return program


@router.get("", response_model=list[ProgramResponse])
async def get_programs(
    pagination: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Program)
        .where(Program.user_id == current_user.id)
        .order_by(Program.id)
        .limit(pagination.limit)
        .offset(pagination.offset)
    )

    return result.scalars().all()


@router.get(
    "/{program_id}",
    response_model=ProgramDetailResponse,
)
async def get_program(
    program_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Program)
        .options(
            selectinload(Program.days)
            .selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )
        .where(
            Program.id == program_id,
            Program.user_id == current_user.id,
        )
    )

    program = result.scalar_one_or_none()

    if program is None:
        raise HTTPException(
            status_code=404,
            detail="Program not found",
        )

    return program


@router.put(
    "/{program_id}",
    response_model=ProgramResponse,
)
async def update_program(
    program_id: int,
    data: ProgramUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    program = await get_owned_program(
        program_id,
        session,
        current_user,
    )

    apply_changes(program, data, partial=False)

    await session.commit()
    await session.refresh(program)

    return program


@router.patch(
    "/{program_id}",
    response_model=ProgramResponse,
)
async def patch_program(
    program_id: int,
    data: ProgramPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    program = await get_owned_program(
        program_id,
        session,
        current_user,
    )

    apply_changes(program, data, partial=True)

    await session.commit()
    await session.refresh(program)

    return program


@router.delete(
    "/{program_id}",
    status_code=204,
)
async def delete_program(
    program_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    program = await get_owned_program(
        program_id,
        session,
        current_user,
    )

    await session.delete(program)
    await session.commit()
