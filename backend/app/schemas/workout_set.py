from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import PatchModel


SetNumber = Annotated[int, Field(ge=1, le=100)]
Weight = Annotated[float, Field(ge=0, le=2000)]
Reps = Annotated[int, Field(ge=1, le=1000)]


class WorkoutSetCreate(BaseModel):
    """Подход записывается к строке программы (program_exercise_id) или,
    если план тренировки меняли, к её строке (workout_exercise_id)."""

    program_exercise_id: int | None = None
    workout_exercise_id: int | None = None
    set_number: SetNumber
    weight: Weight
    reps: Reps
    completed: bool = True

    @model_validator(mode="after")
    def one_target(self):
        if (self.program_exercise_id is None) == (self.workout_exercise_id is None):
            raise ValueError("Pass either program_exercise_id or workout_exercise_id")
        return self


class WorkoutSetUpdate(BaseModel):
    program_exercise_id: int
    set_number: SetNumber
    weight: Weight
    reps: Reps
    completed: bool


class WorkoutSetPatch(PatchModel):
    not_nullable = frozenset(
        {"program_exercise_id", "set_number", "weight", "reps", "completed"}
    )

    program_exercise_id: int | None = None
    set_number: SetNumber | None = None
    weight: Weight | None = None
    reps: Reps | None = None
    completed: bool | None = None


class WorkoutSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheduled_workout_id: int
    # пусто, если упражнение потом убрали из плана
    program_exercise_id: int | None
    # строка своего плана тренировки
    workout_exercise_id: int | None = None
    exercise_id: int
    set_number: int
    # введённый вес: снаряд, доп. вес или противовес гравитрона
    weight: float
    # вес тела на момент подхода (для упражнений со своим весом)
    body_weight: float | None = None
    # нагрузка с учётом веса тела — по ней считается статистика
    load: float
    reps: int
    completed: bool
