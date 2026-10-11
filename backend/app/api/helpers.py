"""Общие проверки доступа и вспомогательные функции для роутов."""

from fastapi import HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import Exercise
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User


class Pagination:
    """Параметры ?limit=&offset= для списков."""

    def __init__(
        self,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        self.limit = limit
        self.offset = offset


def apply_changes(obj, data, *, partial: bool) -> None:
    """Перенести поля из схемы в модель.

    partial=True (PATCH): только те поля, что прислал клиент.
    partial=False (PUT): все поля схемы.
    """
    values = data.model_dump(exclude_unset=partial)

    for field_name, value in values.items():
        setattr(obj, field_name, value)


def visible_exercises_filter(current_user: User):
    """Пользователь видит общие упражнения и свои собственные."""
    return or_(
        Exercise.created_by_user_id.is_(None),
        Exercise.created_by_user_id == current_user.id,
    )


async def get_visible_exercise(
    exercise_id: int,
    session: AsyncSession,
    current_user: User,
) -> Exercise:
    exercise = await session.scalar(
        select(Exercise).where(
            Exercise.id == exercise_id,
            visible_exercises_filter(current_user),
        )
    )

    if exercise is None:
        raise HTTPException(
            status_code=404,
            detail="Exercise not found",
        )

    return exercise


async def get_owned_program(
    program_id: int,
    session: AsyncSession,
    current_user: User,
) -> Program:
    program = await session.scalar(
        select(Program).where(
            Program.id == program_id,
            Program.user_id == current_user.id,
        )
    )

    if program is None:
        raise HTTPException(
            status_code=404,
            detail="Program not found",
        )

    return program


async def get_owned_program_day(
    program_id: int,
    day_id: int,
    session: AsyncSession,
    current_user: User,
    *,
    with_exercises: bool = False,
) -> ProgramDay:
    query = (
        select(ProgramDay)
        .join(Program, Program.id == ProgramDay.program_id)
        .where(
            ProgramDay.id == day_id,
            ProgramDay.program_id == program_id,
            Program.user_id == current_user.id,
        )
    )

    if with_exercises:
        query = query.options(
            selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )

    day = await session.scalar(query)

    if day is None:
        raise HTTPException(
            status_code=404,
            detail="Program day not found",
        )

    return day


async def get_owned_workout(
    scheduled_workout_id: int,
    session: AsyncSession,
    current_user: User,
) -> ScheduledWorkout:
    workout = await session.scalar(
        select(ScheduledWorkout)
        .join(
            Program,
            Program.id == ScheduledWorkout.program_id,
        )
        .where(
            ScheduledWorkout.id == scheduled_workout_id,
            Program.user_id == current_user.id,
        )
    )

    if workout is None:
        raise HTTPException(
            status_code=404,
            detail="Scheduled workout not found",
        )

    return workout
