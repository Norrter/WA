from pydantic import BaseModel, ConfigDict

from app.core.load import LoadType

from app.schemas.common import LongText, Name, PatchModel, ShortText


class ExerciseCreate(BaseModel):
    name: Name
    description: LongText | None = None
    muscle_group: ShortText | None = None
    equipment: ShortText | None = None
    # как считать нагрузку: вес снаряда / свой вес + доп. вес / гравитрон
    load_type: LoadType = "external"


class ExerciseUpdate(BaseModel):
    name: Name
    description: LongText | None = None
    muscle_group: ShortText | None = None
    equipment: ShortText | None = None
    load_type: LoadType = "external"


class ExercisePatch(PatchModel):
    not_nullable = frozenset({"name", "load_type"})

    name: Name | None = None
    description: LongText | None = None
    muscle_group: ShortText | None = None
    equipment: ShortText | None = None
    load_type: LoadType | None = None


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    muscle_group: str | None
    equipment: str | None
    load_type: str = "external"
    # None = общее упражнение, иначе id автора
    created_by_user_id: int | None
