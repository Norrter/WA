"""email verification: when the user confirmed their email

Revision ID: c7f2e9a4d1b6
Revises: b3e8c1f5a7d2
Create Date: 2026-11-05 07:00:00.000000

Новое поле users.email_verified_at. Тем, кто зарегистрировался раньше,
почта считается подтверждённой — им не придёт напоминание.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f2e9a4d1b6"
down_revision: Union[str, Sequence[str], None] = "b3e8c1f5a7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE users SET email_verified_at = now()")


def downgrade() -> None:
    op.drop_column("users", "email_verified_at")
