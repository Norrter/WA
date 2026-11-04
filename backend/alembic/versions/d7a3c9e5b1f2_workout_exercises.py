"""workout exercises: change the plan during a workout

Revision ID: d7a3c9e5b1f2
Revises: c5d2a8f1e7b3
Create Date: 2026-10-22 21:00:00.000000

Во время тренировки можно добавить, заменить, убрать упражнение или
поменять число подходов — программа при этом не меняется. Изменённый
план тренировки хранится в workout_exercises, а подходы ссылаются на
свою строку через workout_sets.workout_exercise_id. Новые поля пустые:
существующие тренировки идут по дню программы, как раньше.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7a3c9e5b1f2"
down_revision: Union[str, Sequence[str], None] = "c5d2a8f1e7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scheduled_workout_id",
            sa.Integer(),
            sa.ForeignKey("scheduled_workouts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            sa.Integer(),
            sa.ForeignKey("exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "program_exercise_id",
            sa.Integer(),
            sa.ForeignKey("program_exercises.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("sets", sa.SmallInteger(), nullable=False),
        sa.Column("target_reps", sa.Integer(), nullable=True),
        sa.Column("target_reps_max", sa.Integer(), nullable=True),
        sa.Column("target_weight", sa.Float(), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("sets BETWEEN 1 AND 20", name="ck_workout_exercises_sets"),
    )
    op.create_index(
        "ix_workout_exercises_scheduled_workout_id",
        "workout_exercises",
        ["scheduled_workout_id"],
    )

    op.add_column(
        "scheduled_workouts",
        sa.Column("custom_plan", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    op.add_column(
        "workout_sets",
        sa.Column("workout_exercise_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workout_sets_workout_exercise_id",
        "workout_sets",
        "workout_exercises",
        ["workout_exercise_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_workout_sets_workout_exercise_id",
        "workout_sets",
        ["workout_exercise_id"],
    )
    op.create_unique_constraint(
        "uq_workout_sets_item_set_number",
        "workout_sets",
        ["workout_exercise_id", "set_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_workout_sets_item_set_number", "workout_sets", type_="unique")
    op.drop_index("ix_workout_sets_workout_exercise_id", table_name="workout_sets")
    op.drop_constraint(
        "fk_workout_sets_workout_exercise_id",
        "workout_sets",
        type_="foreignkey",
    )
    op.drop_column("workout_sets", "workout_exercise_id")
    op.drop_column("scheduled_workouts", "custom_plan")
    op.drop_index("ix_workout_exercises_scheduled_workout_id", table_name="workout_exercises")
    op.drop_table("workout_exercises")
