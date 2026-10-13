"""history protection, coach programs, workout feedback

Revision ID: a4c9e2f7b1d3
Revises: f3b7d1e9a2c4
Create Date: 2026-10-13 18:00:00.000000

1. История тренировок больше не удаляется вместе с планом:
   - у тренировки свой владелец (user_id) и копия названий программы
     и дня; program_id и program_day_id при удалении плана становятся
     пустыми вместо удаления тренировки;
   - у подхода записано упражнение (exercise_id); program_exercise_id
     при удалении упражнения из плана становится пустым.
   Новые поля заполняются из существующих данных.
2. Программа, назначенная тренером: assigned_by_coach_id
   и source_program_id.
3. Обратная связь после тренировки: самочувствие, сложность,
   комментарий.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4c9e2f7b1d3"
down_revision: Union[str, Sequence[str], None] = "f3b7d1e9a2c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ----- Тренировки: владелец и названия -----
    op.add_column("scheduled_workouts", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("scheduled_workouts", sa.Column("program_name", sa.String(150), nullable=True))
    op.add_column("scheduled_workouts", sa.Column("day_name", sa.String(150), nullable=True))

    op.execute(
        """
        UPDATE scheduled_workouts AS w
        SET user_id = p.user_id,
            program_name = p.name,
            day_name = d.name
        FROM programs AS p, program_days AS d
        WHERE p.id = w.program_id AND d.id = w.program_day_id
        """
    )
    # Тренировок без владельца быть не должно (шаблоны не планируются),
    # но на всякий случай не оставляем «ничьих» записей
    op.execute("DELETE FROM scheduled_workouts WHERE user_id IS NULL")

    op.alter_column("scheduled_workouts", "user_id", nullable=False)
    op.create_foreign_key(
        "scheduled_workouts_user_id_fkey",
        "scheduled_workouts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_scheduled_workouts_user_id", "scheduled_workouts", ["user_id"])

    for column, table in (("program_id", "programs"), ("program_day_id", "program_days")):
        op.drop_constraint(f"scheduled_workouts_{column}_fkey", "scheduled_workouts", type_="foreignkey")
        op.alter_column("scheduled_workouts", column, nullable=True)
        op.create_foreign_key(
            f"scheduled_workouts_{column}_fkey",
            "scheduled_workouts",
            table,
            [column],
            ["id"],
            ondelete="SET NULL",
        )

    # ----- Обратная связь -----
    op.add_column("scheduled_workouts", sa.Column("wellbeing", sa.SmallInteger(), nullable=True))
    op.add_column("scheduled_workouts", sa.Column("difficulty", sa.SmallInteger(), nullable=True))
    op.add_column("scheduled_workouts", sa.Column("feedback_comment", sa.Text(), nullable=True))
    op.add_column(
        "scheduled_workouts",
        sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_scheduled_workouts_wellbeing",
        "scheduled_workouts",
        "wellbeing BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "ck_scheduled_workouts_difficulty",
        "scheduled_workouts",
        "difficulty BETWEEN 1 AND 10",
    )

    # ----- Подходы: упражнение -----
    op.add_column("workout_sets", sa.Column("exercise_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE workout_sets AS s
        SET exercise_id = pe.exercise_id
        FROM program_exercises AS pe
        WHERE pe.id = s.program_exercise_id
        """
    )
    op.alter_column("workout_sets", "exercise_id", nullable=False)
    op.create_foreign_key(
        "workout_sets_exercise_id_fkey",
        "workout_sets",
        "exercises",
        ["exercise_id"],
        ["id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_index("ix_workout_sets_exercise_id", "workout_sets", ["exercise_id"])

    op.drop_constraint("workout_sets_program_exercise_id_fkey", "workout_sets", type_="foreignkey")
    op.alter_column("workout_sets", "program_exercise_id", nullable=True)
    op.create_foreign_key(
        "workout_sets_program_exercise_id_fkey",
        "workout_sets",
        "program_exercises",
        ["program_exercise_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ----- Программы тренера -----
    op.add_column("programs", sa.Column("assigned_by_coach_id", sa.Integer(), nullable=True))
    op.add_column("programs", sa.Column("source_program_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "programs_assigned_by_coach_id_fkey",
        "programs",
        "users",
        ["assigned_by_coach_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "programs_source_program_id_fkey",
        "programs",
        "programs",
        ["source_program_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("programs_source_program_id_fkey", "programs", type_="foreignkey")
    op.drop_constraint("programs_assigned_by_coach_id_fkey", "programs", type_="foreignkey")
    op.drop_column("programs", "source_program_id")
    op.drop_column("programs", "assigned_by_coach_id")

    # Подходы и тренировки без плана при откате удаляются:
    # старая схема не умеет их хранить
    op.execute("DELETE FROM workout_sets WHERE program_exercise_id IS NULL")
    op.drop_constraint("workout_sets_program_exercise_id_fkey", "workout_sets", type_="foreignkey")
    op.alter_column("workout_sets", "program_exercise_id", nullable=False)
    op.create_foreign_key(
        "workout_sets_program_exercise_id_fkey",
        "workout_sets",
        "program_exercises",
        ["program_exercise_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index("ix_workout_sets_exercise_id", table_name="workout_sets")
    op.drop_constraint("workout_sets_exercise_id_fkey", "workout_sets", type_="foreignkey")
    op.drop_column("workout_sets", "exercise_id")

    op.drop_constraint("ck_scheduled_workouts_difficulty", "scheduled_workouts", type_="check")
    op.drop_constraint("ck_scheduled_workouts_wellbeing", "scheduled_workouts", type_="check")
    for column in ("feedback_at", "feedback_comment", "difficulty", "wellbeing"):
        op.drop_column("scheduled_workouts", column)

    op.execute(
        "DELETE FROM scheduled_workouts WHERE program_id IS NULL OR program_day_id IS NULL"
    )
    for column, table in (("program_id", "programs"), ("program_day_id", "program_days")):
        op.drop_constraint(f"scheduled_workouts_{column}_fkey", "scheduled_workouts", type_="foreignkey")
        op.alter_column("scheduled_workouts", column, nullable=False)
        op.create_foreign_key(
            f"scheduled_workouts_{column}_fkey",
            "scheduled_workouts",
            table,
            [column],
            ["id"],
            ondelete="CASCADE",
        )

    op.drop_index("ix_scheduled_workouts_user_id", table_name="scheduled_workouts")
    op.drop_constraint("scheduled_workouts_user_id_fkey", "scheduled_workouts", type_="foreignkey")
    op.drop_column("scheduled_workouts", "day_name")
    op.drop_column("scheduled_workouts", "program_name")
    op.drop_column("scheduled_workouts", "user_id")
