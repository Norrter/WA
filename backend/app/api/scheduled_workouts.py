from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import (
    Pagination,
    apply_changes,
    get_owned_program,
    get_owned_workout,
)
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.user import User
from app.models.workout_set import WorkoutSet
from app.schemas.scheduled_workout import (
    GenerateScheduleRequest,
    ScheduledWorkoutCreate,
    ScheduledWorkoutDetailResponse,
    ScheduledWorkoutPatch,
    ScheduledWorkoutResponse,
    ScheduledWorkoutUpdate,
)


router = APIRouter(
    prefix="/scheduled-workouts",
    tags=["Scheduled Workouts"],
)


async def get_program_day(
    program_id: int,
    program_day_id: int,
    session: AsyncSession,
):
    result = await session.execute(
        select(ProgramDay).where(
            ProgramDay.id == program_day_id,
            ProgramDay.program_id == program_id,
        )
    )

    program_day = result.scalar_one_or_none()

    if program_day is None:
        raise HTTPException(
            status_code=404,
            detail="Program day not found in this program",
        )

    return program_day


@router.post(
    "",
    response_model=ScheduledWorkoutResponse,
    status_code=201,
)
async def create_scheduled_workout(
    data: ScheduledWorkoutCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await get_owned_program(
        data.program_id,
        session,
        current_user,
    )

    await get_program_day(
        data.program_id,
        data.program_day_id,
        session,
    )

    workout = ScheduledWorkout(
        program_id=data.program_id,
        program_day_id=data.program_day_id,
        scheduled_date=data.scheduled_date,
        status=data.status.value,
    )

    session.add(workout)

    await session.commit()
    await session.refresh(workout)

    return workout


@router.post(
    "/generate",
    response_model=list[ScheduledWorkoutResponse],
    status_code=201,
)
async def generate_schedule(
    data: GenerateScheduleRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Разложить программу по календарю.

    Дни программы идут по кругу в своём порядке и ставятся на выбранные
    дни недели, начиная со start_date, на weeks недель. Даты, на которые
    у этой программы уже есть тренировка, пропускаются.
    """
    await get_owned_program(
        data.program_id,
        session,
        current_user,
    )

    result = await session.execute(
        select(ProgramDay)
        .where(ProgramDay.program_id == data.program_id)
        .order_by(ProgramDay.order_index, ProgramDay.id)
    )

    days = result.scalars().all()

    if not days:
        raise HTTPException(
            status_code=400,
            detail="Program has no days to schedule",
        )

    end_date = data.start_date + timedelta(weeks=data.weeks)

    result = await session.execute(
        select(ScheduledWorkout.scheduled_date).where(
            ScheduledWorkout.program_id == data.program_id,
            ScheduledWorkout.scheduled_date >= data.start_date,
            ScheduledWorkout.scheduled_date < end_date,
        )
    )

    busy_dates = set(result.scalars().all())

    workouts = []
    current_date = data.start_date

    while current_date < end_date:
        if (
            current_date.weekday() in data.weekdays
            and current_date not in busy_dates
        ):
            day = days[len(workouts) % len(days)]

            workouts.append(
                ScheduledWorkout(
                    program_id=data.program_id,
                    program_day_id=day.id,
                    scheduled_date=current_date,
                    status=WorkoutStatus.planned.value,
                )
            )

        current_date += timedelta(days=1)

    session.add_all(workouts)

    await session.commit()

    return workouts


@router.get(
    "",
    response_model=list[ScheduledWorkoutResponse],
)
async def get_scheduled_workouts(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: WorkoutStatus | None = Query(None),
    program_id: int | None = Query(None),
    pagination: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Свои тренировки. Фильтры: диапазон дат (включительно),
    статус, программа."""
    query = (
        select(ScheduledWorkout)
        .join(
            Program,
            Program.id == ScheduledWorkout.program_id,
        )
        .where(
            Program.user_id == current_user.id,
        )
    )

    if date_from is not None:
        query = query.where(ScheduledWorkout.scheduled_date >= date_from)

    if date_to is not None:
        query = query.where(ScheduledWorkout.scheduled_date <= date_to)

    if status is not None:
        query = query.where(ScheduledWorkout.status == status.value)

    if program_id is not None:
        query = query.where(ScheduledWorkout.program_id == program_id)

    result = await session.execute(
        query.order_by(
            ScheduledWorkout.scheduled_date,
            ScheduledWorkout.id,
        )
        .limit(pagination.limit)
        .offset(pagination.offset)
    )

    return result.scalars().all()


@router.get(
    "/{scheduled_workout_id}",
    response_model=ScheduledWorkoutResponse,
)
async def get_scheduled_workout(
    scheduled_workout_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )


@router.get(
    "/{scheduled_workout_id}/full",
    response_model=ScheduledWorkoutDetailResponse,
)
async def get_scheduled_workout_full(
    scheduled_workout_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Тренировка целиком: программа, день, упражнения с планом
    и уже записанные подходы по каждому упражнению."""
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    program = await session.get(Program, workout.program_id)

    day = await session.scalar(
        select(ProgramDay)
        .options(
            selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )
        .where(ProgramDay.id == workout.program_day_id)
    )

    result = await session.execute(
        select(WorkoutSet)
        .where(WorkoutSet.scheduled_workout_id == workout.id)
        .order_by(WorkoutSet.set_number, WorkoutSet.id)
    )

    sets_by_exercise: dict[int, list[WorkoutSet]] = {}

    for workout_set in result.scalars().all():
        sets_by_exercise.setdefault(
            workout_set.program_exercise_id,
            [],
        ).append(workout_set)

    return {
        "id": workout.id,
        "program_id": program.id,
        "program_name": program.name,
        "program_day_id": day.id,
        "program_day_name": day.name,
        "scheduled_date": workout.scheduled_date,
        "status": workout.status,
        "exercises": [
            {
                "program_exercise_id": program_exercise.id,
                "exercise": program_exercise.exercise,
                "order_index": program_exercise.order_index,
                "sets": program_exercise.sets,
                "target_reps": program_exercise.target_reps,
                "target_reps_max": program_exercise.target_reps_max,
                "target_weight": program_exercise.target_weight,
                "rest_seconds": program_exercise.rest_seconds,
                "notes": program_exercise.notes,
                "performed_sets": sets_by_exercise.get(
                    program_exercise.id,
                    [],
                ),
            }
            for program_exercise in day.exercises
        ],
    }


@router.put(
    "/{scheduled_workout_id}",
    response_model=ScheduledWorkoutResponse,
)
async def update_scheduled_workout(
    scheduled_workout_id: int,
    data: ScheduledWorkoutUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    await get_owned_program(
        data.program_id,
        session,
        current_user,
    )

    await get_program_day(
        data.program_id,
        data.program_day_id,
        session,
    )

    if data.program_day_id != workout.program_day_id:
        # Подходы привязаны к упражнениям старого дня
        logged_sets = await session.scalar(
            select(func.count())
            .select_from(WorkoutSet)
            .where(WorkoutSet.scheduled_workout_id == workout.id)
        )

        if logged_sets:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Cannot change the program day of a workout "
                    "that already has logged sets"
                ),
            )

    workout.program_id = data.program_id
    workout.program_day_id = data.program_day_id
    workout.scheduled_date = data.scheduled_date
    workout.status = data.status.value

    await session.commit()
    await session.refresh(workout)

    return workout


@router.patch(
    "/{scheduled_workout_id}",
    response_model=ScheduledWorkoutResponse,
)
async def patch_scheduled_workout(
    scheduled_workout_id: int,
    data: ScheduledWorkoutPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Перенести тренировку на другую дату или сменить статус."""
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    apply_changes(workout, data, partial=True)

    if data.status is not None:
        workout.status = data.status.value

    await session.commit()
    await session.refresh(workout)

    return workout


@router.delete(
    "/{scheduled_workout_id}",
    status_code=204,
)
async def delete_scheduled_workout(
    scheduled_workout_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    await session.delete(workout)
    await session.commit()
