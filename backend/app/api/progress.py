"""История подходов, личные рекорды и статистика."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import Pagination, get_visible_exercise
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.program import Program
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.user import User
from app.models.workout_set import WorkoutSet
from app.schemas.progress import (
    ExerciseHistoryItem,
    ExerciseRecordsResponse,
    StatsSummaryResponse,
    WeeklyVolumeItem,
)


router = APIRouter(tags=["Progress"])


def user_sets_query(current_user: User):
    """Подходы текущего пользователя вместе с датой тренировки."""
    return (
        select(WorkoutSet, ScheduledWorkout.scheduled_date)
        .join(
            ScheduledWorkout,
            ScheduledWorkout.id == WorkoutSet.scheduled_workout_id,
        )
        .join(
            Program,
            Program.id == ScheduledWorkout.program_id,
        )
        .where(Program.user_id == current_user.id)
    )


def estimate_1rm(weight: float, reps: int) -> float:
    """Расчётный одноповторный максимум по формуле Эпли."""
    if reps == 1:
        return weight

    return weight * (1 + reps / 30)


@router.get(
    "/exercises/{exercise_id}/history",
    response_model=list[ExerciseHistoryItem],
)
async def get_exercise_history(
    exercise_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    pagination: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Все свои подходы по упражнению, от новых к старым."""
    await get_visible_exercise(
        exercise_id,
        session,
        current_user,
    )

    query = (
        user_sets_query(current_user)
        .join(
            ProgramExercise,
            ProgramExercise.id == WorkoutSet.program_exercise_id,
        )
        .where(ProgramExercise.exercise_id == exercise_id)
    )

    if date_from is not None:
        query = query.where(ScheduledWorkout.scheduled_date >= date_from)

    if date_to is not None:
        query = query.where(ScheduledWorkout.scheduled_date <= date_to)

    result = await session.execute(
        query.order_by(
            ScheduledWorkout.scheduled_date.desc(),
            ScheduledWorkout.id.desc(),
            WorkoutSet.set_number,
        )
        .limit(pagination.limit)
        .offset(pagination.offset)
    )

    return [
        {
            "workout_set_id": workout_set.id,
            "scheduled_workout_id": workout_set.scheduled_workout_id,
            "date": scheduled_date,
            "set_number": workout_set.set_number,
            "weight": workout_set.weight,
            "reps": workout_set.reps,
            "completed": workout_set.completed,
        }
        for workout_set, scheduled_date in result.all()
    ]


@router.get(
    "/exercises/{exercise_id}/records",
    response_model=ExerciseRecordsResponse,
)
async def get_exercise_records(
    exercise_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Личные рекорды по упражнению. Считаются только выполненные
    подходы."""
    await get_visible_exercise(
        exercise_id,
        session,
        current_user,
    )

    result = await session.execute(
        user_sets_query(current_user)
        .join(
            ProgramExercise,
            ProgramExercise.id == WorkoutSet.program_exercise_id,
        )
        .where(
            ProgramExercise.exercise_id == exercise_id,
            WorkoutSet.completed.is_(True),
        )
        .order_by(ScheduledWorkout.scheduled_date, WorkoutSet.id)
    )

    rows = result.all()

    max_weight = None
    best_1rm_set = None
    best_1rm = None

    for workout_set, scheduled_date in rows:
        record = {
            "weight": workout_set.weight,
            "reps": workout_set.reps,
            "date": scheduled_date,
        }

        # При равном весе рекордом считается подход с большим числом повторов
        if max_weight is None or (
            workout_set.weight,
            workout_set.reps,
        ) > (
            max_weight["weight"],
            max_weight["reps"],
        ):
            max_weight = record

        estimated = estimate_1rm(workout_set.weight, workout_set.reps)

        if best_1rm is None or estimated > best_1rm:
            best_1rm = estimated
            best_1rm_set = record

    return {
        "exercise_id": exercise_id,
        "total_sets": len(rows),
        "total_reps": sum(workout_set.reps for workout_set, _ in rows),
        "total_volume": sum(
            workout_set.weight * workout_set.reps
            for workout_set, _ in rows
        ),
        "last_performed": rows[-1][1] if rows else None,
        "max_weight": max_weight,
        "best_estimated_1rm_set": best_1rm_set,
        "best_estimated_1rm": (
            round(best_1rm, 2) if best_1rm is not None else None
        ),
    }


@router.get(
    "/stats/summary",
    response_model=StatsSummaryResponse,
)
async def get_stats_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Сводка за период (даты включительно): сколько тренировок
    в каждом статусе и суммарный объём по выполненным подходам."""
    workouts_query = (
        select(ScheduledWorkout.status, func.count())
        .join(
            Program,
            Program.id == ScheduledWorkout.program_id,
        )
        .where(Program.user_id == current_user.id)
        .group_by(ScheduledWorkout.status)
    )

    sets_query = user_sets_query(current_user).where(
        WorkoutSet.completed.is_(True)
    )

    if date_from is not None:
        workouts_query = workouts_query.where(
            ScheduledWorkout.scheduled_date >= date_from
        )
        sets_query = sets_query.where(
            ScheduledWorkout.scheduled_date >= date_from
        )

    if date_to is not None:
        workouts_query = workouts_query.where(
            ScheduledWorkout.scheduled_date <= date_to
        )
        sets_query = sets_query.where(
            ScheduledWorkout.scheduled_date <= date_to
        )

    counts = dict((await session.execute(workouts_query)).all())
    sets = [row[0] for row in (await session.execute(sets_query)).all()]

    return {
        "date_from": date_from,
        "date_to": date_to,
        "workouts_planned": counts.get(WorkoutStatus.planned.value, 0),
        "workouts_completed": counts.get(WorkoutStatus.completed.value, 0),
        "workouts_skipped": counts.get(WorkoutStatus.skipped.value, 0),
        "total_sets": len(sets),
        "total_reps": sum(workout_set.reps for workout_set in sets),
        "total_volume": sum(
            workout_set.weight * workout_set.reps
            for workout_set in sets
        ),
    }


@router.get(
    "/stats/weekly-volume",
    response_model=list[WeeklyVolumeItem],
)
async def get_weekly_volume(
    weeks: int = Query(12, ge=1, le=104),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Объём по неделям за последние weeks недель, включая текущую.
    Недели без тренировок возвращаются с нулями."""
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    first_week_start = current_week_start - timedelta(weeks=weeks - 1)
    period_end = current_week_start + timedelta(days=6)

    result = await session.execute(
        user_sets_query(current_user).where(
            WorkoutSet.completed.is_(True),
            ScheduledWorkout.scheduled_date >= first_week_start,
            ScheduledWorkout.scheduled_date <= period_end,
        )
    )

    by_week = {
        first_week_start + timedelta(weeks=index): {
            "workout_ids": set(),
            "sets": 0,
            "reps": 0,
            "volume": 0.0,
        }
        for index in range(weeks)
    }

    for workout_set, scheduled_date in result.all():
        week_start = scheduled_date - timedelta(
            days=scheduled_date.weekday()
        )

        week = by_week[week_start]
        week["workout_ids"].add(workout_set.scheduled_workout_id)
        week["sets"] += 1
        week["reps"] += workout_set.reps
        week["volume"] += workout_set.weight * workout_set.reps

    return [
        {
            "week_start": week_start,
            "workouts": len(week["workout_ids"]),
            "sets": week["sets"],
            "reps": week["reps"],
            "volume": week["volume"],
        }
        for week_start, week in by_week.items()
    ]
