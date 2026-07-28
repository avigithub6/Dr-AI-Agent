from fastapi import APIRouter

from app.models.chat import ChatRequest, ChatResponse
from app.utils.logger import logger

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):

    logger.info("Chat request received | message_length=%d", len(request.message))

    return ChatResponse(
        response=f"You said: {request.message}"
    )