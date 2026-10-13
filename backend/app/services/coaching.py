"""Показатели клиентов для кабинета тренера.

Всё считается одним проходом по тренировкам и подходам выбранных
клиентов, чтобы список клиентов не делал запросы на каждого.
"""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.progress import estimate_1rm
from app.config import settings
from app.models.exercise import Exercise
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.scheduled_workout import ScheduledWorkout, WorkoutStatus
from app.models.workout_set import WorkoutSet


def in_range(day: date, start: date | None, end: date | None) -> bool:
    return (start is None or day >= start) and (end is None or day <= end)


def improved_records(
    sets: list[tuple[int, date, float]],
    start: date,
    end: date,
) -> int:
    """Сколько упражнений побили свой прошлый лучший расчётный максимум
    в промежутке [start, end]. sets — (упражнение, дата, расчётный максимум).
    Первое выполнение упражнения рекордом не считается: сравнивать не с чем."""
    best_before: dict[int, float] = {}
    best_inside: dict[int, float] = {}

    for exercise_id, day, value in sets:
        if day < start:
            best_before[exercise_id] = max(best_before.get(exercise_id, 0), value)
        elif day <= end:
            best_inside[exercise_id] = max(best_inside.get(exercise_id, 0), value)

    return sum(
        1
        for exercise_id, value in best_inside.items()
        if exercise_id in best_before and value > best_before[exercise_id]
    )


async def client_metrics(
    session: AsyncSession,
    client_ids: list[int],
    date_from: date | None,
    date_to: date | None,
    today: date | None = None,
) -> dict[int, dict]:
    """Показатели каждого клиента за период (даты включительно)."""
    today = today or date.today()
    result = {client_id: empty_metrics() for client_id in client_ids}

    if not client_ids:
        return result

    workouts = await session.execute(
        select(
            ScheduledWorkout.user_id,
            ScheduledWorkout.id,
            ScheduledWorkout.status,
            ScheduledWorkout.scheduled_date,
            func.coalesce(Program.name, ScheduledWorkout.program_name, ""),
            func.coalesce(ProgramDay.name, ScheduledWorkout.day_name, ""),
            ScheduledWorkout.wellbeing,
            ScheduledWorkout.difficulty,
        )
        .outerjoin(Program, Program.id == ScheduledWorkout.program_id)
        .outerjoin(ProgramDay, ProgramDay.id == ScheduledWorkout.program_day_id)
        .where(ScheduledWorkout.user_id.in_(client_ids))
    )

    feedback: dict[int, dict[str, list[int]]] = defaultdict(
        lambda: {"wellbeing": [], "difficulty": []}
    )

    for (
        client_id,
        workout_id,
        status,
        day,
        program_name,
        day_name,
        wellbeing,
        difficulty,
    ) in workouts.all():
        metrics = result[client_id]

        if in_range(day, date_from, date_to):
            if wellbeing is not None:
                feedback[client_id]["wellbeing"].append(wellbeing)
            if difficulty is not None:
                feedback[client_id]["difficulty"].append(difficulty)

        if status == WorkoutStatus.completed.value:
            if metrics["last_workout"] is None or day > metrics["last_workout"]:
                metrics["last_workout"] = day

        if status == WorkoutStatus.planned.value and day >= today:
            upcoming = metrics["next_workout"]

            if upcoming is None or (day, workout_id) < (
                upcoming["date"],
                upcoming["id"],
            ):
                metrics["next_workout"] = {
                    "id": workout_id,
                    "date": day,
                    "program_name": program_name,
                    "day_name": day_name,
                }

        if not in_range(day, date_from, date_to):
            continue

        if status == WorkoutStatus.completed.value:
            metrics["workouts_completed"] += 1
        elif status == WorkoutStatus.skipped.value:
            metrics["workouts_skipped"] += 1
        elif day < today:
            # план прошёл, а тренировка так и не отмечена
            metrics["workouts_missed"] += 1
        else:
            metrics["workouts_upcoming"] += 1

    sets = await session.execute(
        select(
            ScheduledWorkout.user_id,
            WorkoutSet.exercise_id,
            ScheduledWorkout.scheduled_date,
            WorkoutSet.weight,
            WorkoutSet.reps,
        )
        .join(ScheduledWorkout, ScheduledWorkout.id == WorkoutSet.scheduled_workout_id)
        .where(
            ScheduledWorkout.user_id.in_(client_ids),
            WorkoutSet.completed.is_(True),
        )
    )

    estimated: dict[int, list[tuple[int, date, float]]] = defaultdict(list)

    for client_id, exercise_id, day, weight, reps in sets.all():
        estimated[client_id].append((exercise_id, day, estimate_1rm(weight, reps)))

        if in_range(day, date_from, date_to):
            result[client_id]["total_sets"] += 1
            result[client_id]["total_volume"] += weight * reps

    stagnation_start = today - timedelta(days=settings.coach_stagnation_days)

    for client_id, metrics in result.items():
        client_sets = estimated.get(client_id, [])

        due = (
            metrics["workouts_completed"]
            + metrics["workouts_skipped"]
            + metrics["workouts_missed"]
        )
        metrics["adherence"] = (
            round(metrics["workouts_completed"] / due, 3) if due else None
        )

        if date_from is not None:
            metrics["new_records"] = improved_records(
                client_sets, date_from, date_to or today
            )

        for key in ("wellbeing", "difficulty"):
            values = feedback[client_id][key] if client_id in feedback else []
            metrics[f"avg_{key}"] = round(sum(values) / len(values), 1) if values else None

        metrics["days_since_last_workout"] = (
            (today - metrics["last_workout"]).days
            if metrics["last_workout"] is not None
            else None
        )

        reasons = []

        if (
            metrics["days_since_last_workout"] is None
            or metrics["days_since_last_workout"] > settings.coach_inactive_days
        ):
            reasons.append("inactive")

        if (
            metrics["adherence"] is not None
            and metrics["adherence"] < settings.coach_adherence_threshold
        ):
            reasons.append("low_adherence")

        trained_recently = any(day >= stagnation_start for _, day, _ in client_sets)
        has_history = any(day < stagnation_start for _, day, _ in client_sets)

        if (
            not reasons
            and trained_recently
            and has_history
            and improved_records(client_sets, stagnation_start, today) == 0
        ):
            reasons.append("stagnation")

        metrics["reasons"] = reasons

        if "inactive" in reasons or "low_adherence" in reasons:
            metrics["flag"] = "check"
        elif "stagnation" in reasons:
            metrics["flag"] = "progress"
        else:
            metrics["flag"] = "on_track"

    return result


