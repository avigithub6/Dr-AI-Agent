import logging
import os
import tempfile
import threading
import wave
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel


logger = logging.getLogger("Dr AI Agent")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_whisper_lock = threading.Lock()
_piper_lock = threading.Lock()

_whisper_model_instance: WhisperModel | None = None
_piper_voice_instance: Any | None = None


class InvalidAudioError(Exception):
    """Raised when the uploaded audio cannot be transcribed."""


class VoiceModelUnavailableError(Exception):
    """Raised when a required local speech model is unavailable."""


def _get_whisper_model() -> WhisperModel:
    global _whisper_model_instance

    if _whisper_model_instance is not None:
        return _whisper_model_instance

    with _whisper_lock:
        if _whisper_model_instance is not None:
            return _whisper_model_instance

        model_name = os.getenv("WHISPER_MODEL", "base")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

        try:
            _whisper_model_instance = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type,
                cpu_threads=4,
                num_workers=1,
            )
        except Exception as exc:
            logger.exception("Could not load the Whisper model")
            raise VoiceModelUnavailableError(
                "Whisper model could not be loaded."
            ) from exc

    return _whisper_model_instance


def transcribe_audio(
    audio_bytes: bytes,
    file_suffix: str,
    language: str | None = None,
) -> dict[str, Any]:
    if not audio_bytes:
        raise InvalidAudioError("The uploaded audio file is empty.")

    safe_suffix = file_suffix.lower()
    if safe_suffix not in {
        ".wav",
        ".mp3",
        ".m4a",
        ".mp4",
        ".webm",
        ".ogg",
        ".flac",
        ".mpeg",
    }:
        raise InvalidAudioError("This audio file format is not supported.")

    temporary_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=safe_suffix,
            delete=False,
        ) as temporary_file:
            temporary_file.write(audio_bytes)
            temporary_path = temporary_file.name

        model = _get_whisper_model()

        try:
            with _whisper_lock:
                segments, info = model.transcribe(
                    temporary_path,
                    language=language,
                    beam_size=5,
                    vad_filter=True,
                )

                transcript_parts = [
                    segment.text.strip()
                    for segment in segments
                    if segment.text.strip()
                ]
        except Exception as exc:
            logger.info("Whisper could not decode the uploaded audio")
            raise InvalidAudioError(
                "The audio could not be decoded. Check the file and try again."
            ) from exc

        return {
            "text": " ".join(transcript_parts).strip(),
            "language": getattr(info, "language", None),
            "language_probability": getattr(
                info,
                "language_probability",
                None,
            ),
        }
    finally:
        if temporary_path:
            try:
                Path(temporary_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary audio file")


def _get_piper_voice() -> Any:
    global _piper_voice_instance

    if _piper_voice_instance is not None:
        return _piper_voice_instance

    with _piper_lock:
        if _piper_voice_instance is not None:
            return _piper_voice_instance

        configured_path = os.getenv(
            "PIPER_VOICE_PATH",
            "models/piper/en_US-lessac-medium.onnx",
        )
        voice_path = Path(configured_path)

        if not voice_path.is_absolute():
            voice_path = PROJECT_ROOT / voice_path

        if not voice_path.is_file():
            raise VoiceModelUnavailableError(
                "Piper voice file was not found. Set PIPER_VOICE_PATH "
                "to the downloaded .onnx voice file."
            )

        try:
            from piper import PiperVoice

            _piper_voice_instance = PiperVoice.load(str(voice_path))
        except Exception as exc:
            logger.exception("Could not load the Piper voice")
            raise VoiceModelUnavailableError(
                "Piper voice could not be loaded."
            ) from exc

    return _piper_voice_instance


def synthesize_speech(text: str) -> bytes:
    cleaned_text = text.strip()

    if not cleaned_text:
        raise ValueError("Text cannot be empty.")

    if len(cleaned_text) > 3000:
        raise ValueError("Text cannot be longer than 3000 characters.")

    voice = _get_piper_voice()
    output = BytesIO()

    try:
        with _piper_lock:
            with wave.open(output, "wb") as wav_file:
                voice.synthesize_wav(cleaned_text, wav_file)
    except Exception as exc:
        logger.exception("Piper speech synthesis failed")
        raise VoiceModelUnavailableError(
            "Speech audio could not be generated."
        ) from exc

    return output.getvalue()