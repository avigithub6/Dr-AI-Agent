from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import ClinicalUser
from app.database.session import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService
from app.utils.logger import logger


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


def get_conversation_service(
    db: Annotated[Session, Depends(get_db)],
) -> ConversationService:
    return ConversationService(db)


ConversationServiceDependency = Annotated[
    ConversationService,
    Depends(get_conversation_service),
]


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    service: ConversationServiceDependency,
    current_user: ClinicalUser,
):
    logger.info(
        "Chat request received | message_length=%d",
        len(request.message),
    )

    response = service.send_message(
        patient_id=request.patient_id,
        session_id=request.session_id,
        message=request.message,
        owner_user_id=current_user.id,
    )

    return ChatResponse(
        session_id=request.session_id,
        response=response,
    )