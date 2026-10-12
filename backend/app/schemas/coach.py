from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.progress import ExerciseRecordsResponse


class CoachUserItem(BaseModel):
    """Пользователь в списке тренера: сводка за выбранный период."""

    id: int
    email: str
    username: str
    role: str
    created_at: datetime
    programs: int
    workouts_planned: int
    workouts_completed: int
    workouts_skipped: int
    total_sets: int
    # Объём = сумма вес × повторы по выполненным подходам
    total_volume: float
    # Дата последней выполненной тренировки за всё время
    last_workout: date | None


class CoachExerciseRecords(ExerciseRecordsResponse):
    exercise_name: str
    muscle_group: str | None


class CoachWorkoutItem(BaseModel):
    """Тренировка пользователя с итогами по подходам."""

    id: int
    scheduled_date: date
    status: str
    program_name: str
    day_name: str
    sets_completed: int
    volume: float
