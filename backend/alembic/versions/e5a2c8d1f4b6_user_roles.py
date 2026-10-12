"""user roles

Revision ID: e5a2c8d1f4b6
Revises: d9f3b6c2e4a8
Create Date: 2026-10-12 18:30:00.000000

Роль пользователя: user (обычный) или coach (тренер видит статистику
всех пользователей). Кто тренер — задаётся переменной COACH_EMAILS,
роли выставляются при запуске сервера.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5a2c8d1f4b6"
down_revision: Union[str, Sequence[str], None] = "d9f3b6c2e4a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('user', 'coach')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
