from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
        message: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User medical query"
    )


class ChatResponse(BaseModel):
    response: str