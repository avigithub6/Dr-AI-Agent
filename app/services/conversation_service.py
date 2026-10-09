from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.patient import Patient
from app.models.conversation import (
    ChatMessageResponse,
    ConversationDetailResponse,
    ConversationSummary,
    PatientHistoryResponse,
)
from app.repositories.conversation_repository import (
    ConversationRepository,
)
from app.repositories.patient_repository import PatientRepository
from app.services.llm_service import generate_response
from app.utils.logger import logger


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.conversation_repository = ConversationRepository(db)
        self.patient_repository = PatientRepository(db)

    def _require_patient(self, patient_id: UUID) -> Patient:
        patient = self.patient_repository.get_by_id(patient_id)

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found.",
            )

        return patient

    def send_message(
        self,
        patient_id: UUID,
        session_id: str,
        message: str,
        owner_user_id: UUID,
    ) -> str:
        self._require_patient(patient_id)

        conversation = self.conversation_repository.get_or_create(
            session_id=session_id,
            patient_id=patient_id,
            owner_user_id=owner_user_id,
        )

        # A session ID must not be reused for a different patient.
        if conversation.patient_id != patient_id:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        self.conversation_repository.add_message(
            session_id=session_id,
            role="user",
            content=message,
        )
        self.conversation_repository.touch(session_id)

        conversation_messages = (
            self.conversation_repository.get_recent_messages(
                session_id=session_id,
                limit=10,
            )
        )

        llm_messages = [
            {
                "role": item.role,
                "content": item.content,
            }
            for item in conversation_messages
        ]

        logger.info(
            "Conversation context | session_id=%s | count=%d | roles=%s",
            session_id,
            len(llm_messages),
            [item["role"] for item in llm_messages],
        )
        # Save the user's message before calling Ollama. If Ollama is
        # unavailable, the submitted message remains in the history.
        self.db.commit()

        try:
            answer = generate_response(llm_messages)
        except Exception as exc:
            logger.exception(
                "AI response generation failed | session_id=%s",
                session_id,
            )
            self.db.rollback()
            raise HTTPException(
                status_code=503,
                detail="The AI service is temporarily unavailable.",
            ) from exc

        try:
            self.conversation_repository.add_message(
                session_id=session_id,
                role="assistant",
                content=answer,
            )
            self.conversation_repository.touch(session_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return answer

    def list_patient_history(
        self,
        patient_id: UUID,
        owner_user_id: UUID,
        offset: int,
        limit: int,
    ) -> PatientHistoryResponse:
        self._require_patient(patient_id)

        conversations, total = (
            self.conversation_repository.list_patient_conversations(
                patient_id=patient_id,
                owner_user_id=owner_user_id,
                offset=offset,
                limit=limit,
            )
        )

        items = [
            ConversationSummary(
                session_id=conversation.session_id,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                message_count=message_count,
            )
            for conversation, message_count in conversations
        ]

        return PatientHistoryResponse(
            patient_id=patient_id,
            items=items,
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_conversation_history(
        self,
        patient_id: UUID,
        session_id: str,
        owner_user_id: UUID,
        offset: int,
        limit: int,
    ) -> ConversationDetailResponse:
        self._require_patient(patient_id)

        conversation = (
            self.conversation_repository.get_patient_conversation(
                patient_id=patient_id,
                session_id=session_id,
                owner_user_id=owner_user_id,
            )
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        messages, total = self.conversation_repository.list_messages(
            session_id=session_id,
            offset=offset,
            limit=limit,
        )

        return ConversationDetailResponse(
            patient_id=patient_id,
            session_id=session_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[
                ChatMessageResponse.model_validate(item)
                for item in messages
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    def delete_conversation(
        self,
        patient_id: UUID,
        session_id: str,
        owner_user_id: UUID,
    ) -> None:
        self._require_patient(patient_id)

        conversation = (
            self.conversation_repository.get_patient_conversation(
                patient_id=patient_id,
                session_id=session_id,
                owner_user_id=owner_user_id,
            )
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

        self.conversation_repository.delete_conversation(conversation)
        self.db.commit()