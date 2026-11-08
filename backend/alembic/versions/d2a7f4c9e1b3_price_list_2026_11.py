"""price list: personal trainings (single, 5, 10) and online coaching

Revision ID: d2a7f4c9e1b3
Revises: c7f2e9a4d1b6
Create Date: 2026-11-09 01:10:00.000000

Новый прайс на главной. Прежние тарифы скрываются (is_active = false),
а не удаляются: на них могут ссылаться старые заявки. Потом цены и
тексты можно править в админ-панели, таблица «Тарифы на главной».
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2a7f4c9e1b3"
down_revision: Union[str, Sequence[str], None] = "c7f2e9a4d1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERSONAL = (
    "Техника каждого упражнения\n"
    "Подбор весов под вас\n"
    "План и результаты — в приложении"
)

PRICES = [
    {
        "title": "Разовая тренировка",
        "kind": "offline",
        "subtitle": "Личная тренировка в зале, один на один с тренером",
        "price": 2199,
        "price_unit": "за тренировку",
        "features": PERSONAL,
        "is_featured": False,
        "is_active": True,
        "order_index": 1,
    },
    {
        "title": "Блок из 5 тренировок",
        "kind": "offline",
        "subtitle": "Личные тренировки · 1 998 ₽ за занятие",
        "price": 9990,
        "price_unit": "за 5 тренировок",
        "features": "Выгода 1 005 ₽ к разовым\n" + PERSONAL,
        "is_featured": False,
        "is_active": True,
        "order_index": 2,
    },
    {
        "title": "Блок из 10 тренировок",
        "kind": "offline",
        "subtitle": "Личные тренировки · 1 929 ₽ за занятие",
        "price": 19290,
        "price_unit": "за 10 тренировок",
        "features": "Выгода 2 700 ₽ к разовым\n" + PERSONAL,
        "is_featured": False,
        "is_active": True,
        "order_index": 3,
    },
    {
        "title": "Онлайн-ведение",
        "kind": "online",
        "subtitle": "Тренер рядом, где бы вы ни тренировались",
        "price": 7000,
        "price_unit": "в месяц",
        "features": (
            "Программа под вашу цель и инвентарь\n"
            "Тренер видит каждый подход и вес\n"
            "Комментарии и корректировки каждую неделю\n"
            "Норма КБЖУ и контроль питания\n"
            "Связь с тренером в мессенджере"
        ),
        "is_featured": True,
        "is_active": True,
        "order_index": 4,
    },
]

TITLES = [item["title"] for item in PRICES]


def upgrade() -> None:
    offers = sa.table(
        "offers",
        sa.column("title", sa.String),
        sa.column("kind", sa.String),
        sa.column("subtitle", sa.String),
        sa.column("price", sa.Integer),
        sa.column("price_unit", sa.String),
        sa.column("features", sa.Text),
        sa.column("is_featured", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("order_index", sa.Integer),
    )

    # прежние тарифы — скрыть
    op.execute("UPDATE offers SET is_active = false")
    op.bulk_insert(offers, PRICES)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM offers WHERE title IN :titles AND created_at >= '2026-11-09'")
        .bindparams(sa.bindparam("titles", expanding=True)),
        {"titles": TITLES},
    )
    op.execute("UPDATE offers SET is_active = true")
