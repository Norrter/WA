"""offers and leads: tariffs on the landing page and requests from visitors

Revision ID: b3e8c1f5a7d2
Revises: a9d4f7c2e6b1
Create Date: 2026-10-22 23:40:00.000000

Тарифы для главной страницы (с примерами — их правят в админ-панели)
и заявки от посетителей. Существующие данные не меняются.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3e8c1f5a7d2"
down_revision: Union[str, Sequence[str], None] = "a9d4f7c2e6b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EXAMPLES = [
    {
        "title": "Персональная тренировка",
        "kind": "offline",
        "subtitle": "В зале, один на один с тренером",
        "price": 2000,
        "price_unit": "за тренировку",
        "features": "Техника каждого упражнения\nПодбор весов под вас\nПлан и результаты — в приложении",
        "is_featured": False,
        "order_index": 1,
    },
    {
        "title": "Онлайн-ведение",
        "kind": "online",
        "subtitle": "Тренер рядом, где бы вы ни тренировались",
        "price": 5000,
        "price_unit": "в месяц",
        "features": (
            "Программа под вашу цель и инвентарь\n"
            "Тренер видит каждый подход и вес\n"
            "Комментарии и корректировки каждую неделю\n"
            "Норма КБЖУ и контроль питания\n"
            "Связь с тренером в мессенджере"
        ),
        "is_featured": True,
        "order_index": 2,
    },
    {
        "title": "Программа тренировок",
        "kind": "program",
        "subtitle": "Готовый план на 8 недель",
        "price": 2500,
        "price_unit": "разово",
        "features": "Программа под цель: сила, масса или рельеф\nРасписание и прогресс в приложении\nОдна консультация по технике",
        "is_featured": False,
        "order_index": 3,
    },
]


def upgrade() -> None:
    offers = op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("subtitle", sa.String(200), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("price_unit", sa.String(40), nullable=True),
        sa.Column("features", sa.Text(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price >= 0", name="ck_offers_price"),
        sa.CheckConstraint("kind IN ('offline', 'online', 'program')", name="ck_offers_kind"),
    )

    op.bulk_insert(offers, EXAMPLES)

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "offer_id",
            sa.Integer(),
            sa.ForeignKey("offers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("offer_title", sa.String(120), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("contact", sa.String(150), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('new', 'in_progress', 'done', 'rejected')",
            name="ck_leads_status",
        ),
    )
    op.create_index("ix_leads_offer_id", "leads", ["offer_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_offer_id", table_name="leads")
    op.drop_table("leads")
    op.drop_table("offers")
