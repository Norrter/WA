"""Журнал веса тела. Текущий вес в профиле — последняя запись журнала."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.body_weight import BodyWeightEntry
from app.models.user import User
from app.services.loads import fill_body_weight


async def sync_current(session: AsyncSession, user: User) -> None:
    """Вес в профиле = самая поздняя запись журнала."""
    latest = await session.scalar(
        select(BodyWeightEntry)
        .where(BodyWeightEntry.user_id == user.id)
        .order_by(BodyWeightEntry.date.desc(), BodyWeightEntry.id.desc())
        .limit(1)
    )

    user.body_weight = latest.weight if latest else None
    await session.flush()
    await fill_body_weight(session, user)


async def record(
    session: AsyncSession,
    user: User,
    day: date,
    weight: float,
) -> BodyWeightEntry:
    """Записать вес за день: одна запись в день, повторная заменяет."""
    entry = await session.scalar(
        select(BodyWeightEntry).where(
            BodyWeightEntry.user_id == user.id,
            BodyWeightEntry.date == day,
        )
    )

    if entry is None:
        entry = BodyWeightEntry(user_id=user.id, date=day, weight=weight)
        session.add(entry)
    else:
        entry.weight = weight

    await session.flush()
    await sync_current(session, user)

    return entry
