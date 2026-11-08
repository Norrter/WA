"""Вес тела: журнал по дням для графика на экране «Прогресс»."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.body_weight import BodyWeightEntry
from app.models.user import User
from app.schemas.body_weight import BodyWeightEntryResponse, BodyWeightInput
from app.services.body_weight import record, sync_current


router = APIRouter(prefix="/body-weight", tags=["Body weight"])


async def body_weight_list(
    session: AsyncSession,
    user_id: int,
    date_from: date | None,
    date_to: date | None,
) -> list[BodyWeightEntry]:
    query = select(BodyWeightEntry).where(BodyWeightEntry.user_id == user_id)

    if date_from is not None:
        query = query.where(BodyWeightEntry.date >= date_from)

    if date_to is not None:
        query = query.where(BodyWeightEntry.date <= date_to)

    return list((await session.scalars(query.order_by(BodyWeightEntry.date))).all())


@router.get("", response_model=list[BodyWeightEntryResponse])
async def list_entries(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Записи веса от старых к новым."""
    return await body_weight_list(session, current_user.id, date_from, date_to)


@router.post(
    "",
    response_model=BodyWeightEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_entry(
    data: BodyWeightInput,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Записать вес за день (по умолчанию за сегодня). Повторная запись
    за тот же день заменяет прежнюю. Вес в профиле — последняя запись."""
    day = data.date or date.today()

    if day > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date cannot be in the future",
        )

    entry = await record(session, current_user, day, data.weight)
    await session.commit()
    await session.refresh(entry)

    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    entry = await session.get(BodyWeightEntry, entry_id)

    if entry is None or entry.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Entry not found")

    await session.delete(entry)
    await session.flush()
    await sync_current(session, current_user)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
