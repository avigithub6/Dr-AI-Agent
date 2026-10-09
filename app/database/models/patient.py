from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Patient(Base):
    __tablename__ = "patients"

    __table_args__ = (
        CheckConstraint(
            "age >= 0 AND age <= 130",
            name="age_range",
        ),
        CheckConstraint(
            "gender IN "
            "('male', 'female', 'other', 'prefer_not_to_say')",
            name="gender_values",
        ),
        CheckConstraint(
            "char_length(trim(full_name)) BETWEEN 2 AND 100",
            name="full_name_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    age: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    gender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )