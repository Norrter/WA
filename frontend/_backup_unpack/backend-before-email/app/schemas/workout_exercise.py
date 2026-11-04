from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import PatchModel


SetsCount = Annotated[int, Field(ge=1, le=20)]
Reps = Annotated[int, Field(ge=1, le=1000)]
Weight = Annotated[float, Field(ge=0, le=2000)]
RestSeconds = Annotated[int, Field(ge=0, le=3600)]


class WorkoutExerciseCreate(BaseModel):
    """Добавить упражнение в тренировку (в программу оно не попадает)."""

    exercise_id: int
    sets: SetsCount = 3
    target_reps: Reps | None = None
    target_reps_max: Reps | None = None
    target_weight: Weight | None = None
    rest_seconds: RestSeconds | None = None


class WorkoutExercisePatch(PatchModel):
    """Поменять число подходов, цель или заменить упражнение."""

    not_nullable = frozenset({"exercise_id", "sets"})

    exercise_id: int | None = None
    sets: SetsCount | None = None
    target_reps: Reps | None = None
    target_reps_max: Reps | None = None
    target_weight: Weight | None = None
    rest_seconds: RestSeconds | None = None

    @model_validator(mode="after")
    def reps_range(self):
        if (
            self.target_reps is not None
            and self.target_reps_max is not None
            and self.target_reps_max < self.target_reps
        ):
            raise ValueError("target_reps_max must be greater than or equal to target_reps")
        return self


class WorkoutExerciseMove(BaseModel):
    direction: Literal["up", "down"]
