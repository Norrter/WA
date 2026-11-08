from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import (
    Pagination,
    apply_changes,
    drop_unstarted_workouts,
    get_owned_program,
    program_access,
)
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
from app.services.programs import (
    copy_program_tree,
    describe_programs,
    load_program_tree,
)


router = APIRouter(
    prefix="/programs",
    tags=["Programs"],
)


async def described(session: AsyncSession, program: Program, user: User) -> Program:
    [program] = await describe_programs(session, [program], user)
    return program


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

    return await described(session, program, current_user)


@router.get("", response_model=list[ProgramResponse])
async def get_programs(
    pagination: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Свои программы, включая назначенные тренером."""
    result = await session.execute(
        select(Program)
        .where(Program.user_id == current_user.id)
        .order_by(Program.id)
        .limit(pagination.limit)
        .offset(pagination.offset)
    )

    return await describe_programs(session, list(result.scalars().all()), current_user)


@router.get(
    "/templates",
    response_model=list[ProgramDetailResponse],
)
async def get_program_templates(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Готовые программы, общие для всех. Их нельзя менять,
    но можно взять себе копию: POST /programs/{id}/copy."""
    result = await session.execute(
        select(Program)
        .options(
            selectinload(Program.days)
            .selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )
        .where(Program.user_id.is_(None))
        .order_by(Program.id)
    )

    return await describe_programs(session, list(result.scalars().all()), current_user)


@router.post(
    "/{program_id}/copy",
    response_model=ProgramResponse,
    status_code=201,
)
async def copy_program(
    program_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать на основе: своя копия шаблона, своей программы или
    программы от тренера — со всеми днями и упражнениями. Копию
    можно менять как угодно, с оригиналом она не связана."""
    source = await load_program_tree(session, program_id)

    readable = source is not None and (
        source.user_id is None
        or (await program_access(source, session, current_user))[0]
    )

    if not readable:
        raise HTTPException(
            status_code=404,
            detail="Program not found",
        )

    copy = copy_program_tree(source, current_user.id)
    session.add(copy)

    await session.commit()
    await session.refresh(copy)

    return await described(session, copy, current_user)


@router.get(
    "/{program_id}",
    response_model=ProgramDetailResponse,
)
async def get_program(
    program_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Программа целиком. Тренер видит программы своих клиентов."""
    await get_owned_program(program_id, session, current_user, edit=False)
    program = await load_program_tree(session, program_id)

    return await described(session, program, current_user)


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

    return await described(session, program, current_user)


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

    return await described(session, program, current_user)


@router.delete(
    "/{program_id}",
    status_code=204,
)
async def delete_program(
    program_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить программу. Будущие тренировки по ней удаляются,
    выполненные и пропущенные остаются в истории."""
    program = await get_owned_program(
        program_id,
        session,
        current_user,
    )

    await drop_unstarted_workouts(session, program_id=program.id)

    await session.delete(program)
    await session.commit()
