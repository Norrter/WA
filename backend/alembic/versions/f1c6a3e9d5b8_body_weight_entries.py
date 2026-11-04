"""body weight entries: track body weight over time

Revision ID: f1c6a3e9d5b8
Revises: e8b4d2a6c9f1
Create Date: 2026-10-22 22:30:00.000000

Журнал веса тела: одна запись на человека в день. Если вес тела уже
указан в профиле, он становится первой записью (на сегодня).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1c6a3e9d5b8"
down_revision: Union[str, Sequence[str], None] = "e8b4d2a6c9f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "body_weight_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_body_weight_entries_user_date"),
        sa.CheckConstraint("weight BETWEEN 20 AND 400", name="ck_body_weight_entries_weight"),
    )
    op.create_index("ix_body_weight_entries_user_id", "body_weight_entries", ["user_id"])

    op.execute(
        """
        INSERT INTO body_weight_entries (user_id, date, weight)
        SELECT id, CURRENT_DATE, body_weight
        FROM users
        WHERE body_weight BETWEEN 20 AND 400
        """
    )


def downgrade() -> None:
    op.drop_index("ix_body_weight_entries_user_id", table_name="body_weight_entries")
    op.drop_table("body_weight_entries")
