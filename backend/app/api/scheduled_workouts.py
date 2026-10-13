from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import (
    Pagination,
    apply_changes,
    get_owned_workout,
    get_schedulable_program,
)
from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.exercise import Exercise
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
from app.services.programs import schedule_program


router = APIRouter(
    prefix="/scheduled-workouts",
    tags=["Scheduled Workouts"],
)

FEEDBACK_FIELDS = {"wellbeing", "difficulty", "feedback_comment"}


async def get_program_day(
    program_id: int,
    program_day_id: int,
    session: AsyncSession,
) -> ProgramDay:
    program_day = await session.scalar(
        select(ProgramDay).where(
            ProgramDay.id == program_day_id,
            ProgramDay.program_id == program_id,
        )
    )

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
    program = await get_schedulable_program(
        data.program_id,
        session,
        current_user,
    )

    day = await get_program_day(
        data.program_id,
        data.program_day_id,
        session,
    )

    workout = ScheduledWorkout(
        user_id=current_user.id,
        program_id=program.id,
        program_day_id=day.id,
        program_name=program.name,
        day_name=day.name,
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
    program = await get_schedulable_program(
        data.program_id,
        session,
        current_user,
    )

    workouts = await schedule_program(
        session,
        program,
        data.start_date,
        data.weeks,
        data.weekdays,
    )

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
    query = select(ScheduledWorkout).where(
        ScheduledWorkout.user_id == current_user.id,
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


async def workout_detail(session: AsyncSession, workout: ScheduledWorkout) -> dict:
    """Тренировка целиком: план дня и сделанные подходы. Подходы
    по упражнениям, которых в плане уже нет, тоже показываются."""
    program = (
        await session.get(Program, workout.program_id)
        if workout.program_id is not None
        else None
    )

    day = None

    if workout.program_day_id is not None:
        day = await session.scalar(
            select(ProgramDay)
            .options(
                selectinload(ProgramDay.exercises)
                .selectinload(ProgramExercise.exercise)
            )
            .where(ProgramDay.id == workout.program_day_id)
        )

    sets = (
        await session.scalars(
            select(WorkoutSet)
            .where(WorkoutSet.scheduled_workout_id == workout.id)
            .order_by(WorkoutSet.set_number, WorkoutSet.id)
        )
    ).all()

    planned_ids = {item.id for item in day.exercises} if day else set()
    by_plan: dict[int, list[WorkoutSet]] = {}
    orphans: dict[int, list[WorkoutSet]] = {}

    for workout_set in sets:
        if workout_set.program_exercise_id in planned_ids:
            by_plan.setdefault(workout_set.program_exercise_id, []).append(workout_set)
        else:
            orphans.setdefault(workout_set.exercise_id, []).append(workout_set)

    exercises = [
        {
            "program_exercise_id": item.id,
            "exercise": item.exercise,
            "order_index": item.order_index,
            "sets": item.sets,
            "target_reps": item.target_reps,
            "target_reps_max": item.target_reps_max,
            "target_weight": item.target_weight,
            "rest_seconds": item.rest_seconds,
            "notes": item.notes,
            "performed_sets": by_plan.get(item.id, []),
        }
        for item in (day.exercises if day else [])
    ]

    if orphans:
        known = {
            exercise.id: exercise
            for exercise in (
                await session.scalars(select(Exercise).where(Exercise.id.in_(orphans)))
            ).all()
        }
        start = max((item["order_index"] for item in exercises), default=0) + 1

        for offset, (exercise_id, performed) in enumerate(orphans.items()):
            exercises.append(
                {
                    "program_exercise_id": None,
                    "exercise": known[exercise_id],
                    "order_index": start + offset,
                    "sets": len(performed),
                    "target_reps": None,
                    "target_reps_max": None,
                    "target_weight": None,
                    "rest_seconds": None,
                    "notes": None,
                    "performed_sets": performed,
                }
            )

    coach_name = None

    if program is not None and program.assigned_by_coach_id is not None:
        coach = await session.get(User, program.assigned_by_coach_id)
        coach_name = coach.username if coach else None

    return {
        "id": workout.id,
        "program_id": workout.program_id,
        "program_name": program.name if program else (workout.program_name or "Программа"),
        "program_day_id": workout.program_day_id,
        "program_day_name": day.name if day else (workout.day_name or "Тренировка"),
        "scheduled_date": workout.scheduled_date,
        "status": workout.status,
        "wellbeing": workout.wellbeing,
        "difficulty": workout.difficulty,
        "feedback_comment": workout.feedback_comment,
        "feedback_at": workout.feedback_at,
        "coach_name": coach_name,
        "exercises": exercises,
    }


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

    return await workout_detail(session, workout)


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

    program = await get_schedulable_program(
        data.program_id,
        session,
        current_user,
    )

    day = await get_program_day(
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

    workout.program_id = program.id
    workout.program_day_id = day.id
    workout.program_name = program.name
    workout.day_name = day.name
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
    """Перенести тренировку, сменить статус или оставить оценку:
    самочувствие (1–5), сложность (1–10) и комментарий."""
    workout = await get_owned_workout(
        scheduled_workout_id,
        session,
        current_user,
    )

    apply_changes(workout, data, partial=True)

    if data.status is not None:
        workout.status = data.status.value

    if data.model_fields_set & FEEDBACK_FIELDS:
        if workout.feedback_comment == "":
            workout.feedback_comment = None

        workout.feedback_at = datetime.now(timezone.utc)

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
