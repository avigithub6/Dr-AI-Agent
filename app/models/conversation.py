from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    session_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class PatientHistoryResponse(BaseModel):
    patient_id: UUID
    items: list[ConversationSummary]
    total: int
    offset: int
    limit: int


class ConversationDetailResponse(BaseModel):
    patient_id: UUID
    session_id: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse]
    total: int
    offset: int
    limit: int


class ConversationDeleteResponse(BaseModel):
    detail: str