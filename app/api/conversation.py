from app.core.security import ClinicalUser
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.conversation_service import ConversationService


router = APIRouter(
    prefix="/patients",
    tags=["Patient Conversation History"],
)


def get_conversation_service(
    db: Annotated[Session, Depends(get_db)],
) -> ConversationService:
    return ConversationService(db)


ConversationServiceDependency = Annotated[
    ConversationService,
    Depends(get_conversation_service),
]


@router.get("/{patient_id}/history")
def list_patient_history(
    patient_id: UUID,
    service: ConversationServiceDependency,
    current_user: ClinicalUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return service.list_patient_history(
        patient_id=patient_id,
        owner_user_id=current_user.id,
        offset=offset,
        limit=limit,
    )


@router.get("/{patient_id}/history/{session_id}")
def get_conversation_history(
    patient_id: UUID,
    session_id: str,
    service: ConversationServiceDependency,
    current_user: ClinicalUser,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    return service.get_conversation_history(
        patient_id=patient_id,
        session_id=session_id,
        owner_user_id=current_user.id,
        offset=offset,
        limit=limit,
    )


@router.delete(
    "/{patient_id}/history/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    patient_id: UUID,
    session_id: str,
    service: ConversationServiceDependency,
    current_user: ClinicalUser,
):
    service.delete_conversation(
        patient_id=patient_id,
        session_id=session_id,
        owner_user_id=current_user.id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)