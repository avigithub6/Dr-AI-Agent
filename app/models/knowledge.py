from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=3,
        max_length=1000,
        strict=True,
    )

    limit: int = Field(
        default=4,
        ge=1,
        le=10,
    )


class KnowledgeSource(BaseModel):
    document_id: UUID
    source_name: str
    page_number: int | None
    chunk_index: int
    score: float
    text: str


class KnowledgeSearchResponse(BaseModel):
    question: str
    sources: list[KnowledgeSource]


class KnowledgeDocumentResponse(BaseModel):
    document_id: UUID
    source_name: str
    source_sha256: str
    chunks_indexed: int


class KnowledgeDeleteResponse(BaseModel):
    detail: str