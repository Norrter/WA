"""Продажи: тарифы на главной странице и заявки от посетителей."""

import datetime as dt

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

LEAD_STATUSES = ("new", "in_progress", "done", "rejected")


class Offer(Base):
    """Тариф: персональные тренировки, онлайн-ведение и т. п.
    Редактируется в админ-панели."""

    __tablename__ = "offers"

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_offers_price"),
        CheckConstraint("kind IN ('offline', 'online', 'program')", name="ck_offers_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    # offline — в зале, online — онлайн-ведение, program — готовая программа
    kind: Mapped[str] = mapped_column(String(20), default="online")
    subtitle: Mapped[str | None] = mapped_column(String(200))
    # цена в рублях; 0 — «по договорённости»
    price: Mapped[int] = mapped_column(Integer)
    # «за тренировку», «в месяц»
    price_unit: Mapped[str | None] = mapped_column(String(40))
    # что входит — по строке на пункт
    features: Mapped[str | None] = mapped_column(Text)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    order_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Lead(Base):
    """Заявка с главной страницы. Тренер связывается с человеком сам."""

    __tablename__ = "leads"

    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'in_progress', 'done', 'rejected')",
            name="ck_leads_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("offers.id", ondelete="SET NULL"), index=True
    )
    # название тарифа на момент заявки — если тариф потом изменят или удалят
    offer_title: Mapped[str | None] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(150))
    goal: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new", index=True)
    # заметка тренера по заявке
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
