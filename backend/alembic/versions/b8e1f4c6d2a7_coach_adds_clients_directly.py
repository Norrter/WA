"""coach adds clients directly, without acceptance

Revision ID: b8e1f4c6d2a7
Revises: a4c9e2f7b1d3
Create Date: 2026-10-13 19:30:00.000000

Тренер теперь сам назначает клиента, подтверждать не нужно.
Приглашения, на которые зарегистрированные люди ещё не ответили,
становятся активными: у клиента без тренера — самое раннее из них,
остальные закрываются как отклонённые. Приглашения на email, который
ещё не зарегистрирован, остаются ждать регистрации (одно на email).
Схема таблиц не меняется.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8e1f4c6d2a7"
down_revision: Union[str, Sequence[str], None] = "a4c9e2f7b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Самое раннее приглашение каждого зарегистрированного клиента
    # без активного тренера становится активным
    op.execute(
        """
        UPDATE coach_clients AS cc
        SET status = 'active',
            responded_at = now()
        FROM (
            SELECT DISTINCT ON (client_id) id
            FROM coach_clients
            WHERE status = 'invited'
              AND client_id IS NOT NULL
              AND client_id NOT IN (
                  SELECT client_id FROM coach_clients
                  WHERE status = 'active' AND client_id IS NOT NULL
              )
            ORDER BY client_id, created_at, id
        ) AS first_invite
        WHERE cc.id = first_invite.id
        """
    )

    # Остальные приглашения зарегистрированным людям закрываются
    op.execute(
        """
        UPDATE coach_clients
        SET status = 'declined',
            responded_at = now()
        WHERE status = 'invited' AND client_id IS NOT NULL
        """
    )

    # На незарегистрированный email ждёт регистрации только одно
    # приглашение — самое раннее
    op.execute(
        """
        UPDATE coach_clients
        SET status = 'declined',
            responded_at = now()
        WHERE status = 'invited'
          AND client_id IS NULL
          AND id NOT IN (
              SELECT DISTINCT ON (lower(invited_email)) id
              FROM coach_clients
              WHERE status = 'invited' AND client_id IS NULL
              ORDER BY lower(invited_email), created_at, id
          )
        """
    )


def downgrade() -> None:
    # Данные не возвращаются: принятые автоматически связи остаются
    pass
