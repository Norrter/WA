from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Exercise(Base):
    __tablename__ = "exercises"

    __table_args__ = (
        CheckConstraint(
            "load_type IN ('external', 'bodyweight', 'assisted')",
            name="ck_exercises_load_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # Кто создал упражнение. NULL = общее упражнение из справочника:
    # его видят все, но менять и удалять через API нельзя.
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    muscle_group: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    equipment: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Как считать нагрузку: вес снаряда, свой вес + доп. вес или свой вес
    # с облегчением (гравитрон). Подробнее — app/core/load.py
    load_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="external",
        server_default="external",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    program_exercises: Mapped[list["ProgramExercise"]] = relationship(
        back_populates="exercise",
    )
