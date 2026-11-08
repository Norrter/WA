"""Копирование программ и раскладка по календарю.

Используется и пользователем (свои программы), и тренером
(назначение программы клиенту).
"""

from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.helpers import program_access
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.user import User


async def load_program_tree(session: AsyncSession, program_id: int) -> Program | None:
    return await session.scalar(
        select(Program)
        .options(
            selectinload(Program.days)
            .selectinload(ProgramDay.exercises)
            .selectinload(ProgramExercise.exercise)
        )
        .where(Program.id == program_id)
    )


def copy_program_tree(
    source: Program,
    owner_id: int,
    *,
    assigned_by_coach_id: int | None = None,
) -> Program:
    """Новая программа со всеми днями и упражнениями источника."""
    return Program(
        user_id=owner_id,
        name=source.name,
        description=source.description,
        assigned_by_coach_id=assigned_by_coach_id,
        source_program_id=source.id,
        days=[
            ProgramDay(
                name=day.name,
                order_index=day.order_index,
                exercises=[
                    ProgramExercise(
                        exercise_id=item.exercise_id,
                        order_index=item.order_index,
                        sets=item.sets,
                        target_reps=item.target_reps,
                        target_reps_max=item.target_reps_max,
                        target_weight=item.target_weight,
                        rest_seconds=item.rest_seconds,
                        notes=item.notes,
                    )
                    for item in day.exercises
                ],
            )
            for day in source.days
        ],
    )


async def schedule_program(
    session: AsyncSession,
    program: Program,
    start_date: date,
    weeks: int,
    weekdays: list[int],
) -> list[ScheduledWorkout]:
    """Разложить программу по календарю.

    Дни программы идут по кругу в своём порядке и ставятся на выбранные
    дни недели, начиная со start_date, на weeks недель. Даты, на которые
    у этой программы уже есть тренировка, пропускаются.
    """
    days = (
        await session.scalars(
            select(ProgramDay)
            .where(ProgramDay.program_id == program.id)
            .order_by(ProgramDay.order_index, ProgramDay.id)
        )
    ).all()

    if not days:
        raise HTTPException(
            status_code=400,
            detail="Program has no days to schedule",
        )

    end_date = start_date + timedelta(weeks=weeks)

    busy_dates = set(
        (
            await session.scalars(
                select(ScheduledWorkout.scheduled_date).where(
                    ScheduledWorkout.program_id == program.id,
                    ScheduledWorkout.scheduled_date >= start_date,
                    ScheduledWorkout.scheduled_date < end_date,
                )
            )
        ).all()
    )

    workouts = []
    current_date = start_date

    while current_date < end_date:
        if current_date.weekday() in weekdays and current_date not in busy_dates:
            day = days[len(workouts) % len(days)]

            workouts.append(
                ScheduledWorkout(
                    user_id=program.user_id,
                    program_id=program.id,
                    program_day_id=day.id,
                    program_name=program.name,
                    day_name=day.name,
                    scheduled_date=current_date,
                    status=WorkoutStatus.planned.value,
                )
            )

        current_date += timedelta(days=1)

    session.add_all(workouts)

    return workouts


async def describe_programs(
    session: AsyncSession,
    programs: list[Program],
    user: User,
) -> list[Program]:
    """Добавить к программам поля для ответа: can_edit и assigned_by."""
    coach_ids = {
        program.assigned_by_coach_id
        for program in programs
        if program.assigned_by_coach_id is not None
    }
    coaches = {}

    if coach_ids:
        coaches = {
            coach.id: coach
            for coach in (
                await session.scalars(select(User).where(User.id.in_(coach_ids)))
            ).all()
        }

    for program in programs:
        _, can_edit = await program_access(program, session, user)
        coach = coaches.get(program.assigned_by_coach_id)

        program.can_edit = can_edit
        program.assigned_by = (
            {"id": coach.id, "username": coach.username, "email": coach.email}
            if coach
            else None
        )

    return programs
