from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from app.models.voice import SpeechRequest, TranscriptionResponse
from app.services.voice_service import (
    InvalidAudioError,
    VoiceModelUnavailableError,
    synthesize_speech,
    transcribe_audio,
)


router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)

MAX_AUDIO_BYTES = 15 * 1024 * 1024

ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "application/octet-stream",
}


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
)
async def transcribe(
    file: UploadFile = File(...),
    language: str | None = Query(
        default=None,
        min_length=2,
        max_length=10,
        description="Optional language code, for example en or hi.",
    ),
):
    suffix = Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "").lower()

    if suffix not in {
        ".wav",
        ".mp3",
        ".m4a",
        ".mp4",
        ".webm",
        ".ogg",
        ".flac",
        ".mpeg",
    }:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio file extension.",
        )

    if content_type and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio content type.",
        )

    try:
        audio_bytes = await file.read(MAX_AUDIO_BYTES + 1)
    finally:
        await file.close()

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio upload cannot exceed 15 MB.",
        )

    try:
        result = await run_in_threadpool(
            transcribe_audio,
            audio_bytes,
            suffix,
            language,
        )
        return TranscriptionResponse(**result)
    except InvalidAudioError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VoiceModelUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.post("/speak")
async def speak(request: SpeechRequest):
    try:
        audio_bytes = await run_in_threadpool(
            synthesize_speech,
            request.text,
        )
    except VoiceModelUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'inline; filename="dr-ai-response.wav"',
            "Cache-Control": "no-store",
        },
    )