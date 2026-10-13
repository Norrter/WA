from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

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


Wellbeing = Annotated[int, Field(ge=1, le=5)]
Difficulty = Annotated[int, Field(ge=1, le=10)]
Comment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class ScheduledWorkoutPatch(PatchModel):
    """Частичное обновление: перенести дату, сменить статус или оставить
    оценку после тренировки (самочувствие, сложность, комментарий)."""

    not_nullable = frozenset({"scheduled_date", "status"})

    scheduled_date: date | None = None
    status: WorkoutStatus | None = None
    # самочувствие: 1 — плохо ... 5 — отлично
    wellbeing: Wellbeing | None = None
    # субъективная сложность: 1 — очень легко ... 10 — на пределе
    difficulty: Difficulty | None = None
    feedback_comment: Comment | None = None


class WorkoutFeedback(BaseModel):
    wellbeing: int | None = None
    difficulty: int | None = None
    feedback_comment: str | None = None
    feedback_at: datetime | None = None


class ScheduledWorkoutResponse(WorkoutFeedback):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # пусто, если программу или день потом удалили — тренировка
    # осталась в истории с названиями из program_name и day_name
    program_id: int | None
    program_day_id: int | None
    program_name: str | None = None
    day_name: str | None = None
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
    """Упражнение в тренировке: план и фактически сделанные подходы.
    program_exercise_id пустой, если упражнение потом убрали из плана:
    тогда здесь только сделанные подходы, без плана."""

    program_exercise_id: int | None
    exercise: ExerciseShortResponse
    order_index: int
    sets: int
    target_reps: int | None
    target_reps_max: int | None
    target_weight: float | None
    rest_seconds: int | None
    notes: str | None
    performed_sets: list[WorkoutSetResponse]


class ScheduledWorkoutDetailResponse(WorkoutFeedback):
    """Всё для экрана тренировки одним ответом."""

    id: int
    program_id: int | None
    program_name: str
    program_day_id: int | None
    program_day_name: str
    # программу ведёт тренер (для подписи на экране)
    coach_name: str | None = None
    scheduled_date: date
    status: WorkoutStatus
    exercises: list[WorkoutExerciseDetail]
