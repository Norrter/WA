"""Питание: профиль с нормой КБЖУ, свои продукты и дневник по дням."""

import datetime as dt

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NutritionProfile(Base):
    """Антропометрия для расчёта нормы и сама норма (можно поправить вручную)."""

    __tablename__ = "nutrition_profiles"

    __table_args__ = (
        CheckConstraint("sex IN ('male', 'female')", name="ck_nutrition_profiles_sex"),
        CheckConstraint(
            "activity IN ('minimal', 'light', 'moderate', 'high', 'extreme')",
            name="ck_nutrition_profiles_activity",
        ),
        CheckConstraint(
            "goal IN ('lose', 'maintain', 'gain')",
            name="ck_nutrition_profiles_goal",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    sex: Mapped[str] = mapped_column(String(10), nullable=False)
    birth_year: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    activity: Mapped[str] = mapped_column(String(20), nullable=False)
    goal: Mapped[str] = mapped_column(String(20), nullable=False)

    # Норма в день
    target_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    target_protein: Mapped[float] = mapped_column(Float, nullable=False)
    target_fat: Mapped[float] = mapped_column(Float, nullable=False)
    target_carbs: Mapped[float] = mapped_column(Float, nullable=False)

    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Food(Base):
    """Свой продукт: КБЖУ на 100 г, чтобы быстро добавлять в дневник."""

    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class FoodEntry(Base):
    """Запись дневника: что съедено за приём пищи (итог на порцию)."""

    __tablename__ = "food_entries"

    __table_args__ = (
        CheckConstraint(
            "meal IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_food_entries_meal",
        ),
        Index("ix_food_entries_user_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    meal: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    # вес порции, если известен
    grams: Mapped[float | None] = mapped_column(Float, nullable=True)

    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, nullable=False)
    fat: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)

    # продукт, из которого добавлено (если был)
    food_id: Mapped[int | None] = mapped_column(
        ForeignKey("foods.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
