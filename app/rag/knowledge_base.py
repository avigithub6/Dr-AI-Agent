import hashlib
import re
from io import BytesIO
from uuid import NAMESPACE_URL, uuid5

import ollama
from pypdf import PdfReader
from qdrant_client import QdrantClient, models

from app.config import settings


MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 200
CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250
EMBED_BATCH_SIZE = 32
UPSERT_BATCH_SIZE = 64


class KnowledgeBaseService:
    def __init__(self):
        self.ollama_client = ollama.Client(
            host=settings.OLLAMA_BASE_URL,
        )

        api_key = (
            settings.QDRANT_API_KEY.get_secret_value()
            if settings.QDRANT_API_KEY
            else None
        )

        self.qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=api_key,
            timeout=30,
        )

        self.collection_name = settings.QDRANT_COLLECTION
        self.embedding_model = settings.OLLAMA_EMBEDDING_MODEL

    @staticmethod
    def _split_text(text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))

            if end < len(text):
                boundary = text.rfind(" ", start, end)
                if boundary > start + CHUNK_SIZE // 2:
                    end = boundary

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(text):
                break

            start = max(end - CHUNK_OVERLAP, start + 1)

        return chunks

    @classmethod
    def _extract_pages(
        cls,
        filename: str,
        content: bytes,
    ) -> list[tuple[int | None, str]]:
        extension = filename.lower().rsplit(".", 1)[-1]

        if extension == "txt":
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    "TXT file must use UTF-8 encoding."
                ) from exc

            return [(None, text)]

        if extension != "pdf":
            raise ValueError("Only PDF and TXT files are supported.")

        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:
            raise ValueError("The PDF file could not be read.") from exc

        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")

        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF cannot contain more than {MAX_PDF_PAGES} pages."
            )

        pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                raise ValueError(
                    f"Text could not be extracted from PDF page "
                    f"{page_number}."
                ) from exc

            if page_text.strip():
                pages.append((page_number, page_text))

        return pages

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self.ollama_client.embed(
            model=self.embedding_model,
            input=texts,
        )

        vectors = response.embeddings

        if len(vectors) != len(texts):
            raise RuntimeError(
                "Embedding model returned an unexpected number of vectors."
            )

        return vectors

    def _ensure_collection(self, vector_size: int) -> None:
        if not self.qdrant_client.collection_exists(
            self.collection_name
        ):
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

            self.qdrant_client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

            return

        collection = self.qdrant_client.get_collection(
            self.collection_name
        )
        vector_config = collection.config.params.vectors

        if isinstance(vector_config, dict):
            vector_config = vector_config.get("")

        stored_size = getattr(vector_config, "size", None)

        if stored_size != vector_size:
            raise RuntimeError(
                "Qdrant collection embedding size does not match the "
                "configured embedding model. Recreate the collection "
                "and re-index its documents after changing models."
            )

    def index_document(
        self,
        filename: str,
        content: bytes,
    ) -> dict:
        if not filename:
            raise ValueError("A filename is required.")

        if not content:
            raise ValueError("The uploaded file is empty.")

        if len(content) > MAX_FILE_BYTES:
            raise ValueError("File size cannot exceed 10 MB.")

        safe_filename = filename.replace("\\", "/").split("/")[-1]
        source_hash = hashlib.sha256(content).hexdigest()
        document_id = str(
            uuid5(NAMESPACE_URL, f"dr-ai-document:{source_hash}")
        )

        pages = self._extract_pages(safe_filename, content)
        chunks = []

        for page_number, page_text in pages:
            for chunk in self._split_text(page_text):
                chunks.append(
                    {
                        "text": chunk,
                        "page_number": page_number,
                    }
                )

        if not chunks:
            raise ValueError(
                "No readable text was found. Scanned PDFs need OCR "
                "before indexing."
            )

        vectors = []

        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[start:start + EMBED_BATCH_SIZE]
            vectors.extend(
                self._embed([item["text"] for item in batch])
            )

        if not vectors:
            raise RuntimeError("No embeddings were generated.")

        self._ensure_collection(len(vectors[0]))

        # Remove any old points for this exact document before re-indexing.
        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

        points = []

        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(
                uuid5(
                    NAMESPACE_URL,
                    f"dr-ai-chunk:{document_id}:{index}",
                )
            )

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "source_name": safe_filename,
                        "source_sha256": source_hash,
                        "chunk_index": index,
                        "page_number": chunk["page_number"],
                        "text": chunk["text"],
                    },
                )
            )

        for start in range(0, len(points), UPSERT_BATCH_SIZE):
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points[start:start + UPSERT_BATCH_SIZE],
                wait=True,
            )

        return {
            "document_id": document_id,
            "source_name": safe_filename,
            "source_sha256": source_hash,
            "chunks_indexed": len(points),
        }

    def search(self, question: str, limit: int) -> list[dict]:
        if not self.qdrant_client.collection_exists(
            self.collection_name
        ):
            return []

        question_vector = self._embed([question])[0]

        result = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=question_vector,
            limit=limit,
            with_payload=True,
        )

        sources = []

        for point in result.points:
            payload = point.payload or {}

            sources.append(
                {
                    "document_id": payload.get("document_id", ""),
                    "source_name": payload.get("source_name", ""),
                    "page_number": payload.get("page_number"),
                    "chunk_index": payload.get("chunk_index", 0),
                    "score": float(point.score or 0.0),
                    "text": payload.get("text", ""),
                }
            )

        return sources

    def delete_document(self, document_id: str) -> None:
        if not self.qdrant_client.collection_exists(
            self.collection_name
        ):
            return

        self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )


knowledge_base = KnowledgeBaseService()