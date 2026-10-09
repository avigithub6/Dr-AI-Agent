from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    language_probability: float | None = None


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)