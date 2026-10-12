from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import OrderIndex, PatchModel


SetsCount = Annotated[int, Field(ge=1, le=100)]
Reps = Annotated[int, Field(ge=1, le=1000)]
Weight = Annotated[float, Field(ge=0, le=2000)]
RestSeconds = Annotated[int, Field(ge=0, le=3600)]
Notes = Annotated[str, StringConstraints(max_length=2000)]


class ProgramExerciseCreate(BaseModel):
    exercise_id: int
    order_index: OrderIndex
    sets: SetsCount
    target_reps: Reps | None = None
    target_reps_max: Reps | None = None
    target_weight: Weight | None = None
    rest_seconds: RestSeconds | None = None
    notes: Notes | None = None


class ProgramExerciseUpdate(BaseModel):
    exercise_id: int
    order_index: OrderIndex
    sets: SetsCount
    target_reps: Reps | None = None
    target_reps_max: Reps | None = None
    target_weight: Weight | None = None
    rest_seconds: RestSeconds | None = None
    notes: Notes | None = None


class ProgramExercisePatch(PatchModel):
    not_nullable = frozenset({"exercise_id", "order_index", "sets"})

    exercise_id: int | None = None
    order_index: OrderIndex | None = None
    sets: SetsCount | None = None
    target_reps: Reps | None = None
    target_reps_max: Reps | None = None
    target_weight: Weight | None = None
    rest_seconds: RestSeconds | None = None
    notes: Notes | None = None


class ExerciseShortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProgramExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_day_id: int
    exercise_id: int
    exercise: ExerciseShortResponse
    order_index: int
    sets: int
    target_reps: int | None
    target_reps_max: int | None
    target_weight: float | None
    rest_seconds: int | None
    notes: str | None
