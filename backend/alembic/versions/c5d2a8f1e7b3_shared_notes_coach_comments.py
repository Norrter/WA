"""shared coach notes and coach comments on workouts

Revision ID: c5d2a8f1e7b3
Revises: b8e1f4c6d2a7
Create Date: 2026-10-13 20:00:00.000000

1. coach_notes.shared — заметка видна клиенту. У существующих
   заметок false: они остаются личными.
2. scheduled_workouts.coach_comment, coach_comment_at,
   coach_comment_by — комментарий тренера к тренировке клиента.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5d2a8f1e7b3"
down_revision: Union[str, Sequence[str], None] = "b8e1f4c6d2a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "coach_notes",
        sa.Column("shared", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    op.add_column(
        "scheduled_workouts",
        sa.Column("coach_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "scheduled_workouts",
        sa.Column("coach_comment_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scheduled_workouts",
        sa.Column("coach_comment_by", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_scheduled_workouts_coach_comment_by_users",
        "scheduled_workouts",
        "users",
        ["coach_comment_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_scheduled_workouts_coach_comment_by_users",
        "scheduled_workouts",
        type_="foreignkey",
    )
    op.drop_column("scheduled_workouts", "coach_comment_by")
    op.drop_column("scheduled_workouts", "coach_comment_at")
    op.drop_column("scheduled_workouts", "coach_comment")
    op.drop_column("coach_notes", "shared")
