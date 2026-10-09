from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    patient_id: UUID

    session_id: str = Field(
        min_length=3,
        max_length=100,
        strict=True,
    )

    message: str = Field(
        min_length=2,
        max_length=1000,
        strict=True,
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str