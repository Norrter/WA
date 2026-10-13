from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PatchModel


SetNumber = Annotated[int, Field(ge=1, le=100)]
Weight = Annotated[float, Field(ge=0, le=2000)]
Reps = Annotated[int, Field(ge=1, le=1000)]


class WorkoutSetCreate(BaseModel):
    program_exercise_id: int
    set_number: SetNumber
    weight: Weight
    reps: Reps
    completed: bool = True


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
    exercise_id: int
    set_number: int
    weight: float
    reps: int
    completed: bool
