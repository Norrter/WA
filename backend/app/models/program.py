from datetime import datetime

from sqlalchemy import DateTime, String, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    days: Mapped[list["ProgramDay"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramDay.order_index",
    )

    user: Mapped["User"] = relationship(
        back_populates="programs",
    )

    scheduled_workouts: Mapped[list["ScheduledWorkout"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
    )