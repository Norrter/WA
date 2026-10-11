from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.scheduled_workout import WorkoutStatus
from app.schemas.common import PatchModel
from app.schemas.program_exercise import ExerciseShortResponse
from app.schemas.workout_set import WorkoutSetResponse


class ScheduledWorkoutCreate(BaseModel):
    program_id: int
    program_day_id: int
    scheduled_date: date
    status: WorkoutStatus = WorkoutStatus.planned


class ScheduledWorkoutUpdate(BaseModel):
    program_id: int
    program_day_id: int
    scheduled_date: date
    status: WorkoutStatus


class ScheduledWorkoutPatch(PatchModel):
    """Частичное обновление: перенести дату или сменить статус."""

    not_nullable = frozenset({"scheduled_date", "status"})

    scheduled_date: date | None = None
    status: WorkoutStatus | None = None


class ScheduledWorkoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    program_day_id: int
    scheduled_date: date
    status: WorkoutStatus


class GenerateScheduleRequest(BaseModel):
    """Разложить программу по календарю на несколько недель вперёд."""

    program_id: int
    start_date: date
    weeks: int = Field(ge=1, le=52)
    # Дни недели для тренировок: 0 = понедельник ... 6 = воскресенье
    weekdays: list[int] = Field(min_length=1, max_length=7)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekdays must be between 0 (Mon) and 6 (Sun)")

        if len(set(value)) != len(value):
            raise ValueError("weekdays must be unique")

        return sorted(value)


class WorkoutExerciseDetail(BaseModel):
    """Упражнение в тренировке: план и фактически сделанные подходы."""

    program_exercise_id: int
    exercise: ExerciseShortResponse
    order_index: int
    sets: int
    target_reps: int | None
    target_weight: float | None
    rest_seconds: int | None
    notes: str | None
    performed_sets: list[WorkoutSetResponse]


class ScheduledWorkoutDetailResponse(BaseModel):
    """Всё для экрана тренировки одним ответом."""

    id: int
    program_id: int
    program_name: str
    program_day_id: int
    program_day_name: str
    scheduled_date: date
    status: WorkoutStatus
    exercises: list[WorkoutExerciseDetail]
