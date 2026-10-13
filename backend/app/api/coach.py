"""Кабинет тренера.

Тренер (роль coach, см. COACH_EMAILS) сам добавляет клиентов по email,
без подтверждения клиента. Данные клиента видны, только пока связь
активна (сотрудничество не завершено). Менять данные клиента отсюда
нельзя.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import Pagination, program_access
from app.api.progress import (
    all_exercise_records,
    exercise_history,
    stats_summary,
    weekly_volume,
)
from app.core.dependencies import get_current_coach
from app.database.session import get_session
from app.models.coaching import CoachClient, CoachingStatus, CoachNote
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.scheduled_workout import ScheduledWorkout
from app.models.user import User
from app.models.workout_set import WorkoutSet
from app.schemas.coach import (
    AssignProgramRequest,
    AssignProgramResponse,
    CoachClientCard,
    CoachClientItem,
    CoachExerciseRecords,
    CoachWorkoutItem,
    InviteRequest,
    NoteInput,
    NoteResponse,
    PeriodOverview,
    ScheduleRequest,
)
from app.schemas.program import ProgramResponse
from app.schemas.progress import ExerciseHistoryItem
from app.schemas.progress import StatsSummaryResponse, WeeklyVolumeItem
from app.services.coaching import client_metrics, period_overview
from app.services.programs import (
    copy_program_tree,
    describe_programs,
    load_program_tree,
    schedule_program,
)


router = APIRouter(prefix="/coach", tags=["Coach"])


def now() -> datetime:
    return datetime.now(timezone.utc)


def person(user: User | None) -> dict | None:
    if user is None:
        return None

    return {"id": user.id, "username": user.username, "email": user.email}


def link_item(link: CoachClient, client: User | None, metrics=None) -> dict:
    return {
        "id": link.id,
        "status": link.status,
        "invited_email": link.invited_email,
        "created_at": link.created_at,
        "responded_at": link.responded_at,
        "ended_at": link.ended_at,
        "client": person(client),
        "metrics": metrics,
    }


async def get_active_link(
    session: AsyncSession,
    coach: User,
    client_id: int,
) -> CoachClient:
    """Активная связь с клиентом. Чужие и бывшие клиенты — 404."""
    link = await session.scalar(
        select(CoachClient).where(
            CoachClient.coach_id == coach.id,
            CoachClient.client_id == client_id,
            CoachClient.status == CoachingStatus.active.value,
        )
    )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return link


# ----- Клиенты -----


@router.get("/clients", response_model=list[CoachClientItem])
async def list_clients(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Все связи тренера: ждущие регистрации, активные и бывшие клиенты.
    Для активных — показатели за период (даты включительно)."""
    rows = (
        await session.execute(
            select(CoachClient, User)
            .outerjoin(User, User.id == CoachClient.client_id)
            .where(CoachClient.coach_id == coach.id)
            .order_by(CoachClient.created_at.desc(), CoachClient.id.desc())
        )
    ).all()

    active_ids = [
        link.client_id
        for link, _ in rows
        if link.status == CoachingStatus.active.value
    ]
    metrics = await client_metrics(session, active_ids, date_from, date_to)

    return [
        link_item(
            link,
            client,
            metrics.get(link.client_id)
            if link.status == CoachingStatus.active.value
            else None,
        )
        for link, client in rows
    ]


@router.post(
    "/clients",
    response_model=CoachClientItem,
    status_code=status.HTTP_201_CREATED,
)
async def add_client(
    data: InviteRequest,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Добавить клиента по email — без подтверждения с его стороны.

    Если человек уже зарегистрирован и у него нет другого тренера,
    он сразу становится клиентом. Если ещё не зарегистрирован, запись
    ждёт регистрации с этим email и тогда же становится активной.
    """
    email = data.email.strip().lower()

    if email == coach.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot invite yourself",
        )

    client = await session.scalar(
        select(User).where(func.lower(User.email) == email)
    )

    if client is not None:
        active = await session.scalar(
            select(CoachClient).where(
                CoachClient.client_id == client.id,
                CoachClient.status == CoachingStatus.active.value,
            )
        )

        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Already your client"
                    if active.coach_id == coach.id
                    else "Client already has a coach"
                ),
            )

        link = CoachClient(
            coach_id=coach.id,
            client_id=client.id,
            invited_email=email,
            status=CoachingStatus.active.value,
            responded_at=datetime.now(timezone.utc),
        )
    else:
        # Этот email уже ждёт регистрации — у будущего клиента
        # тоже может быть только один тренер
        waiting = await session.scalar(
            select(CoachClient).where(
                func.lower(CoachClient.invited_email) == email,
                CoachClient.status == CoachingStatus.invited.value,
            )
        )

        if waiting is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Invitation already sent"
                    if waiting.coach_id == coach.id
                    else "Client already has a coach"
                ),
            )

        link = CoachClient(
            coach_id=coach.id,
            client_id=None,
            invited_email=email,
            status=CoachingStatus.invited.value,
        )

    session.add(link)
    await session.commit()
    await session.refresh(link)

    return link_item(link, client)


@router.delete(
    "/invitations/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_invitation(
    link_id: int,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Убрать клиента, который ещё не зарегистрировался."""
    link = await session.get(CoachClient, link_id)

    if link is None or link.coach_id != coach.id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if link.status != CoachingStatus.invited.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation is already answered",
        )

    await session.delete(link)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/clients/{client_id}/end", response_model=CoachClientItem)
