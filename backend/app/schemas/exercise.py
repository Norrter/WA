from pydantic import BaseModel, ConfigDict

from app.schemas.common import LongText, Name, PatchModel, ShortText


class ExerciseCreate(BaseModel):
    name: Name
    description: LongText | None = None
    muscle_group: ShortText | None = None
    equipment: ShortText | None = None


class ExerciseUpdate(BaseModel):
    name: Name
    description: LongText | None = None
    muscle_group: ShortText | None = None
    equipment: ShortText | None = None


class ExercisePatch(PatchModel):
    not_nullable = frozenset({"name"})

    name: Name | None = None
    description: LongText | None = None
    muscle_group: ShortText | None = None
    equipment: ShortText | None = None


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    muscle_group: str | None
    equipment: str | None
    # None = общее упражнение, иначе id автора
    created_by_user_id: int | None
