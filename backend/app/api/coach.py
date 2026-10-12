"""Кабинет тренера: статистика по всем пользователям.

Доступен только пользователям с ролью coach (см. COACH_EMAILS).
Тренер только смотрит — изменить чужие данные отсюда нельзя.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.progress import all_exercise_records, stats_summary, weekly_volume
from app.core.dependencies import get_current_coach
from app.database.session import get_session
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.user import User
from app.models.workout_set import WorkoutSet
from app.schemas.coach import (
    CoachExerciseRecords,
    CoachUserItem,
    CoachWorkoutItem,
)
from app.schemas.progress import StatsSummaryResponse, WeeklyVolumeItem
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/coach",
    tags=["Coach"],
    dependencies=[Depends(get_current_coach)],
)


def in_period(query, date_from: date | None, date_to: date | None):
    if date_from is not None:
        query = query.where(ScheduledWorkout.scheduled_date >= date_from)

    if date_to is not None:
        query = query.where(ScheduledWorkout.scheduled_date <= date_to)

    return query


async def get_user_or_404(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get("/users", response_model=list[CoachUserItem])
async def list_users(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Все пользователи со сводкой за период (даты включительно)."""
    users = (
        await session.scalars(select(User).order_by(User.username))
    ).all()

    programs = dict(
        (
            await session.execute(
                select(Program.user_id, func.count())
                .where(Program.user_id.is_not(None))
                .group_by(Program.user_id)
            )
        ).all()
    )

    workouts: dict[int, dict[str, int]] = {}
    workout_rows = await session.execute(
        in_period(
            select(Program.user_id, ScheduledWorkout.status, func.count())
            .join(Program, Program.id == ScheduledWorkout.program_id)
            .group_by(Program.user_id, ScheduledWorkout.status),
            date_from,
            date_to,
        )
    )

    for user_id, workout_status, count in workout_rows.all():
        workouts.setdefault(user_id, {})[workout_status] = count

    sets = {
        user_id: (count, volume)
        for user_id, count, volume in (
            await session.execute(
                in_period(
                    select(
                        Program.user_id,
                        func.count(WorkoutSet.id),
                        func.coalesce(
                            func.sum(WorkoutSet.weight * WorkoutSet.reps),
                            0,
                        ),
                    )
                    .join(
                        ScheduledWorkout,
                        ScheduledWorkout.id == WorkoutSet.scheduled_workout_id,
                    )
                    .join(Program, Program.id == ScheduledWorkout.program_id)
                    .where(WorkoutSet.completed.is_(True))
                    .group_by(Program.user_id),
                    date_from,
                    date_to,
                )
            )
        ).all()
    }

    last_workout = dict(
        (
            await session.execute(
                select(Program.user_id, func.max(ScheduledWorkout.scheduled_date))
                .join(Program, Program.id == ScheduledWorkout.program_id)
                .where(ScheduledWorkout.status == WorkoutStatus.completed.value)
                .group_by(Program.user_id)
            )
        ).all()
    )

    items = []

    for user in users:
        counts = workouts.get(user.id, {})
        sets_count, volume = sets.get(user.id, (0, 0))

        items.append(
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "created_at": user.created_at,
                "programs": programs.get(user.id, 0),
                "workouts_planned": counts.get(WorkoutStatus.planned.value, 0),
                "workouts_completed": counts.get(
                    WorkoutStatus.completed.value, 0
                ),
                "workouts_skipped": counts.get(WorkoutStatus.skipped.value, 0),
                "total_sets": sets_count,
                "total_volume": float(volume),
                "last_workout": last_workout.get(user.id),
            }
        )

    return items


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    return await get_user_or_404(session, user_id)


@router.get(
    "/users/{user_id}/summary",
    response_model=StatsSummaryResponse,
)
async def get_user_summary(
    user_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    await get_user_or_404(session, user_id)

    return await stats_summary(session, user_id, date_from, date_to)


@router.get(
    "/users/{user_id}/weekly-volume",
    response_model=list[WeeklyVolumeItem],
)
async def get_user_weekly_volume(
    user_id: int,
    weeks: int = Query(12, ge=1, le=104),
    session: AsyncSession = Depends(get_session),
):
    await get_user_or_404(session, user_id)

    return await weekly_volume(session, user_id, weeks)


@router.get(
    "/users/{user_id}/records",
    response_model=list[CoachExerciseRecords],
)
async def get_user_records(
    user_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Рекорды по всем упражнениям, которые выполнял пользователь."""
    await get_user_or_404(session, user_id)

    return await all_exercise_records(session, user_id)


@router.get(
    "/users/{user_id}/workouts",
    response_model=list[CoachWorkoutItem],
)
async def get_user_workouts(
    user_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """Тренировки пользователя от новых к старым, с итогами
    по выполненным подходам."""
    await get_user_or_404(session, user_id)

    completed_sets = (
        select(
            WorkoutSet.scheduled_workout_id.label("workout_id"),
            func.count().label("sets"),
            func.sum(WorkoutSet.weight * WorkoutSet.reps).label("volume"),
        )
        .where(WorkoutSet.completed.is_(True))
        .group_by(WorkoutSet.scheduled_workout_id)
        .subquery()
    )

    query = in_period(
        select(
            ScheduledWorkout,
            Program.name,
            ProgramDay.name,
            func.coalesce(completed_sets.c.sets, 0),
            func.coalesce(completed_sets.c.volume, 0),
        )
        .join(Program, Program.id == ScheduledWorkout.program_id)
        .join(ProgramDay, ProgramDay.id == ScheduledWorkout.program_day_id)
        .outerjoin(
            completed_sets,
            completed_sets.c.workout_id == ScheduledWorkout.id,
        )
        .where(Program.user_id == user_id),
        date_from,
        date_to,
    )

    result = await session.execute(
        query.order_by(
            ScheduledWorkout.scheduled_date.desc(),
            ScheduledWorkout.id.desc(),
        ).limit(limit)
    )

    return [
        {
            "id": workout.id,
            "scheduled_date": workout.scheduled_date,
            "status": workout.status,
            "program_name": program_name,
            "day_name": day_name,
            "sets_completed": sets,
            "volume": float(volume),
        }
        for workout, program_name, day_name, sets, volume in result.all()
    ]
