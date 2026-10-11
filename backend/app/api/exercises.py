from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import (
    Pagination,
    apply_changes,
    get_visible_exercise,
    visible_exercises_filter,
)
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.exercise import Exercise
from app.models.program_exercise import ProgramExercise
from app.models.user import User
from app.schemas.exercise import (
    ExerciseCreate,
    ExercisePatch,
    ExerciseResponse,
    ExerciseUpdate,
)


router = APIRouter(
    prefix="/exercises",
    tags=["Exercises"],
)


def escape_like(value: str) -> str:
    """Экранировать спецсимволы LIKE, чтобы % и _ искались как текст."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


async def get_own_exercise(
    exercise_id: int,
    session: AsyncSession,
    current_user: User,
) -> Exercise:
    """Упражнение, которое текущий пользователь вправе менять."""
    exercise = await get_visible_exercise(
        exercise_id,
        session,
        current_user,
    )

    if exercise.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Shared exercises are read-only",
        )

    return exercise


@router.post(
    "",
    response_model=ExerciseResponse,
)
async def create_exercise(
    data: ExerciseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    exercise = Exercise(
        created_by_user_id=current_user.id,
        name=data.name,
        description=data.description,
        muscle_group=data.muscle_group,
        equipment=data.equipment,
    )

    session.add(exercise)

    await session.commit()
    await session.refresh(exercise)

    return exercise


@router.get(
    "",
    response_model=list[ExerciseResponse],
)
async def get_exercises(
    search: str | None = Query(None, max_length=150),
    muscle_group: str | None = Query(None, max_length=100),
    equipment: str | None = Query(None, max_length=100),
    pagination: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Общие упражнения и свои. Фильтры: поиск по названию,
    группа мышц, оборудование."""
    query = select(Exercise).where(
        visible_exercises_filter(current_user)
    )

    if search:
        query = query.where(
            Exercise.name.ilike(
                f"%{escape_like(search.strip())}%",
                escape="\\",
            )
        )

    if muscle_group:
        query = query.where(
            func.lower(Exercise.muscle_group) == muscle_group.lower()
        )

    if equipment:
        query = query.where(
            func.lower(Exercise.equipment) == equipment.lower()
        )

    result = await session.execute(
        query.order_by(Exercise.id)
        .limit(pagination.limit)
        .offset(pagination.offset)
    )

    return result.scalars().all()


@router.get(
    "/{exercise_id}",
    response_model=ExerciseResponse,
)
async def get_exercise(
    exercise_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_visible_exercise(
        exercise_id,
        session,
        current_user,
    )


@router.put(
    "/{exercise_id}",
    response_model=ExerciseResponse,
)
async def update_exercise(
    exercise_id: int,
    data: ExerciseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    exercise = await get_own_exercise(
        exercise_id,
        session,
        current_user,
    )

    apply_changes(exercise, data, partial=False)

    await session.commit()
    await session.refresh(exercise)

    return exercise


@router.patch(
    "/{exercise_id}",
    response_model=ExerciseResponse,
)
async def patch_exercise(
    exercise_id: int,
    data: ExercisePatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    exercise = await get_own_exercise(
        exercise_id,
        session,
        current_user,
    )

    apply_changes(exercise, data, partial=True)

    await session.commit()
    await session.refresh(exercise)

    return exercise


@router.delete(
    "/{exercise_id}",
    status_code=204,
)
async def delete_exercise(
    exercise_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    exercise = await get_own_exercise(
        exercise_id,
        session,
        current_user,
    )

    used_in_programs = await session.scalar(
        select(func.count())
        .select_from(ProgramExercise)
        .where(ProgramExercise.exercise_id == exercise_id)
    )

    if used_in_programs:
        raise HTTPException(
            status_code=409,
            detail="Exercise is used in programs and cannot be deleted",
        )

    await session.delete(exercise)
    await session.commit()
