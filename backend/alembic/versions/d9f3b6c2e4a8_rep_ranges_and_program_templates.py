"""rep ranges and program templates

Revision ID: d9f3b6c2e4a8
Revises: c4e8a1d5f2b7
Create Date: 2026-10-12 17:00:00.000000

1. Диапазон повторов в плане: program_exercises.target_reps_max.
2. Программа без владельца (user_id = NULL) — общий шаблон.
3. Упражнения и шаблон программы «Сплит на 4 тренировки».
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9f3b6c2e4a8"
down_revision: Union[str, Sequence[str], None] = "c4e8a1d5f2b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Новые общие упражнения: (название, группа мышц, оборудование, подсказка)
NEW_EXERCISES = [
    ("Сведение рук в тренажёре «бабочка»", "Грудь", "Тренажёр",
     "Спина прижата к спинке, локти чуть согнуты, руки сводятся перед грудью."),
    ("Жим в Смите на наклонной скамье", "Грудь", "Тренажёр",
     "Скамья под 30°, гриф опускается к верху груди."),
    ("Жим в Хаммере на верх груди", "Грудь", "Тренажёр",
     "Рукояти на уровне верха груди, локти не разводятся выше плеч."),
    ("Махи в стороны в тренажёре", "Плечи", "Тренажёр",
     "Сидя, руки поднимаются в стороны до уровня плеч за счёт средней дельты."),
    ("Жим в Хаммере на плечи", "Плечи", "Тренажёр",
     "Спина прижата к спинке, жим вверх без полного выпрямления локтей."),
    ("Разгибание из-за головы в кроссовере", "Трицепс", "Блок",
     "Спиной к блоку, локти смотрят вперёд и не расходятся."),
    ("Разгибания с канатом на блоке", "Трицепс", "Блок",
     "Локти прижаты, внизу концы каната разводятся в стороны."),
    ("Жим в тренажёре на трицепс", "Трицепс", "Тренажёр",
     "Локти вдоль корпуса, руки выпрямляются до конца."),
    ("Тяга гантелей лёжа на наклонной скамье", "Спина", "Гантели",
     "Грудью на скамье под 45°, локти идут назад вдоль корпуса."),
    ("Тяга одной рукой в блочном тренажёре", "Спина", "Тренажёр",
     "Корпус неподвижен, локоть идёт назад, лопатка сводится к позвоночнику."),
    ("Тяга верхнего блока узким обратным хватом", "Спина", "Блок",
     "Ладони к себе, рукоять тянется к низу груди, локти вдоль корпуса."),
    ("Пуловер на блоке с рогами", "Спина", "Блок",
     "Руки почти прямые, рукоять опускается к бёдрам по дуге."),
    ("Сгибания в тренажёре Скотта", "Бицепс", "Тренажёр",
     "Плечи лежат на подушке, без рывка в начале движения."),
    ("Гак-присед", "Ноги", "Тренажёр",
     "Спина прижата к спинке, колени идут по направлению носков."),
    ("Жим ногами одной ногой", "Ноги", "Тренажёр",
     "Таз не отрывается от сиденья, колено не заваливается внутрь."),
    ("Сгибания ног в тренажёре сидя", "Ноги", "Тренажёр",
     "Валик над пятками, пауза в нижней точке."),
    ("Отведение бедра в тренажёре сидя", "Ягодицы", "Тренажёр",
     "Корпус чуть наклонён вперёд, ноги разводятся без рывков."),
    ("Кардио: эллипс или лестница", "Кардио", "Тренажёр",
     "Ровный темп на пульсе 120–130. Повторы в плане — это минуты."),
]


TEMPLATE_NAME = "Сплит на 4 тренировки"

TEMPLATE_DESCRIPTION = (
    "Четыре тренировки: грудь, плечи и трицепс; спина и бицепс; "
    "грудь, дельты и трицепс; ноги. В конце каждой — 15 минут кардио "
    "на пульсе 120–130."
)

CARDIO = ("Кардио: эллипс или лестница", 1, 15, None, "15 минут, пульс 120–130")

# День -> упражнения: (название, подходы, повторы от, повторы до, заметка)
TEMPLATE_DAYS = [
    ("Грудь, плечи, трицепс", [
        ("Сведение рук в тренажёре «бабочка»", 4, 12, 15, None),
        ("Жим в Смите на наклонной скамье", 4, 8, 12, "Наклон скамьи 30°"),
        ("Жим в тренажёре сидя", 4, 12, 15, "Блочный тренажёр"),
        ("Махи в стороны в тренажёре", 4, 15, 20, "На среднюю дельту"),
        ("Жим в Хаммере на плечи", 4, 10, 12, "На переднюю дельту"),
        ("Разгибание из-за головы в кроссовере", 4, 10, 12, "Прямая рукоять"),
        CARDIO,
    ]),
    ("Спина, бицепс", [
        ("Тяга гантелей лёжа на наклонной скамье", 4, 8, 12, "Наклон скамьи 45°"),
        ("Тяга одной рукой в блочном тренажёре", 4, 12, 15, None),
        ("Тяга верхнего блока узким обратным хватом", 4, 12, 15, None),
        ("Тяга нижнего блока к поясу", 4, 8, 12, "Средний параллельный хват"),
        ("Пуловер на блоке с рогами", 4, 12, 15, None),
        ("Сгибания в тренажёре Скотта", 4, 12, 15,
         "Суперсет со следующим упражнением"),
        ("Сгибания на нижнем блоке", 4, 12, 15,
         "Суперсет с предыдущим упражнением, стоя в кроссовере"),
        CARDIO,
    ]),
    ("Грудь, дельты, трицепс", [
        ("Жим в Хаммере на верх груди", 4, 8, 12, None),
        ("Сведение рук в кроссовере", 4, 12, 14, "Сведение книзу"),
        ("Жим в Хаммере на плечи", 4, 10, 12, "На переднюю дельту"),
        ("Махи гантелями в стороны", 4, 15, 20, None),
        ("Обратная бабочка", 4, 15, None, "На заднюю дельту"),
        ("Жим в тренажёре на трицепс", 4, 12, 15,
         "Суперсет со следующим упражнением"),
        ("Разгибания с канатом на блоке", 4, 12, 15,
         "Суперсет с предыдущим упражнением"),
        CARDIO,
    ]),
    ("Ноги", [
        ("Разгибания ног в тренажёре", 4, 15, 20, None),
        ("Гак-присед", 4, 8, 12, None),
        ("Жим ногами одной ногой", 4, 12, 15, None),
        ("Сгибания ног в тренажёре сидя", 4, 12, 15, None),
        ("Отведение бедра в тренажёре сидя", 4, 12, 15, None),
        ("Подъёмы на носки стоя", 4, 20, None,
         "Можно в суперсете с первым или предпоследним упражнением"),
        CARDIO,
    ]),
]


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Диапазон повторов
    op.add_column(
        "program_exercises",
        sa.Column("target_reps_max", sa.Integer(), nullable=True),
    )

    # 2. Программа может быть без владельца — это шаблон
    op.alter_column(
        "programs",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 3. Новые упражнения (если общего с таким названием ещё нет)
    def shared_exercise_ids() -> dict[str, int]:
        rows = connection.execute(
            sa.text(
                "SELECT id, name FROM exercises "
                "WHERE created_by_user_id IS NULL"
            )
        )
        return {name: exercise_id for exercise_id, name in rows}

    existing = {name.lower() for name in shared_exercise_ids()}

    for name, muscle_group, equipment, description in NEW_EXERCISES:
        if name.lower() in existing:
            continue

        connection.execute(
            sa.text(
                "INSERT INTO exercises "
                "(name, muscle_group, equipment, description, created_by_user_id) "
                "VALUES (:name, :muscle_group, :equipment, :description, NULL)"
            ),
            {
                "name": name,
                "muscle_group": muscle_group,
                "equipment": equipment,
                "description": description,
            },
        )

    # 4. Шаблон программы (если ещё не создан)
    already = connection.execute(
        sa.text(
            "SELECT 1 FROM programs WHERE user_id IS NULL AND name = :name"
        ),
        {"name": TEMPLATE_NAME},
    ).scalar()

    if already:
        return

    exercise_ids = shared_exercise_ids()

    program_id = connection.execute(
        sa.text(
            "INSERT INTO programs (user_id, name, description) "
            "VALUES (NULL, :name, :description) RETURNING id"
        ),
        {"name": TEMPLATE_NAME, "description": TEMPLATE_DESCRIPTION},
    ).scalar_one()

    for day_index, (day_name, items) in enumerate(TEMPLATE_DAYS, start=1):
        day_id = connection.execute(
            sa.text(
                "INSERT INTO program_days (program_id, name, order_index) "
                "VALUES (:program_id, :name, :order_index) RETURNING id"
            ),
            {"program_id": program_id, "name": day_name, "order_index": day_index},
        ).scalar_one()

        for item_index, (name, sets, reps, reps_max, notes) in enumerate(items, start=1):
            if name not in exercise_ids:
                raise RuntimeError(f"Общее упражнение «{name}» не найдено")

            connection.execute(
                sa.text(
                    "INSERT INTO program_exercises "
                    "(program_day_id, exercise_id, order_index, sets, "
                    " target_reps, target_reps_max, notes) "
                    "VALUES (:day_id, :exercise_id, :order_index, :sets, "
                    " :reps, :reps_max, :notes)"
                ),
                {
                    "day_id": day_id,
                    "exercise_id": exercise_ids[name],
                    "order_index": item_index,
                    "sets": sets,
                    "reps": reps,
                    "reps_max": reps_max,
                    "notes": notes,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()

    # Шаблоны без владельца невозможны в старой схеме — удаляем их
    connection.execute(sa.text("DELETE FROM programs WHERE user_id IS NULL"))

    op.alter_column(
        "programs",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    connection.execute(
        sa.text(
            """
            DELETE FROM exercises
            WHERE created_by_user_id IS NULL
              AND name = ANY(:names)
              AND NOT EXISTS (
                  SELECT 1 FROM program_exercises
                  WHERE program_exercises.exercise_id = exercises.id
              )
            """
        ),
        {"names": [name for name, *_ in NEW_EXERCISES]},
    )

    op.drop_column("program_exercises", "target_reps_max")
