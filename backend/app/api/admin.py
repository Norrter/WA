"""Админ-панель: любые данные любой таблицы.

Доступна только администраторам (ADMIN_EMAILS). Таблицы и поля
описываются по моделям, поэтому новые поля появляются в панели сами.
Проверки базы (уникальность, связи, допустимые значения) работают
как обычно: нарушение — ответ 409 с понятным текстом.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    or_,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin
from app.core.roles import role_for_email
from app.core.security import hash_password
from app.database.session import get_session
from app.models.coaching import CoachClient, CoachNote
from app.models.exercise import Exercise
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.user import User
from app.models.workout_set import WorkoutSet


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin)],
)


@dataclass
class AdminTable:
    model: type
    label: str
    # колонки в списке
    list_columns: list[str]
    # по каким полям искать
    search: list[str] = field(default_factory=list)
    # поля только для чтения (кроме id и дат создания)
    readonly: set[str] = field(default_factory=set)
    # поля, которые не показываются вовсе
    hidden: set[str] = field(default_factory=set)
    # подсказки к полям
    hints: dict[str, str] = field(default_factory=dict)


TABLES: dict[str, AdminTable] = {
    "users": AdminTable(
        User,
        "Пользователи",
        ["id", "username", "email", "role", "created_at"],
        search=["username", "email"],
        readonly={"role"},
        hidden={"password_hash"},
        hints={"role": "Тренер задаётся переменной COACH_EMAILS"},
    ),
    "exercises": AdminTable(
        Exercise,
        "Упражнения",
        ["id", "name", "muscle_group", "equipment", "created_by_user_id"],
        search=["name", "muscle_group", "equipment"],
        hints={"created_by_user_id": "Пусто — общее упражнение для всех"},
    ),
    "programs": AdminTable(
        Program,
        "Программы",
        ["id", "name", "user_id", "assigned_by_coach_id"],
        search=["name", "description"],
        hints={"user_id": "Пусто — готовая программа для всех"},
    ),
    "program_days": AdminTable(
        ProgramDay,
        "Дни программ",
        ["id", "program_id", "name", "order_index"],
        search=["name"],
    ),
    "program_exercises": AdminTable(
        ProgramExercise,
        "Упражнения в днях",
        ["id", "program_day_id", "exercise_id", "sets", "target_reps", "target_weight"],
        search=["notes"],
    ),
    "scheduled_workouts": AdminTable(
        ScheduledWorkout,
        "Тренировки",
        ["id", "user_id", "scheduled_date", "status", "day_name"],
        search=["day_name", "program_name", "status", "feedback_comment"],
        hints={
            "wellbeing": "Самочувствие 1–5",
            "difficulty": "Сложность 1–10",
        },
    ),
    "workout_sets": AdminTable(
        WorkoutSet,
        "Подходы",
        ["id", "scheduled_workout_id", "exercise_id", "set_number", "weight", "reps", "completed"],
    ),
    "coach_clients": AdminTable(
        CoachClient,
        "Тренеры и клиенты",
        ["id", "coach_id", "client_id", "invited_email", "status"],
        search=["invited_email", "status"],
    ),
    "coach_notes": AdminTable(
        CoachNote,
        "Заметки тренеров",
        ["id", "coach_id", "client_id", "text", "created_at"],
        search=["text"],
    ),
}

# Допустимые значения для полей-списков
CHOICES = {
    ("users", "role"): ["user", "coach"],
    ("scheduled_workouts", "status"): [item.value for item in WorkoutStatus],
    ("coach_clients", "status"): ["invited", "active", "declined", "ended"],
}

AUTOMATIC = {"created_at", "updated_at"}


def get_table(name: str) -> AdminTable:
    table = TABLES.get(name)

    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    return table


def column_kind(column) -> str:
    column_type = column.type

    if isinstance(column_type, Boolean):
        return "boolean"
    if isinstance(column_type, (Integer, SmallInteger)):
        return "integer"
    if isinstance(column_type, Float):
        return "number"
    if isinstance(column_type, DateTime):
        return "datetime"
    if isinstance(column_type, Date):
        return "date"
    if isinstance(column_type, Text):
        return "text"
    if isinstance(column_type, String):
        return "string"

    return "string"


def columns_info(name: str, table: AdminTable) -> list[dict]:
    result = []

    for column in table.model.__table__.columns:
        if column.name in table.hidden:
            continue

        foreign = next(iter(column.foreign_keys), None)
        readonly = (
            column.primary_key
            or column.name in AUTOMATIC
            or column.name in table.readonly
        )

        result.append(
            {
                "name": column.name,
                "kind": column_kind(column),
                "nullable": bool(column.nullable),
                "readonly": readonly,
                # обязательно при создании
                "required": (
                    not column.nullable
                    and not readonly
                    and column.default is None
                    and column.server_default is None
                ),
                "max_length": getattr(column.type, "length", None),
                "references": foreign.column.table.name if foreign is not None else None,
                "choices": CHOICES.get((name, column.name)),
                "hint": table.hints.get(column.name),
            }
        )

    if table.model is User:
        # Пароль хранится в виде хеша: задать можно, увидеть нельзя
        result.append(
            {
                "name": "password",
                "kind": "password",
                "nullable": True,
                "readonly": False,
                "required": True,
                "max_length": 128,
                "references": None,
                "choices": None,
                "hint": "Новый пароль, не короче 8 символов. Пусто — не менять",
            }
        )

    return result


def serialize(table: AdminTable, row) -> dict:
    data = {}

    for column in table.model.__table__.columns:
        if column.name in table.hidden:
            continue

        value = getattr(row, column.name)

        if isinstance(value, (date, datetime)):
            value = value.isoformat()

        data[column.name] = value

    return data


def bad(column: str, message: str) -> HTTPException:
    return HTTPException(status_code=422, detail=f"{column}: {message}")


def coerce(name: str, info: dict, value: Any) -> Any:
    """Привести значение из формы к типу поля."""
    column = info["name"]

    if value is None or (value == "" and info["kind"] not in ("string", "text")):
        if not info["nullable"]:
            raise bad(column, "обязательное поле")
        return None

    kind = info["kind"]

    try:
        if kind == "integer":
            if isinstance(value, bool):
                raise ValueError
            value = int(value)
        elif kind == "number":
            if isinstance(value, bool):
                raise ValueError
            value = float(value)
        elif kind == "boolean":
            if not isinstance(value, bool):
                raise ValueError
        elif kind == "date":
            value = date.fromisoformat(str(value)[:10])
        elif kind == "datetime":
            value = datetime.fromisoformat(str(value))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
        else:
            value = str(value)
    except (TypeError, ValueError):
        raise bad(column, "неверное значение")

    if kind in ("string", "text"):
        if not value.strip() and not info["nullable"]:
            raise bad(column, "обязательное поле")
        if value == "" and info["nullable"]:
            return None
        if info["max_length"] and len(value) > info["max_length"]:
            raise bad(column, f"не длиннее {info['max_length']} символов")

    if info["choices"] and value not in info["choices"]:
        raise bad(column, f"допустимо: {', '.join(info['choices'])}")

    return value


def apply_values(
    name: str,
    table: AdminTable,
    row,
    values: dict,
    *,
    creating: bool,
) -> None:
    infos = {info["name"]: info for info in columns_info(name, table)}

    unknown = set(values) - set(infos)

    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Неизвестные поля: {', '.join(sorted(unknown))}",
        )

    if creating:
        missing = [
            column
            for column, info in infos.items()
            if info["required"] and values.get(column) in (None, "")
        ]

        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Обязательные поля: {', '.join(missing)}",
            )

    for column, value in values.items():
        info = infos[column]

        if info["readonly"]:
            continue

        if info["kind"] == "password":
            if value in (None, ""):
                continue
            if not isinstance(value, str) or not 8 <= len(value) <= 128:
                raise bad("password", "от 8 до 128 символов")
            row.password_hash = hash_password(value)
            continue

        setattr(row, column, coerce(name, info, value))

    if table.model is User:
        row.role = role_for_email(row.email)


async def get_row(session: AsyncSession, table: AdminTable, row_id: int):
    row = await session.get(table.model, row_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Row not found")

    return row


# ----- Обзор -----


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)):
    """Сколько записей в каждой таблице и активность за неделю."""
    week_ago = date.today() - timedelta(days=6)

    counts = {
        name: await session.scalar(select(func.count()).select_from(table.model))
        for name, table in TABLES.items()
    }

    new_users = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(func.date(User.created_at) >= week_ago)
    )
    completed = select(ScheduledWorkout).where(
        ScheduledWorkout.status == WorkoutStatus.completed.value,
        ScheduledWorkout.scheduled_date >= week_ago,
        ScheduledWorkout.scheduled_date <= date.today(),
    )
    workouts_week = await session.scalar(
        select(func.count()).select_from(completed.subquery())
    )
    active_users = await session.scalar(
        select(func.count(func.distinct(completed.subquery().c.user_id)))
    )

    return {
        "counts": counts,
        "new_users_week": new_users,
        "workouts_week": workouts_week,
        "active_users_week": active_users,
    }


# ----- Таблицы -----


@router.get("/tables")
async def list_tables(session: AsyncSession = Depends(get_session)):
    return [
        {
            "name": name,
            "label": table.label,
            "count": await session.scalar(select(func.count()).select_from(table.model)),
            "list_columns": table.list_columns,
            "searchable": bool(table.search),
            "columns": columns_info(name, table),
        }
        for name, table in TABLES.items()
    ]


@router.get("/tables/{name}/rows")
async def list_rows(
    name: str,
    q: str | None = Query(None, max_length=200),
    field_name: str | None = Query(None, alias="field"),
    value: str | None = Query(None, max_length=200),
    sort: str = Query("id"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Записи таблицы. q — поиск по текстовым полям или по id;
    field + value — точный фильтр, например field=user_id&value=5."""
    table = get_table(name)
    model = table.model
    columns = model.__table__.columns
    query = select(model)

    if q:
        conditions = [getattr(model, column).ilike(f"%{q}%") for column in table.search]

        if q.strip().isdigit():
            conditions.append(model.id == int(q.strip()))

        if conditions:
            query = query.where(or_(*conditions))

    if field_name is not None:
        if field_name not in columns or field_name in table.hidden:
            raise HTTPException(status_code=422, detail="Unknown field")

        info = next(i for i in columns_info(name, table) if i["name"] == field_name)
        query = query.where(
            getattr(model, field_name).is_(None)
            if value in (None, "", "null")
            else getattr(model, field_name) == coerce(name, {**info, "choices": None}, value)
        )

    if sort not in columns or sort in table.hidden:
        raise HTTPException(status_code=422, detail="Unknown sort field")

    total = await session.scalar(select(func.count()).select_from(query.subquery()))

    sort_column = getattr(model, sort)
    rows = (
        await session.scalars(
            query.order_by(sort_column.desc() if order == "desc" else sort_column, model.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return {"total": total, "rows": [serialize(table, row) for row in rows]}


@router.get("/tables/{name}/rows/{row_id}")
async def get_row_endpoint(
    name: str,
    row_id: int,
    session: AsyncSession = Depends(get_session),
):
    table = get_table(name)

    return serialize(table, await get_row(session, table, row_id))


@router.post("/tables/{name}/rows", status_code=status.HTTP_201_CREATED)
async def create_row(
    name: str,
    values: dict = Body(...),
    session: AsyncSession = Depends(get_session),
):
    table = get_table(name)
    row = table.model()
    apply_values(name, table, row, values, creating=True)

    session.add(row)
    await session.commit()
    await session.refresh(row)

    return serialize(table, row)


@router.patch("/tables/{name}/rows/{row_id}")
async def update_row(
    name: str,
    row_id: int,
    values: dict = Body(...),
    session: AsyncSession = Depends(get_session),
):
    table = get_table(name)
    row = await get_row(session, table, row_id)
    apply_values(name, table, row, values, creating=False)

    await session.commit()
    await session.refresh(row)

    return serialize(table, row)


@router.delete("/tables/{name}/rows/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    name: str,
    row_id: int,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(get_current_admin),
):
    """Удалить запись. Связанные записи удаляются или отвязываются
    по правилам базы (например, с пользователем — все его данные)."""
    table = get_table(name)

    if table.model is User and row_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account here",
        )

    row = await get_row(session, table, row_id)

    await session.delete(row)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
