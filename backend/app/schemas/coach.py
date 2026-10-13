from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.schemas.progress import ExerciseRecordsResponse


class PersonShort(BaseModel):
    id: int
    username: str
    email: str


class NextWorkout(BaseModel):
    id: int
    date: date
    program_name: str
    day_name: str


class ClientMetrics(BaseModel):
    """Показатели клиента за выбранный период."""

    workouts_completed: int
    workouts_skipped: int
    # прошедшие тренировки из плана, которые клиент не отметил
    workouts_missed: int
    workouts_upcoming: int
    # выполнено / (выполнено + пропущено + не отмечено); null — плана не было
    adherence: float | None
    total_sets: int
    # сумма вес × повторы по выполненным подходам
    total_volume: float
    # сколько упражнений побили прошлый лучший расчётный максимум
    new_records: int
    # средние оценки клиента после тренировок за период (1–5 и 1–10)
    avg_wellbeing: float | None = None
    avg_difficulty: float | None = None
    # последняя выполненная тренировка за всё время
    last_workout: date | None
    days_since_last_workout: int | None
    next_workout: NextWorkout | None
    # on_track — «По плану», check — «Проверить»,
    # progress — «Оценить прогресс»
    flag: Literal["on_track", "check", "progress"]
    # inactive, low_adherence, stagnation
    reasons: list[str]


class CoachClientItem(BaseModel):
    """Связь тренера с клиентом: приглашение, активный клиент или бывший."""

    id: int
    status: Literal["invited", "active", "declined", "ended"]
    invited_email: str
    created_at: datetime
    responded_at: datetime | None
    ended_at: datetime | None
    # пусто, пока человек с этим email не зарегистрировался
    client: PersonShort | None
    # только для активных клиентов
    metrics: ClientMetrics | None = None


class InviteRequest(BaseModel):
    email: EmailStr


class CoachClientCard(BaseModel):
    client: PersonShort
    link: CoachClientItem
    metrics: ClientMetrics


class CoachExerciseRecords(ExerciseRecordsResponse):
    exercise_name: str
    muscle_group: str | None


class CoachWorkoutItem(BaseModel):
    """Тренировка клиента с итогами по подходам и его оценкой."""

    id: int
    scheduled_date: date
    status: str
    program_name: str
    day_name: str
    sets_completed: int
    volume: float
    wellbeing: int | None = None
    difficulty: int | None = None
    feedback_comment: str | None = None


class KeyExercise(BaseModel):
    exercise_id: int
    name: str
    muscle_group: str | None
    # лучший расчётный максимум на 1 повтор за период и за период до него
    best_now: float | None
    best_before: float | None
    # изменение: 0.06 = +6%
    change: float | None
    sets: int


class PeriodOverview(BaseModel):
    """Показатели за период и за такой же период перед ним."""

    date_from: date
    date_to: date
    previous_from: date
    previous_to: date
    current: ClientMetrics
    previous: ClientMetrics
    # среднее изменение расчётной силы по упражнениям: 0.06 = +6%
    strength_change: float | None
    key_exercises: list[KeyExercise]


class ScheduleRequest(BaseModel):
    """Разложить программу по календарю."""

    start_date: date
    weeks: int = Field(ge=1, le=52)
    # 0 = понедельник ... 6 = воскресенье
    weekdays: list[int] = Field(min_length=1, max_length=7)

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("weekdays must be between 0 (Mon) and 6 (Sun)")

        if len(set(value)) != len(value):
            raise ValueError("weekdays must be unique")

        return sorted(value)


class AssignProgramRequest(BaseModel):
    # своя программа тренера или готовый шаблон
    program_id: int
    # сразу разложить по календарю клиента
    schedule: ScheduleRequest | None = None


class AssignProgramResponse(BaseModel):
    program_id: int
    workouts_created: int


NoteText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=5000),
]


class NoteInput(BaseModel):
    text: NoteText


class NoteResponse(BaseModel):
    id: int
    text: str
    created_at: datetime
    updated_at: datetime


class CurrentCoach(BaseModel):
    id: int
    coach: PersonShort
    # с какого момента сотрудничают
    since: datetime | None


class CoachingState(BaseModel):
    coach: CurrentCoach | None
