import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

LeadStatus = Literal["new", "in_progress", "done", "rejected"]


class OfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    kind: str
    subtitle: str | None
    price: int
    price_unit: str | None
    features: list[str]
    is_featured: bool


class LeadInput(BaseModel):
    offer_id: int | None = None
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    # телефон, Telegram или email
    contact: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
    goal: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    # ловушка для ботов: поле скрыто, человек его не заполняет
    website: str | None = Field(None, max_length=200)
    # галочка согласия на обработку персональных данных (152-ФЗ)
    consent: bool = False


class LeadCreated(BaseModel):
    id: int


class LeadPatch(BaseModel):
    status: LeadStatus | None = None
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    offer_id: int | None
    offer_title: str | None
    name: str
    contact: str
    goal: str | None
    status: LeadStatus
    note: str | None
    created_at: dt.datetime
    updated_at: dt.datetime
