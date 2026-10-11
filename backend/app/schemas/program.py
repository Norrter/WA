from pydantic import BaseModel, ConfigDict

from app.schemas.common import LongText, Name, PatchModel
from app.schemas.program_day import ProgramDayResponse


class ProgramCreate(BaseModel):
    name: Name
    description: LongText | None = None


class ProgramUpdate(BaseModel):
    name: Name
    description: LongText | None = None


class ProgramPatch(PatchModel):
    not_nullable = frozenset({"name"})

    name: Name | None = None
    description: LongText | None = None


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


class ProgramDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    days: list[ProgramDayResponse]