async def end_cooperation(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Завершить сотрудничество. Тренировки клиента остаются у него,
    тренер больше их не видит."""
    link = await get_active_link(session, coach, client_id)
    link.status = CoachingStatus.ended.value
    link.ended_at = now()

    await session.commit()
    await session.refresh(link)

    return link_item(link, await session.get(User, client_id))


# ----- Карточка клиента -----


@router.get("/clients/{client_id}", response_model=CoachClientCard)
async def get_client_card(
    client_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    link = await get_active_link(session, coach, client_id)
    client = await session.get(User, client_id)
    metrics = await client_metrics(session, [client_id], date_from, date_to)

    return {
        "client": person(client),
        "link": link_item(link, client),
        "metrics": metrics[client_id],
    }


@router.get(
    "/clients/{client_id}/summary",
    response_model=StatsSummaryResponse,
)
async def get_client_summary(
    client_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    await get_active_link(session, coach, client_id)

    return await stats_summary(session, client_id, date_from, date_to)


@router.get(
    "/clients/{client_id}/weekly-volume",
    response_model=list[WeeklyVolumeItem],
)
async def get_client_weekly_volume(
    client_id: int,
    weeks: int = Query(12, ge=1, le=104),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    await get_active_link(session, coach, client_id)

    return await weekly_volume(session, client_id, weeks)


@router.get(
    "/clients/{client_id}/records",
    response_model=list[CoachExerciseRecords],
)
async def get_client_records(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Рекорды по всем упражнениям, которые выполнял клиент."""
    await get_active_link(session, coach, client_id)

    return await all_exercise_records(session, client_id)


@router.get(
    "/clients/{client_id}/workouts",
    response_model=list[CoachWorkoutItem],
)
async def get_client_workouts(
    client_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    order: Literal["asc", "desc"] = Query("desc"),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Тренировки клиента с итогами по выполненным подходам и его
    оценкой. По умолчанию от новых к старым; order=asc — расписание
    на ближайшие дни."""
    await get_active_link(session, coach, client_id)

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

    query = (
        select(
            ScheduledWorkout,
            func.coalesce(Program.name, ScheduledWorkout.program_name, ""),
            func.coalesce(ProgramDay.name, ScheduledWorkout.day_name, ""),
            func.coalesce(completed_sets.c.sets, 0),
            func.coalesce(completed_sets.c.volume, 0),
        )
        .outerjoin(Program, Program.id == ScheduledWorkout.program_id)
        .outerjoin(ProgramDay, ProgramDay.id == ScheduledWorkout.program_day_id)
        .outerjoin(
            completed_sets,
            completed_sets.c.workout_id == ScheduledWorkout.id,
        )
        .where(ScheduledWorkout.user_id == client_id)
    )

    if date_from is not None:
        query = query.where(ScheduledWorkout.scheduled_date >= date_from)

    if date_to is not None:
        query = query.where(ScheduledWorkout.scheduled_date <= date_to)

    ordering = (
        (ScheduledWorkout.scheduled_date, ScheduledWorkout.id)
        if order == "asc"
        else (ScheduledWorkout.scheduled_date.desc(), ScheduledWorkout.id.desc())
    )
    result = await session.execute(query.order_by(*ordering).limit(limit))

    return [
        {
            "id": workout.id,
            "scheduled_date": workout.scheduled_date,
            "status": workout.status,
            "program_name": program_name,
            "day_name": day_name,
            "sets_completed": sets,
            "volume": float(volume),
            "wellbeing": workout.wellbeing,
            "difficulty": workout.difficulty,
            "feedback_comment": workout.feedback_comment,
        }
        for workout, program_name, day_name, sets, volume in result.all()
    ]


@router.get(
    "/clients/{client_id}/overview",
    response_model=PeriodOverview,
)
async def get_client_overview(
    client_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Показатели за период и за такой же период перед ним, изменение
    силы и ключевые упражнения. По умолчанию — последние 4 недели."""
    await get_active_link(session, coach, client_id)

    date_to = date_to or date.today()
    date_from = date_from or date_to - timedelta(days=27)

    if date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from is after date_to")

    return await period_overview(session, client_id, date_from, date_to)


@router.get(
    "/clients/{client_id}/exercises/{exercise_id}/history",
    response_model=list[ExerciseHistoryItem],
)
async def get_client_exercise_history(
    client_id: int,
    exercise_id: int,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    pagination: Pagination = Depends(),
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Подходы клиента по упражнению, от новых к старым."""
    await get_active_link(session, coach, client_id)

    return await exercise_history(
        session,
        client_id,
        exercise_id,
        date_from,
        date_to,
        pagination.limit,
        pagination.offset,
    )


# ----- Программы клиента -----


@router.get(
    "/clients/{client_id}/programs",
    response_model=list[ProgramResponse],
)
async def list_client_programs(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Программы клиента. Менять тренер может те, что назначил сам."""
    await get_active_link(session, coach, client_id)

    programs = (
        await session.scalars(
            select(Program).where(Program.user_id == client_id).order_by(Program.id)
        )
    ).all()

    return await describe_programs(session, list(programs), coach)


@router.post(
    "/clients/{client_id}/programs",
    response_model=AssignProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_program(
    client_id: int,
    data: AssignProgramRequest,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Назначить клиенту программу: у клиента появляется своя копия,
    которую ведёт тренер. Шаблон тренера при этом не меняется.
    Можно сразу разложить её по календарю клиента."""
    await get_active_link(session, coach, client_id)

    source = await load_program_tree(session, data.program_id)

    if source is None or source.user_id not in (None, coach.id):
        raise HTTPException(status_code=404, detail="Program not found")

    program = copy_program_tree(source, client_id, assigned_by_coach_id=coach.id)
    session.add(program)
    await session.flush()

    workouts = []

    if data.schedule is not None:
        workouts = await schedule_program(
            session,
            program,
            data.schedule.start_date,
            data.schedule.weeks,
            data.schedule.weekdays,
        )

    await session.commit()

    return {"program_id": program.id, "workouts_created": len(workouts)}


@router.post(
    "/clients/{client_id}/programs/{program_id}/schedule",
    response_model=AssignProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_client_program(
    client_id: int,
    program_id: int,
    data: ScheduleRequest,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Разложить назначенную программу по календарю клиента."""
    await get_active_link(session, coach, client_id)

    program = await session.get(Program, program_id)

    if program is None or program.user_id != client_id:
        raise HTTPException(status_code=404, detail="Program not found")

    _, can_edit = await program_access(program, session, coach)

    if not can_edit:
        raise HTTPException(status_code=403, detail="Program is read-only")

    workouts = await schedule_program(
        session, program, data.start_date, data.weeks, data.weekdays
    )
    await session.commit()

    return {"program_id": program.id, "workouts_created": len(workouts)}


# ----- Заметки тренера -----


async def get_own_note(
    session: AsyncSession,
    coach: User,
    note_id: int,
) -> CoachNote:
    note = await session.get(CoachNote, note_id)

    if note is None or note.coach_id != coach.id:
        raise HTTPException(status_code=404, detail="Note not found")

    await get_active_link(session, coach, note.client_id)

    return note


@router.get(
    "/clients/{client_id}/notes",
    response_model=list[NoteResponse],
)
async def list_notes(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    """Заметки о клиенте, от новых к старым."""
    await get_active_link(session, coach, client_id)

    return (
        await session.scalars(
            select(CoachNote)
            .where(
                CoachNote.coach_id == coach.id,
                CoachNote.client_id == client_id,
            )
            .order_by(CoachNote.created_at.desc(), CoachNote.id.desc())
        )
    ).all()


@router.post(
    "/clients/{client_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    client_id: int,
    data: NoteInput,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    await get_active_link(session, coach, client_id)

    note = CoachNote(coach_id=coach.id, client_id=client_id, text=data.text)
    session.add(note)
    await session.commit()
    await session.refresh(note)

    return note


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: int,
    data: NoteInput,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    note = await get_own_note(session, coach, note_id)
    note.text = data.text

    await session.commit()
    await session.refresh(note)

    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    session: AsyncSession = Depends(get_session),
    coach: User = Depends(get_current_coach),
):
    note = await get_own_note(session, coach, note_id)

    await session.delete(note)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