def empty_metrics() -> dict:
    return {
        "workouts_completed": 0,
        "workouts_skipped": 0,
        # прошедшие тренировки из плана, которые не отмечены
        "workouts_missed": 0,
        "workouts_upcoming": 0,
        "adherence": None,
        "total_sets": 0,
        "total_volume": 0.0,
        "new_records": 0,
        # средние оценки клиента после тренировок за период
        "avg_wellbeing": None,
        "avg_difficulty": None,
        "last_workout": None,
        "days_since_last_workout": None,
        "next_workout": None,
        "flag": "on_track",
        "reasons": [],
    }


async def exercise_progress(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    previous_from: date,
    limit: int = 6,
) -> tuple[float | None, list[dict]]:
    """Изменение расчётной силы и ключевые упражнения.

    Для каждого упражнения сравнивается лучший расчётный максимум на
    1 повтор за период с лучшим за такой же период до него. Изменение
    силы — среднее изменение по упражнениям, которые делались в обоих
    периодах. Ключевые — упражнения, по которым больше всего подходов
    за период."""
    rows = await session.execute(
        select(
            WorkoutSet.exercise_id,
            Exercise.name,
            Exercise.muscle_group,
            ScheduledWorkout.scheduled_date,
            WorkoutSet.weight,
            WorkoutSet.reps,
        )
        .join(ScheduledWorkout, ScheduledWorkout.id == WorkoutSet.scheduled_workout_id)
        .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
        .where(
            ScheduledWorkout.user_id == user_id,
            WorkoutSet.completed.is_(True),
            ScheduledWorkout.scheduled_date >= previous_from,
            ScheduledWorkout.scheduled_date <= date_to,
        )
    )

    stats: dict[int, dict] = {}

    for exercise_id, name, muscle_group, day, weight, reps in rows.all():
        item = stats.setdefault(
            exercise_id,
            {
                "exercise_id": exercise_id,
                "name": name,
                "muscle_group": muscle_group,
                "best_now": None,
                "best_before": None,
                "sets": 0,
            },
        )
        value = estimate_1rm(weight, reps)
        key = "best_now" if day >= date_from else "best_before"
        item[key] = max(item[key] or 0, value)

        if day >= date_from:
            item["sets"] += 1

    changes = []

    for item in stats.values():
        if item["best_now"] and item["best_before"]:
            item["change"] = round(item["best_now"] / item["best_before"] - 1, 3)
            changes.append(item["change"])
        else:
            item["change"] = None

        for key in ("best_now", "best_before"):
            if item[key] is not None:
                item[key] = round(item[key], 1)

    strength_change = round(sum(changes) / len(changes), 3) if changes else None

    key_exercises = sorted(
        (item for item in stats.values() if item["sets"]),
        key=lambda item: (-item["sets"], item["name"]),
    )[:limit]

    return strength_change, key_exercises


async def period_overview(
    session: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> dict:
    """Показатели за период и за такой же период перед ним."""
    length = (date_to - date_from).days + 1
    previous_to = date_from - timedelta(days=1)
    previous_from = previous_to - timedelta(days=length - 1)

    current = (await client_metrics(session, [user_id], date_from, date_to))[user_id]
    previous = (
        await client_metrics(session, [user_id], previous_from, previous_to)
    )[user_id]

    strength_change, key_exercises = await exercise_progress(
        session, user_id, date_from, date_to, previous_from
    )

    return {
        "date_from": date_from,
        "date_to": date_to,
        "previous_from": previous_from,
        "previous_to": previous_to,
        "current": current,
        "previous": previous,
        "strength_change": strength_change,
        "key_exercises": key_exercises,
    }
