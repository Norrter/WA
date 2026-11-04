"""Главная страница для гостей: тарифы и заявки.

Публичные запросы (без входа): список тарифов и отправка заявки.
Заявки видят и обрабатывают тренер и администратор.
"""

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_session
from app.models.sales import Lead, Offer
from app.models.user import User, UserRole
from app.schemas.sales import (
    LeadCreated,
    LeadInput,
    LeadPatch,
    LeadResponse,
    LeadStatus,
    OfferResponse,
)


public_router = APIRouter(prefix="/public", tags=["Public"])
router = APIRouter(prefix="/leads", tags=["Leads"])


# Не больше LEADS_PER_WINDOW заявок с одного адреса за LEADS_WINDOW секунд
LEADS_PER_WINDOW = 5
LEADS_WINDOW = 600
_recent: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    # Render и другие хостинги передают адрес посетителя в X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate(ip: str) -> None:
    now = time.monotonic()
    hits = _recent[ip]

    while hits and now - hits[0] > LEADS_WINDOW:
        hits.popleft()

    if len(hits) >= LEADS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, try again later",
        )

    hits.append(now)


def describe_offer(offer: Offer) -> dict:
    return {
        "id": offer.id,
        "title": offer.title,
        "kind": offer.kind,
        "subtitle": offer.subtitle,
        "price": offer.price,
        "price_unit": offer.price_unit,
        "features": [line.strip() for line in (offer.features or "").splitlines() if line.strip()],
        "is_featured": offer.is_featured,
    }


@public_router.get("/offers", response_model=list[OfferResponse])
async def list_offers(session: AsyncSession = Depends(get_session)):
    """Тарифы для главной страницы."""
    offers = (
        await session.scalars(
            select(Offer).where(Offer.is_active.is_(True)).order_by(Offer.order_index, Offer.id)
        )
    ).all()

    return [describe_offer(offer) for offer in offers]


@public_router.post("/leads", response_model=LeadCreated, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadInput,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Заявка с главной страницы. Вход не нужен."""
    # Бот заполнил скрытое поле — делаем вид, что всё хорошо
    if data.website:
        return {"id": 0}

    check_rate(client_ip(request))

    offer = None
    if data.offer_id is not None:
        offer = await session.get(Offer, data.offer_id)
        if offer is None or not offer.is_active:
            raise HTTPException(status_code=404, detail="Offer not found")

    lead = Lead(
        offer_id=offer.id if offer else None,
        offer_title=offer.title if offer else None,
        name=data.name,
        contact=data.contact,
        goal=data.goal or None,
    )
    session.add(lead)
    await session.commit()

    return {"id": lead.id}


# ----- Заявки для тренера и администратора -----


async def get_lead_manager(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.coach.value and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coach access required",
        )

    return current_user


async def get_lead(session: AsyncSession, lead_id: int) -> Lead:
    lead = await session.get(Lead, lead_id)

    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    lead_status: LeadStatus | None = Query(None, alias="status"),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_lead_manager),
):
    """Заявки, новые сверху."""
    query = select(Lead)

    if lead_status:
        query = query.where(Lead.status == lead_status)

    return (await session.scalars(query.order_by(Lead.created_at.desc(), Lead.id.desc()))).all()


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    data: LeadPatch,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_lead_manager),
):
    lead = await get_lead(session, lead_id)
    changes = data.model_dump(exclude_unset=True)

    if changes.get("status") is not None:
        lead.status = changes["status"]

    if "note" in changes:
        lead.note = changes["note"] or None

    await session.commit()
    await session.refresh(lead)

    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_lead_manager),
):
    lead = await get_lead(session, lead_id)
    await session.delete(lead)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
