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


class ProgramAuthor(BaseModel):
    id: int
    username: str
    email: str


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # Владелец; пусто у готовых шаблонов
    user_id: int | None = None
    name: str
    description: str | None
    # Можно ли текущему пользователю менять программу. Программу от
    # тренера клиент только смотрит и может скопировать себе
    can_edit: bool = False
    # Тренер, который назначил программу
    assigned_by: ProgramAuthor | None = None
    # Из какой программы сделана копия
    source_program_id: int | None = None


class ProgramDetailResponse(ProgramResponse):
    days: list[ProgramDayResponse]
