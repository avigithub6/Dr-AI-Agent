from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    __table_args__ = (
        Index(
            "ix_conversations_patient_updated_at",
            "patient_id",
            "updated_at",
        ),
    )

    session_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    patient_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "patients.id",
            ondelete="CASCADE",
            name="fk_conversations_patient_id_patients",
        ),
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

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    owner_user_id: Mapped[UUID] = mapped_column(
    Uuid(as_uuid=True),
    ForeignKey("users.id", ondelete="RESTRICT"),
    nullable=False,
    index=True,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="role_values",
        ),
        CheckConstraint(
            "char_length(trim(content)) > 0",
            name="content_not_blank",
        ),
        Index(
            "ix_chat_messages_session_created_at_id",
            "session_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    session_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey(
            "conversations.session_id",
            ondelete="CASCADE",
            name="fk_chat_messages_session_id_conversations",
        ),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
    )