"""personal data consent: when a user / a lead gave consent (152-FZ)

Revision ID: e4b9c2d7f6a1
Revises: d2a7f4c9e1b3
Create Date: 2026-11-12 23:50:00.000000

Время согласия на обработку персональных данных: у пользователя
(галочка при регистрации) и у заявки с главной. Нужно, чтобы оператор
мог подтвердить, что согласие получено. У старых записей — пусто.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4b9c2d7f6a1"
down_revision: Union[str, Sequence[str], None] = "d2a7f4c9e1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("pd_consent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("pd_consent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "pd_consent_at")
    op.drop_column("users", "pd_consent_at")
