import datetime as dt
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


BodyWeight = Annotated[float, Field(ge=20, le=400)]


class BodyWeightInput(BaseModel):
    weight: BodyWeight
    # по умолчанию — сегодня
    date: dt.date | None = None


class BodyWeightEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: dt.date
    weight: float
