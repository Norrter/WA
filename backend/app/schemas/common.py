from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, StringConstraints, model_validator


# Название: без пробелов по краям, не пустое, до 150 символов
Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]

# Короткая подпись (группа мышц, оборудование)
ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

LongText = Annotated[str, StringConstraints(max_length=5000)]

OrderIndex = Annotated[int, Field(ge=0, le=10_000)]


class PatchModel(BaseModel):
    """База для схем частичного обновления (PATCH).

    Все поля необязательные: меняется только то, что прислали.
    Поля из not_nullable нельзя явно обнулить через null.
    """

    not_nullable: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        for field_name in self.model_fields_set & self.not_nullable:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")

        return self


class ReorderRequest(BaseModel):
    """Новый порядок элементов: список их id сверху вниз."""

    ids: list[int] = Field(min_length=1)

    @model_validator(mode="after")
    def ids_are_unique(self):
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("ids must be unique")

        return self
