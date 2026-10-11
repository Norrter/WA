from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProgramDay(Base):
    __tablename__ = "program_days"

    # DEFERRED: проверяется в конце транзакции, поэтому дни можно
    # переставлять местами одним запросом (см. /days/reorder)
    __table_args__ = (
        UniqueConstraint(
            "program_id",
            "order_index",
            name="uq_program_days_program_id_order_index",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    order_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    program: Mapped["Program"] = relationship(
        back_populates="days",
    )

    exercises: Mapped[list["ProgramExercise"]] = relationship(
        back_populates="program_day",
        cascade="all, delete-orphan",
        order_by="ProgramExercise.order_index",
    )

    scheduled_workouts: Mapped[list["ScheduledWorkout"]] = relationship(
        back_populates="program_day",
        cascade="all, delete-orphan",
    )
