import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Sex = Literal["male", "female"]
Activity = Literal["minimal", "light", "moderate", "high", "extreme"]
Goal = Literal["lose", "maintain", "gain"]
Meal = Literal["breakfast", "lunch", "dinner", "snack"]

Age = Annotated[int, Field(ge=12, le=100)]
Height = Annotated[float, Field(ge=100, le=250)]
BodyWeight = Annotated[float, Field(ge=20, le=400)]
Kcal = Annotated[float, Field(ge=0, le=20000)]
Grams = Annotated[float, Field(ge=0, le=5000)]
FoodName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class Anthropometry(BaseModel):
    sex: Sex
    age: Age
    height_cm: Height
    activity: Activity
    goal: Goal


class CalculateRequest(Anthropometry):
    # если не указан — берётся последний вес из журнала
    weight: BodyWeight | None = None


class Calculation(BaseModel):
    weight: float
    # основной обмен и расход за день с учётом активности
    bmr: int
    tdee: int
    kcal: float
    protein: float
    fat: float
    carbs: float


class Targets(BaseModel):
    kcal: Kcal
    protein: Grams
    fat: Grams
    carbs: Grams


class ProfileInput(Anthropometry):
    # своя норма вместо рассчитанной (необязательно)
    targets: Targets | None = None


class ProfileResponse(BaseModel):
    sex: Sex
    age: int
    height_cm: float
    activity: Activity
    goal: Goal
    targets: Targets
    # расчёт по текущему весу — чтобы показать, если норму правили вручную
    calculated: Calculation | None


class FoodInput(BaseModel):
    """Продукт: КБЖУ на 100 г."""

    name: FoodName
    kcal: Kcal
    protein: Grams
    fat: Grams
    carbs: Grams


class FoodResponse(FoodInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EntryInput(BaseModel):
    """Запись дневника: итог на порцию."""

    date: dt.date | None = None
    meal: Meal
    name: FoodName
    grams: Grams | None = None
    kcal: Kcal
    protein: Grams
    fat: Grams
    carbs: Grams
    food_id: int | None = None
    # сохранить в «мои продукты» (пересчитав на 100 г, нужен вес порции)
    save_food: bool = False


class EntryPatch(BaseModel):
    meal: Meal | None = None
    name: FoodName | None = None
    grams: Grams | None = None
    kcal: Kcal | None = None
    protein: Grams | None = None
    fat: Grams | None = None
    carbs: Grams | None = None


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: dt.date
    meal: Meal
    name: str
    grams: float | None
    kcal: float
    protein: float
    fat: float
    carbs: float
    food_id: int | None


class Totals(BaseModel):
    kcal: float = 0
    protein: float = 0
    fat: float = 0
    carbs: float = 0


class DayResponse(BaseModel):
    date: dt.date
    entries: list[EntryResponse]
    totals: Totals
    targets: Targets | None


class DaySummary(Totals):
    date: dt.date
    entries: int


class ClientNutrition(BaseModel):
    """Питание клиента для тренера: норма, день и 7 дней до него."""

    profile: ProfileResponse | None
    day: DayResponse
    week: list[DaySummary]
