"""Тренер глазами клиента.

Тренер сам добавляет клиента по email, подтверждать не нужно.

У клиента не больше одного активного тренера. Завершить
сотрудничество может любая сторона; история тренировок остаётся
у клиента.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.coaching import CoachClient, CoachingStatus
from app.models.user import User
from app.schemas.coach import CoachingState


router = APIRouter(prefix="/coaching", tags=["Coaching"])


def person(user: User) -> dict:
    return {"id": user.id, "username": user.username, "email": user.email}


async def coaching_state(session: AsyncSession, user: User) -> dict:
    row = (
        await session.execute(
            select(CoachClient, User)
            .join(User, User.id == CoachClient.coach_id)
            .where(
                CoachClient.client_id == user.id,
                CoachClient.status == CoachingStatus.active.value,
            )
        )
    ).first()

    if row is None:
        return {"coach": None}

    link, coach_user = row

    return {
        "coach": {
            "id": link.id,
            "coach": person(coach_user),
            "since": link.responded_at,
        }
    }


@router.get("", response_model=CoachingState)
async def get_coaching(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Текущий тренер (или null)."""
    return await coaching_state(session, current_user)


@router.post("/end", response_model=CoachingState)
async def end_cooperation(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Завершить сотрудничество с текущим тренером."""
    link = await session.scalar(
        select(CoachClient).where(
            CoachClient.client_id == current_user.id,
            CoachClient.status == CoachingStatus.active.value,
        )
    )

    if link is None:
        raise HTTPException(status_code=404, detail="You have no coach")

    link.status = CoachingStatus.ended.value
    link.ended_at = datetime.now(timezone.utc)
    await session.commit()

    return await coaching_state(session, current_user)
