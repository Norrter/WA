"""Питание: норма КБЖУ по антропометрии, свои продукты и дневник."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.nutrition import Food, FoodEntry, NutritionProfile
from app.models.user import User
from app.schemas.nutrition import (
    CalculateRequest,
    Calculation,
    DayResponse,
    DaySummary,
    EntryInput,
    EntryPatch,
    EntryResponse,
    FoodInput,
    FoodResponse,
    ProfileInput,
    ProfileResponse,
)
from app.services.nutrition import age_from_birth_year, calculate


router = APIRouter(prefix="/nutrition", tags=["Nutrition"])


def need_weight(user: User, weight: float | None) -> float:
    value = weight if weight is not None else user.body_weight

    if value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your body weight first",
        )

    return value


def run_calculation(data, weight: float) -> dict:
    return {
        "weight": weight,
        **calculate(
            sex=data.sex,
            age=data.age,
            height_cm=data.height_cm,
            weight=weight,
            activity=data.activity,
            goal=data.goal,
        ),
    }


def profile_targets(profile: NutritionProfile) -> dict:
    return {
        "kcal": profile.target_kcal,
        "protein": profile.target_protein,
        "fat": profile.target_fat,
        "carbs": profile.target_carbs,
    }


def describe_profile(profile: NutritionProfile, user: User) -> dict:
    age = age_from_birth_year(profile.birth_year)
    data = {
        "sex": profile.sex,
        "age": age,
        "height_cm": profile.height_cm,
        "activity": profile.activity,
        "goal": profile.goal,
    }

    calculated = None

    if user.body_weight is not None and 12 <= age <= 100:
        calculated = run_calculation(CalculateRequest(**data), user.body_weight)

    return {**data, "targets": profile_targets(profile), "calculated": calculated}


# ----- Норма -----


@router.post("/calculate", response_model=Calculation)
async def calculate_norm(
    data: CalculateRequest,
    current_user: User = Depends(get_current_user),
):
    """Посчитать норму без сохранения. Вес — из запроса или из журнала."""
    return run_calculation(data, need_weight(current_user, data.weight))


@router.get("/profile", response_model=ProfileResponse | None)
async def get_profile(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Сохранённая норма и данные для расчёта; null, если ещё не считали."""
    profile = await session.get(NutritionProfile, current_user.id)
    return describe_profile(profile, current_user) if profile else None


