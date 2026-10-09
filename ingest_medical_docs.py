
import hashlib
import json
import logging
from pathlib import Path

from app.rag.knowledge_base import knowledge_base

DOCS_DIR = Path(__file__).resolve().parent / "medical_docs"
STATE_FILE = Path("/app/data/medical_ingestion_state.json")
SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("medical_ingestion")


def file_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid ingestion state")
        return data
    except (OSError, ValueError) as exc:
        logger.warning("Cannot read ingestion state: %s", exc)
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATE_FILE)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    state = load_state()

    files = sorted(
        path
        for path in DOCS_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        logger.info("No medical documents found in %s", DOCS_DIR)
        return

    indexed = 0
    skipped = 0
    failed = 0

    for path in files:
        relative_path = path.relative_to(DOCS_DIR).as_posix()

        try:
            digest = file_sha256(path)

            if state.get(relative_path) == digest:
                logger.info("Skipping unchanged file: %s", relative_path)
                skipped += 1
                continue

            logger.info("Indexing: %s", relative_path)

            result = knowledge_base.index_document(
                filename=path.name,
                content=path.read_bytes(),
            )

            state[relative_path] = digest
            save_state(state)

            indexed += 1
            logger.info(
                "Indexed %s | chunks=%s",
                relative_path,
                result["chunks_indexed"],
            )

        except Exception:
            failed += 1
            logger.exception("Failed to index %s", relative_path)

    logger.info(
        "Finished | indexed=%d | skipped=%d | failed=%d",
        indexed,
        skipped,
        failed,
    )


if __name__ == "__main__":
    main()
