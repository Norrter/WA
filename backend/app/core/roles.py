"""Роли пользователей.

Кто тренер, решает переменная COACH_EMAILS: роль выставляется при
регистрации, при смене email и при каждом запуске сервера. Чтобы
сделать человека тренером или снять роль, достаточно поменять список
и перезапустить сервер.
"""

from sqlalchemy import case, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, UserRole


def role_for_email(email: str) -> str:
    if email.strip().lower() in settings.coach_emails:
        return UserRole.coach.value

    return UserRole.user.value


async def sync_coach_roles(session: AsyncSession) -> None:
    """Привести роли всех пользователей в соответствие с COACH_EMAILS."""
    new_role = case(
        (
            func.lower(User.email).in_(settings.coach_emails),
            UserRole.coach.value,
        ),
        else_=UserRole.user.value,
    )

    await session.execute(
        update(User)
        .where(User.role != new_role)
        .values(role=new_role)
    )
    await session.commit()
