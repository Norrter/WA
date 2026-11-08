"""Записи веса тела: одна на человека в день."""

import datetime as dt

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BodyWeightEntry(Base):
    __tablename__ = "body_weight_entries"

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_body_weight_entries_user_date"),
        CheckConstraint("weight BETWEEN 20 AND 400", name="ck_body_weight_entries_weight"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
