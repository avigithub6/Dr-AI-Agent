import json
import logging
from typing import Annotated

from langchain_core.tools import tool
from pydantic import Field

from app.config import settings
from app.rag.knowledge_base import knowledge_base

logger = logging.getLogger("Dr AI Agent")

@tool
def search_medical_knowledge(
    question: Annotated[
        str,
        Field(
            description=(
                "A focused medical question to search in the "
                "approved medical knowledge base."
            ),
            min_length=3,
            max_length=1000,
        ),
    ],
) -> str:
    """Search approved medical documents and return source excerpts.

    Use this for medical facts that should be grounded in the indexed
    knowledge base. Do not use it to diagnose a patient or prescribe
    treatment.
    """
    sources = knowledge_base.search(
        question=question,
        limit=settings.RAG_TOP_K,
    )

    logger.info(
        "Medical RAG | Search completed | results=%d",
        len(sources),
    )

    if not sources:
        logger.warning(
            "Medical RAG | No relevant documents found"
        )
        return json.dumps(
            {
                "found": False,
                "message": (
                    "No relevant source was found in the medical "
                    "knowledge base."
                ),
                "sources": [],
            },
            ensure_ascii=False,
        )

    safe_sources = [
        {
            "source_name": source["source_name"],
            "page_number": source["page_number"],
            "score": source["score"],
            "excerpt": source["text"],
        }
        for source in sources
    ]

    return json.dumps(
        {
            "found": True,
            "sources": safe_sources,
        },
        ensure_ascii=False,
    )