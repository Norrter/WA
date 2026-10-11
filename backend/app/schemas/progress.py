from datetime import date

from pydantic import BaseModel


class ExerciseHistoryItem(BaseModel):
    """Один выполненный подход в истории упражнения."""

    workout_set_id: int
    scheduled_workout_id: int
    date: date
    set_number: int
    weight: float
    reps: int
    completed: bool


class RecordSet(BaseModel):
    weight: float
    reps: int
    date: date


class ExerciseRecordsResponse(BaseModel):
    """Личные рекорды по упражнению (только выполненные подходы)."""

    exercise_id: int
    total_sets: int
    total_reps: int
    total_volume: float
    last_performed: date | None
    # Подход с самым большим весом
    max_weight: RecordSet | None
    # Подход с лучшим расчётным одноповторным максимумом (формула Эпли)
    best_estimated_1rm_set: RecordSet | None
    best_estimated_1rm: float | None


class StatsSummaryResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    workouts_planned: int
    workouts_completed: int
    workouts_skipped: int
    total_sets: int
    total_reps: int
    # Объём = сумма вес × повторы по выполненным подходам
    total_volume: float


class WeeklyVolumeItem(BaseModel):
    # Понедельник этой недели
    week_start: date
    workouts: int
    sets: int
    reps: int
    volume: float
