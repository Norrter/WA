"""Общие проверки доступа и вспомогательные функции для роутов."""

from fastapi import HTTPException, Query
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.coaching import CoachClient, CoachingStatus
from app.models.exercise import Exercise
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.user import User
from app.models.workout_set import WorkoutSet


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


async def coaching_is_active(
    session: AsyncSession,
    coach_id: int,
    client_id: int,
) -> bool:
    link_id = await session.scalar(
        select(CoachClient.id).where(
            CoachClient.coach_id == coach_id,
            CoachClient.client_id == client_id,
            CoachClient.status == CoachingStatus.active.value,
        )
    )

    return link_id is not None


async def program_access(
    program: Program,
    session: AsyncSession,
    user: User,
) -> tuple[bool, bool]:
    """Права на программу: (можно смотреть, можно менять).

    - Своя программа — смотреть можно всегда. Менять — если её не ведёт
      тренер: программа, назначенная тренером, пока сотрудничество
      активно, у клиента только для чтения.
    - Тренер видит программы своих активных клиентов, а менять может
      те, что сам назначил.
    """
    if program.user_id is None:
        return False, False

    if program.user_id == user.id:
        managed = (
            program.assigned_by_coach_id is not None
            and await coaching_is_active(
                session, program.assigned_by_coach_id, user.id
            )
        )

        return True, not managed

    if await coaching_is_active(session, user.id, program.user_id):
        return True, program.assigned_by_coach_id == user.id

    return False, False


async def check_program_access(
    program: Program | None,
    session: AsyncSession,
    user: User,
    *,
    edit: bool,
) -> Program:
    can_read, can_edit = (
        await program_access(program, session, user)
        if program is not None
        else (False, False)
    )

    if not can_read:
        raise HTTPException(
            status_code=404,
            detail="Program not found",
        )

    if edit and not can_edit:
        raise HTTPException(
            status_code=403,
            detail=(
                "Program is managed by your coach"
                if program.user_id == user.id
                else "Program is read-only"
            ),
        )

    return program


async def get_owned_program(
    program_id: int,
    session: AsyncSession,
    current_user: User,
    *,
    edit: bool = True,
) -> Program:
    """Программа, которую можно менять (edit=True) или смотреть."""
    program = await session.get(Program, program_id)

    return await check_program_access(program, session, current_user, edit=edit)


async def get_schedulable_program(
    program_id: int,
    session: AsyncSession,
    current_user: User,
) -> Program:
    """Своя программа, по которой можно ставить тренировки. Программы
    от тренера тоже подходят: заниматься по ним клиент может."""
    program = await session.get(Program, program_id)

    if program is None or program.user_id != current_user.id:
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
    edit: bool = True,
) -> ProgramDay:
    await get_owned_program(program_id, session, current_user, edit=edit)

    query = select(ProgramDay).where(
        ProgramDay.id == day_id,
        ProgramDay.program_id == program_id,
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
        select(ScheduledWorkout).where(
            ScheduledWorkout.id == scheduled_workout_id,
            ScheduledWorkout.user_id == current_user.id,
        )
    )

    if workout is None:
        raise HTTPException(
            status_code=404,
            detail="Scheduled workout not found",
        )

    return workout


async def drop_unstarted_workouts(
    session: AsyncSession,
    *,
    program_id: int | None = None,
    day_id: int | None = None,
) -> None:
    """Перед удалением программы или дня: убрать запланированные
    тренировки без единого подхода, а у остальных (история) запомнить
    текущие названия программы и дня."""
    condition = (
        ScheduledWorkout.program_id == program_id
        if program_id is not None
        else ScheduledWorkout.program_day_id == day_id
    )

    has_sets = (
        select(WorkoutSet.id)
        .where(WorkoutSet.scheduled_workout_id == ScheduledWorkout.id)
        .exists()
    )

    await session.execute(
        delete(ScheduledWorkout)
        .where(
            condition,
            ScheduledWorkout.status == WorkoutStatus.planned.value,
            ~has_sets,
        )
        .execution_options(synchronize_session=False)
    )

    await session.execute(
        update(ScheduledWorkout)
        .where(condition)
        .values(
            program_name=select(Program.name)
            .where(Program.id == ScheduledWorkout.program_id)
            .scalar_subquery(),
            day_name=select(ProgramDay.name)
            .where(ProgramDay.id == ScheduledWorkout.program_day_id)
            .scalar_subquery(),
        )
        .execution_options(synchronize_session=False)
    )
