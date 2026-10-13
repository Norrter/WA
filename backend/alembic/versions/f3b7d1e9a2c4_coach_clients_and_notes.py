"""coach clients and notes

Revision ID: f3b7d1e9a2c4
Revises: e5a2c8d1f4b6
Create Date: 2026-10-13 16:30:00.000000

Тренер видит только своих клиентов:
1. coach_clients — приглашение и связь тренер–клиент со статусом
   invited / active / declined / ended. У клиента не больше одного
   активного тренера.
2. coach_notes — заметки тренера о клиенте.

Только новые таблицы: существующие данные не меняются.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b7d1e9a2c4"
down_revision: Union[str, Sequence[str], None] = "e5a2c8d1f4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coach_clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("invited_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'declined', 'ended')",
            name="ck_coach_clients_status",
        ),
    )
    op.create_index("ix_coach_clients_coach_id", "coach_clients", ["coach_id"])
    op.create_index("ix_coach_clients_client_id", "coach_clients", ["client_id"])
    op.create_index(
        "uq_coach_clients_one_active_coach",
        "coach_clients",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "uq_coach_clients_one_pending_invite",
        "coach_clients",
        ["coach_id", sa.text("lower(invited_email)")],
        unique=True,
        postgresql_where=sa.text("status = 'invited'"),
    )

    op.create_table(
        "coach_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_coach_notes_coach_client",
        "coach_notes",
        ["coach_id", "client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_notes_coach_client", table_name="coach_notes")
    op.drop_table("coach_notes")
    op.drop_index("uq_coach_clients_one_pending_invite", table_name="coach_clients")
    op.drop_index("uq_coach_clients_one_active_coach", table_name="coach_clients")
    op.drop_index("ix_coach_clients_client_id", table_name="coach_clients")
    op.drop_index("ix_coach_clients_coach_id", table_name="coach_clients")
    op.drop_table("coach_clients")
