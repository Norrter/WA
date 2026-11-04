"""nutrition: profile with daily norm, own foods, food diary

Revision ID: a9d4f7c2e6b1
Revises: f1c6a3e9d5b8
Create Date: 2026-10-22 23:00:00.000000

Раздел «Питание»: антропометрия и норма КБЖУ, свои продукты (на 100 г)
и дневник питания по дням. Существующие данные не меняются.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9d4f7c2e6b1"
down_revision: Union[str, Sequence[str], None] = "f1c6a3e9d5b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_profiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("birth_year", sa.Integer(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("activity", sa.String(20), nullable=False),
        sa.Column("goal", sa.String(20), nullable=False),
        sa.Column("target_kcal", sa.Float(), nullable=False),
        sa.Column("target_protein", sa.Float(), nullable=False),
        sa.Column("target_fat", sa.Float(), nullable=False),
        sa.Column("target_carbs", sa.Float(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("sex IN ('male', 'female')", name="ck_nutrition_profiles_sex"),
        sa.CheckConstraint(
            "activity IN ('minimal', 'light', 'moderate', 'high', 'extreme')",
            name="ck_nutrition_profiles_activity",
        ),
        sa.CheckConstraint(
            "goal IN ('lose', 'maintain', 'gain')",
            name="ck_nutrition_profiles_goal",
        ),
    )

    op.create_table(
        "foods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("kcal", sa.Float(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("fat", sa.Float(), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_foods_user_id", "foods", ["user_id"])

    op.create_table(
        "food_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal", sa.String(20), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("grams", sa.Float(), nullable=True),
        sa.Column("kcal", sa.Float(), nullable=False),
        sa.Column("protein", sa.Float(), nullable=False),
        sa.Column("fat", sa.Float(), nullable=False),
        sa.Column("carbs", sa.Float(), nullable=False),
        sa.Column(
            "food_id",
            sa.Integer(),
            sa.ForeignKey("foods.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "meal IN ('breakfast', 'lunch', 'dinner', 'snack')",
            name="ck_food_entries_meal",
        ),
    )
    op.create_index("ix_food_entries_user_date", "food_entries", ["user_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_food_entries_user_date", table_name="food_entries")
    op.drop_table("food_entries")
    op.drop_index("ix_foods_user_id", table_name="foods")
    op.drop_table("foods")
    op.drop_table("nutrition_profiles")
