"""add users and program ownership

Revision ID: 057eeb89e864
Revises: 0714e3c52b55
Create Date: 2026-09-26 19:14:07.442361

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "057eeb89e864"
down_revision: Union[str, Sequence[str], None] = "0714e3c52b55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Создаём таблицу пользователей
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )

    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
    )

    # 2. Добавляем user_id временно nullable,
    #    потому что в programs уже есть существующие записи
    op.add_column(
        "programs",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )

    # 3. Создаём временного пользователя для старых программ
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, username, password_hash)
            VALUES (
                'migration@example.com',
                'migration_user',
                'temporary-migration-password'
            )
            """
        )
    )

    # 4. Привязываем существующие программы
    op.execute(
        sa.text(
            """
            UPDATE programs
            SET user_id = (
                SELECT id
                FROM users
                WHERE username = 'migration_user'
            )
            WHERE user_id IS NULL
            """
        )
    )

    # 5. Теперь user_id можно сделать обязательным
    op.alter_column(
        "programs",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 6. Создаём именованный FK
    op.create_foreign_key(
        "fk_programs_user_id_users",
        "programs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Удаляем FK
    op.drop_constraint(
        "fk_programs_user_id_users",
        "programs",
        type_="foreignkey",
    )

    # Удаляем user_id
    op.drop_column("programs", "user_id")

    # Удаляем индексы
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")

    # Удаляем таблицу users
    op.drop_table("users")