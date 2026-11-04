from pydantic import BaseModel, ConfigDict

from app.schemas.common import Name, OrderIndex, PatchModel
from app.schemas.program_exercise import ProgramExerciseResponse


class ProgramDayCreate(BaseModel):
    name: Name
    order_index: OrderIndex


class ProgramDayUpdate(BaseModel):
    name: Name
    order_index: OrderIndex


class ProgramDayPatch(PatchModel):
    not_nullable = frozenset({"name", "order_index"})

    name: Name | None = None
    order_index: OrderIndex | None = None


class ProgramDayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: int
    name: str
    order_index: int
    exercises: list[ProgramExerciseResponse]