@router.put("/profile", response_model=ProfileResponse)
async def save_profile(
    data: ProfileInput,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Сохранить антропометрию и норму. Без targets норма рассчитывается
    по текущему весу тела."""
    if data.targets is not None:
        targets = data.targets.model_dump()
    else:
        calculation = run_calculation(data, need_weight(current_user, None))
        targets = {key: calculation[key] for key in ("kcal", "protein", "fat", "carbs")}

    profile = await session.get(NutritionProfile, current_user.id)

    if profile is None:
        profile = NutritionProfile(user_id=current_user.id)
        session.add(profile)

    profile.sex = data.sex
    profile.birth_year = date.today().year - data.age
    profile.height_cm = data.height_cm
    profile.activity = data.activity
    profile.goal = data.goal
    profile.target_kcal = targets["kcal"]
    profile.target_protein = targets["protein"]
    profile.target_fat = targets["fat"]
    profile.target_carbs = targets["carbs"]

    await session.commit()
    await session.refresh(profile)

    return describe_profile(profile, current_user)


# ----- Дневник -----


async def get_own_entry(session: AsyncSession, user: User, entry_id: int) -> FoodEntry:
    entry = await session.get(FoodEntry, entry_id)

    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Entry not found")

    return entry


async def get_own_food(session: AsyncSession, user: User, food_id: int) -> Food:
    food = await session.get(Food, food_id)

    if food is None or food.user_id != user.id:
        raise HTTPException(status_code=404, detail="Food not found")

    return food


def round1(value: float) -> float:
    return round(value, 1)


async def day_payload(session: AsyncSession, user_id: int, day: date) -> dict:
    entries = (
        await session.scalars(
            select(FoodEntry)
            .where(FoodEntry.user_id == user_id, FoodEntry.date == day)
            .order_by(FoodEntry.created_at, FoodEntry.id)
        )
    ).all()

    totals = {
        key: round1(sum(getattr(entry, key) for entry in entries))
        for key in ("kcal", "protein", "fat", "carbs")
    }

    profile = await session.get(NutritionProfile, user_id)

    return {
        "date": day,
        "entries": entries,
        "totals": totals,
        "targets": profile_targets(profile) if profile else None,
    }


async def summary_payload(
    session: AsyncSession, user_id: int, date_from: date, date_to: date
) -> list[dict]:
    rows = (
        await session.execute(
            select(
                FoodEntry.date,
                func.count(),
                func.sum(FoodEntry.kcal),
                func.sum(FoodEntry.protein),
                func.sum(FoodEntry.fat),
                func.sum(FoodEntry.carbs),
            )
            .where(
                FoodEntry.user_id == user_id,
                FoodEntry.date >= date_from,
                FoodEntry.date <= date_to,
            )
            .group_by(FoodEntry.date)
            .order_by(FoodEntry.date)
        )
    ).all()

    return [
        {
            "date": day,
            "entries": count,
            "kcal": round1(kcal),
            "protein": round1(protein),
            "fat": round1(fat),
            "carbs": round1(carbs),
        }
        for day, count, kcal, protein, fat, carbs in rows
    ]


async def profile_payload(session: AsyncSession, user: User) -> dict | None:
    profile = await session.get(NutritionProfile, user.id)
    return describe_profile(profile, user) if profile else None


@router.get("/day", response_model=DayResponse)
async def get_day(
    day: date | None = Query(None, alias="date"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Дневник за день: записи, итог и норма."""
    return await day_payload(session, current_user.id, day or date.today())


@router.get("/summary", response_model=list[DaySummary])
async def get_summary(
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Итоги по дням за период (только дни с записями)."""
    return await summary_payload(session, current_user.id, date_from, date_to)


@router.post("/entries", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
async def add_entry(
    data: EntryInput,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Добавить еду в дневник. save_food сохраняет её в «мои продукты»
    с пересчётом на 100 г (нужен вес порции)."""
    food_id = data.food_id

    if food_id is not None:
        await get_own_food(session, current_user, food_id)

    if data.save_food and food_id is None:
        if not data.grams:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portion weight is needed to save the food",
            )

        factor = 100 / data.grams
        food = Food(
            user_id=current_user.id,
            name=data.name,
            kcal=round1(data.kcal * factor),
            protein=round1(data.protein * factor),
            fat=round1(data.fat * factor),
            carbs=round1(data.carbs * factor),
        )
        session.add(food)
        await session.flush()
        food_id = food.id

    entry = FoodEntry(
        user_id=current_user.id,
        date=data.date or date.today(),
        meal=data.meal,
        name=data.name,
        grams=data.grams,
        kcal=round1(data.kcal),
        protein=round1(data.protein),
        fat=round1(data.fat),
        carbs=round1(data.carbs),
        food_id=food_id,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)

    return entry


@router.patch("/entries/{entry_id}", response_model=EntryResponse)
async def change_entry(
    entry_id: int,
    data: EntryPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    entry = await get_own_entry(session, current_user, entry_id)

    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None and key != "grams":
            continue
        setattr(entry, key, round1(value) if isinstance(value, float) else value)

    await session.commit()
    await session.refresh(entry)

    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    entry = await get_own_entry(session, current_user, entry_id)
    await session.delete(entry)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----- Мои продукты -----


@router.get("/foods", response_model=list[FoodResponse])
async def list_foods(
    q: str | None = Query(None, max_length=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Food).where(Food.user_id == current_user.id)

    if q:
        query = query.where(Food.name.ilike(f"%{q.strip()}%"))

    return (await session.scalars(query.order_by(func.lower(Food.name)))).all()


@router.post("/foods", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def add_food(
    data: FoodInput,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    food = Food(user_id=current_user.id, **data.model_dump())
    session.add(food)
    await session.commit()
    await session.refresh(food)

    return food


@router.put("/foods/{food_id}", response_model=FoodResponse)
async def update_food(
    food_id: int,
    data: FoodInput,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    food = await get_own_food(session, current_user, food_id)

    for key, value in data.model_dump().items():
        setattr(food, key, value)

    await session.commit()
    await session.refresh(food)

    return food


@router.delete("/foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(
    food_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить продукт. Записи дневника с ним остаются."""
    food = await get_own_food(session, current_user, food_id)
    await session.delete(food)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
