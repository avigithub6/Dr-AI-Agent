import hmac
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Header,
    HTTPException,
    UploadFile,
    status,
)

from app.config import settings
from app.models.knowledge import (
    KnowledgeDeleteResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.rag.knowledge_base import (
    MAX_FILE_BYTES,
    knowledge_base,
)
from app.utils.logger import logger


router = APIRouter(
    prefix="/knowledge",
    tags=["Medical Knowledge Base"],
)


def verify_admin_key(provided_key: str) -> None:
    expected_key = (
        settings.KNOWLEDGE_ADMIN_API_KEY.get_secret_value()
    )

    if not hmac.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid knowledge-base admin key.",
        )


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    admin_key: Annotated[
        str,
        Header(alias="X-Knowledge-Admin-Key"),
    ] = "",
):
    verify_admin_key(admin_key)

    try:
        content = await file.read(MAX_FILE_BYTES + 1)

        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size cannot exceed 10 MB.",
            )

        result = knowledge_base.index_document(
            filename=file.filename or "",
            content=content,
        )

        return KnowledgeDocumentResponse(**result)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Knowledge document indexing failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Knowledge indexing is unavailable. Check that Ollama "
                "and Qdrant are running and the embedding model is pulled."
            ),
        ) from exc

    finally:
        await file.close()


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
)
def search_knowledge(
    request: KnowledgeSearchRequest,
):
    try:
        sources = knowledge_base.search(
            question=request.question,
            limit=request.limit,
        )

        return KnowledgeSearchResponse(
            question=request.question,
            sources=sources,
        )

    except Exception as exc:
        logger.exception("Knowledge search failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Medical knowledge search is unavailable.",
        ) from exc


@router.delete(
    "/documents/{document_id}",
    response_model=KnowledgeDeleteResponse,
)
def delete_document(
    document_id: str,
    admin_key: Annotated[
        str,
        Header(alias="X-Knowledge-Admin-Key"),
    ] = "",
):
    verify_admin_key(admin_key)

    try:
        knowledge_base.delete_document(document_id)
    except Exception as exc:
        logger.exception(
            "Knowledge document deletion failed | document_id=%s",
            document_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge document deletion is unavailable.",
        ) from exc

    return KnowledgeDeleteResponse(
        detail="Knowledge document deleted.",
    )