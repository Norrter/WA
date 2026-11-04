"""body weight and load: bodyweight and assisted exercises

Revision ID: e8b4d2a6c9f1
Revises: d7a3c9e5b1f2
Create Date: 2026-10-22 22:00:00.000000

1. users.body_weight — вес тела.
2. exercises.load_type — как считать нагрузку: вес снаряда (external),
   свой вес + доп. вес (bodyweight), свой вес с облегчением (assisted).
   Подтягивания и отжимания из справочника становятся bodyweight.
3. Новые упражнения справочника с противовесом: подтягивания
   и отжимания на брусьях в гравитроне.
4. workout_sets.body_weight и workout_sets.load. Для старых подходов
   load = weight, вес тела неизвестен — история не меняется.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8b4d2a6c9f1"
down_revision: Union[str, Sequence[str], None] = "d7a3c9e5b1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BODYWEIGHT = [
    "Подтягивания",
    "Отжимания на брусьях",
    "Отжимания от пола",
    "Отжимания от скамьи",
]

ASSISTED = [
    ("Подтягивания в гравитроне", "Спина", "Тренажёр",
     "Противовес облегчает подтягивание: чем он меньше, тем ближе к подтягиваниям "
     "без помощи. Нагрузка = вес тела − противовес."),
    ("Отжимания на брусьях в гравитроне", "Грудь", "Тренажёр",
     "Колени на платформе с противовесом, корпус чуть наклонён вперёд. "
     "Нагрузка = вес тела − противовес."),
]


def upgrade() -> None:
    op.add_column("users", sa.Column("body_weight", sa.Float(), nullable=True))

    op.add_column(
        "exercises",
        sa.Column("load_type", sa.String(20), server_default="external", nullable=False),
    )
    op.create_check_constraint(
        "ck_exercises_load_type",
        "exercises",
        "load_type IN ('external', 'bodyweight', 'assisted')",
    )

    op.add_column("workout_sets", sa.Column("body_weight", sa.Float(), nullable=True))
    op.add_column("workout_sets", sa.Column("load", sa.Float(), nullable=True))
    op.execute("UPDATE workout_sets SET load = weight")
    op.alter_column("workout_sets", "load", nullable=False)

    exercises = sa.table(
        "exercises",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("muscle_group", sa.String),
        sa.column("equipment", sa.String),
        sa.column("load_type", sa.String),
        sa.column("created_by_user_id", sa.Integer),
    )

    op.execute(
        exercises.update()
        .where(
            exercises.c.created_by_user_id.is_(None),
            exercises.c.name.in_(BODYWEIGHT),
        )
        .values(load_type="bodyweight")
    )

    connection = op.get_bind()

    for name, muscle_group, equipment, description in ASSISTED:
        exists = connection.execute(
            sa.select(sa.func.count())
            .select_from(exercises)
            .where(exercises.c.created_by_user_id.is_(None), exercises.c.name == name)
        ).scalar()

        if exists:
            op.execute(
                exercises.update()
                .where(exercises.c.created_by_user_id.is_(None), exercises.c.name == name)
                .values(load_type="assisted")
            )
        else:
            op.execute(
                exercises.insert().values(
                    name=name,
                    description=description,
                    muscle_group=muscle_group,
                    equipment=equipment,
                    load_type="assisted",
                )
            )


def downgrade() -> None:
    # Добавленные упражнения справочника остаются, если по ним есть подходы.
    # Отложенные проверки внешних ключей выполняем сразу, иначе ALTER TABLE
    # ниже не пройдёт
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.execute(
        """
        DELETE FROM exercises e
        WHERE e.created_by_user_id IS NULL
          AND e.name IN ('Подтягивания в гравитроне', 'Отжимания на брусьях в гравитроне')
          AND NOT EXISTS (SELECT 1 FROM workout_sets s WHERE s.exercise_id = e.id)
          AND NOT EXISTS (SELECT 1 FROM program_exercises p WHERE p.exercise_id = e.id)
        """
    )
    op.drop_column("workout_sets", "load")
    op.drop_column("workout_sets", "body_weight")
    op.drop_constraint("ck_exercises_load_type", "exercises", type_="check")
    op.drop_column("exercises", "load_type")
    op.drop_column("users", "body_weight")
