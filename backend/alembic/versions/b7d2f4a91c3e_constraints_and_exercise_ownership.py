"""constraints and exercise ownership

Revision ID: b7d2f4a91c3e
Revises: 057eeb89e864
Create Date: 2026-10-08 02:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d2f4a91c3e"
down_revision: Union[str, Sequence[str], None] = "057eeb89e864"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. У упражнения появляется автор.
    #    У существующих упражнений автора нет (NULL) — они становятся общими.
    op.add_column(
        "exercises",
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_exercises_created_by_user_id",
        "exercises",
        ["created_by_user_id"],
    )

    op.create_foreign_key(
        "fk_exercises_created_by_user_id_users",
        "exercises",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. Статус тренировки — только из фиксированного набора.
    #    Незнакомые старые значения приводим к planned.
    op.execute(
        sa.text(
            """
            UPDATE scheduled_workouts
            SET status = 'planned'
            WHERE status NOT IN ('planned', 'completed', 'skipped')
            """
        )
    )

    op.create_check_constraint(
        "ck_scheduled_workouts_status",
        "scheduled_workouts",
        "status IN ('planned', 'completed', 'skipped')",
    )

    op.create_index(
        "ix_scheduled_workouts_scheduled_date",
        "scheduled_workouts",
        ["scheduled_date"],
    )

    # 3. Уникальность порядка дней в программе.
    #    Если в какой-то программе уже есть дни с одинаковым order_index,
    #    перенумеровываем дни этой программы как 1, 2, 3...
    op.execute(
        sa.text(
            """
            WITH duplicated AS (
                SELECT DISTINCT program_id
                FROM program_days
                GROUP BY program_id, order_index
                HAVING count(*) > 1
            ),
            renumbered AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY program_id
                        ORDER BY order_index, id
                    ) AS new_index
                FROM program_days
                WHERE program_id IN (SELECT program_id FROM duplicated)
            )
            UPDATE program_days
            SET order_index = renumbered.new_index
            FROM renumbered
            WHERE program_days.id = renumbered.id
            """
        )
    )

    op.create_unique_constraint(
        "uq_program_days_program_id_order_index",
        "program_days",
        ["program_id", "order_index"],
        deferrable=True,
        initially="DEFERRED",
    )

    # 4. То же для порядка упражнений внутри дня
    op.execute(
        sa.text(
            """
            WITH duplicated AS (
                SELECT DISTINCT program_day_id
                FROM program_exercises
                GROUP BY program_day_id, order_index
                HAVING count(*) > 1
            ),
            renumbered AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY program_day_id
                        ORDER BY order_index, id
                    ) AS new_index
                FROM program_exercises
                WHERE program_day_id IN (
                    SELECT program_day_id FROM duplicated
                )
            )
            UPDATE program_exercises
            SET order_index = renumbered.new_index
            FROM renumbered
            WHERE program_exercises.id = renumbered.id
            """
        )
    )

    op.create_unique_constraint(
        "uq_program_exercises_program_day_id_order_index",
        "program_exercises",
        ["program_day_id", "order_index"],
        deferrable=True,
        initially="DEFERRED",
    )

    # 5. Номер подхода уникален в пределах упражнения одной тренировки.
    #    Дубли перенумеровываем, сами подходы не удаляем.
    op.execute(
        sa.text(
            """
            WITH duplicated AS (
                SELECT DISTINCT scheduled_workout_id, program_exercise_id
                FROM workout_sets
                GROUP BY scheduled_workout_id, program_exercise_id, set_number
                HAVING count(*) > 1
            ),
            renumbered AS (
                SELECT
                    ws.id,
                    row_number() OVER (
                        PARTITION BY
                            ws.scheduled_workout_id,
                            ws.program_exercise_id
                        ORDER BY ws.set_number, ws.id
                    ) AS new_number
                FROM workout_sets ws
                JOIN duplicated d
                    ON d.scheduled_workout_id = ws.scheduled_workout_id
                    AND d.program_exercise_id = ws.program_exercise_id
            )
            UPDATE workout_sets
            SET set_number = renumbered.new_number
            FROM renumbered
            WHERE workout_sets.id = renumbered.id
            """
        )
    )

    op.create_unique_constraint(
        "uq_workout_sets_workout_exercise_set_number",
        "workout_sets",
        ["scheduled_workout_id", "program_exercise_id", "set_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_workout_sets_workout_exercise_set_number",
        "workout_sets",
        type_="unique",
    )

    op.drop_constraint(
        "uq_program_exercises_program_day_id_order_index",
        "program_exercises",
        type_="unique",
    )

    op.drop_constraint(
        "uq_program_days_program_id_order_index",
        "program_days",
        type_="unique",
    )

    op.drop_index(
        "ix_scheduled_workouts_scheduled_date",
        table_name="scheduled_workouts",
    )

    op.drop_constraint(
        "ck_scheduled_workouts_status",
        "scheduled_workouts",
        type_="check",
    )

    op.drop_constraint(
        "fk_exercises_created_by_user_id_users",
        "exercises",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_exercises_created_by_user_id",
        table_name="exercises",
    )

    op.drop_column("exercises", "created_by_user_id")
