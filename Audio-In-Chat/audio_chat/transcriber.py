"""Audio transcription providers.

Default: OpenAI Whisper (per user's OpenAI-first preference).
Optional: AssemblyAI for built-in speaker diarization.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from audio_chat.config import Settings
from audio_chat.exceptions import (
    AudioFileTooLargeError,
    TranscriptionError,
    UnsupportedAudioFormatError,
)
from audio_chat.logger import get_logger

logger = get_logger("transcriber")


@dataclass
class TranscriptSegment:
    """One labeled chunk of transcript text."""
    speaker: Optional[str]
    text: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "text": self.text,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
        }


def _validate_audio_file(path: str, settings: Settings) -> Path:
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise TranscriptionError(f"Audio file not found: {path}")
    ext = p.suffix.lower()
    if ext not in settings.allowed_audio_extensions:
        raise UnsupportedAudioFormatError(
            f"Unsupported audio extension {ext!r}. "
            f"Allowed: {', '.join(settings.allowed_audio_extensions)}"
        )
    size_mb = p.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_audio_mb:
        raise AudioFileTooLargeError(
            f"Audio file is {size_mb:.1f} MB, exceeds limit of {settings.max_audio_mb} MB. "
            f"Increase MAX_AUDIO_MB if needed (large files may also exceed provider limits)."
        )
    return p


class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> List[TranscriptSegment]:
        ...


class OpenAITranscriber(BaseTranscriber):
    """OpenAI Whisper API transcription.

    Notes:
        * Whisper does not natively diarize speakers; every segment is labeled
          'Speaker' for downstream consistency.
        * Files >25 MB will be rejected by OpenAI; we surface that as a
          TranscriptionError with a clearer message.
    """

    def __init__(self, settings: Settings):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise TranscriptionError("openai package is required.") from e
        if not settings.openai_api_key:
            raise TranscriptionError("OPENAI_API_KEY is required for OpenAITranscriber.")
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.openai_transcription_model
        self.settings = settings
        logger.info("OpenAITranscriber initialized | model=%s", self.model)

    def transcribe(self, audio_path: str) -> List[TranscriptSegment]:
        path = _validate_audio_file(audio_path, self.settings)
        logger.info("Transcribing (OpenAI) %s ...", path.name)
        try:
            with open(path, "rb") as fh:
                resp = self._client.audio.transcriptions.create(
                    model=self.model,
                    file=fh,
                    response_format="verbose_json",
                )
        except Exception as e:
            msg = str(e)
            if "Maximum content size" in msg or "25 MB" in msg:
                raise AudioFileTooLargeError(
                    "OpenAI rejected the file (25 MB hard limit). "
                    "Split or compress the audio first."
                ) from e
            raise TranscriptionError(f"OpenAI transcription failed: {e}") from e

        segments_raw = getattr(resp, "segments", None) or []
        if not segments_raw:
            text = getattr(resp, "text", "") or ""
            if not text.strip():
                raise TranscriptionError("Transcription returned no text.")
            return [TranscriptSegment(speaker="Speaker", text=text.strip())]

        segments: List[TranscriptSegment] = []
        for seg in segments_raw:
            seg_text = (
                seg.get("text") if isinstance(seg, dict) else getattr(seg, "text", "")
            ) or ""
            seg_start = (
                seg.get("start") if isinstance(seg, dict) else getattr(seg, "start", None)
            )
            seg_end = (
                seg.get("end") if isinstance(seg, dict) else getattr(seg, "end", None)
            )
            if not seg_text.strip():
                continue
            segments.append(
                TranscriptSegment(
                    speaker="Speaker",
                    text=seg_text.strip(),
                    start_ms=int(seg_start * 1000) if seg_start is not None else None,
                    end_ms=int(seg_end * 1000) if seg_end is not None else None,
                )
            )
        logger.info("Transcribed %d segments", len(segments))
        return segments


class AssemblyAITranscriber(BaseTranscriber):
    """AssemblyAI transcription with built-in speaker diarization."""

    def __init__(self, settings: Settings):
        try:
            import assemblyai as aai
        except ImportError as e:
            raise TranscriptionError(
                "assemblyai is required for AssemblyAITranscriber. "
                "Install with: pip install assemblyai"
            ) from e
        if not settings.assemblyai_api_key:
            raise TranscriptionError("ASSEMBLYAI_API_KEY is required.")
        aai.settings.api_key = settings.assemblyai_api_key
        self._aai = aai
        self._transcriber = aai.Transcriber()
        self.settings = settings
        logger.info("AssemblyAITranscriber initialized")

    def transcribe(self, audio_path: str) -> List[TranscriptSegment]:
        path = _validate_audio_file(audio_path, self.settings)
        config = self._aai.TranscriptionConfig(
            speaker_labels=self.settings.assemblyai_speaker_labels,
            speakers_expected=self.settings.assemblyai_expected_speakers,
        )
        logger.info("Transcribing (AssemblyAI) %s ...", path.name)
        try:
            transcript = self._transcriber.transcribe(str(path), config=config)
        except Exception as e:
            raise TranscriptionError(f"AssemblyAI transcription failed: {e}") from e

        if transcript.status == "error":
            raise TranscriptionError(f"AssemblyAI error: {transcript.error}")

        utterances = getattr(transcript, "utterances", None) or []
        if not utterances:
            text = (getattr(transcript, "text", "") or "").strip()
            if not text:
                raise TranscriptionError("Transcription returned no text.")
            return [TranscriptSegment(speaker="Speaker", text=text)]

        segments = [
            TranscriptSegment(
                speaker=f"Speaker {u.speaker}",
                text=(u.text or "").strip(),
                start_ms=getattr(u, "start", None),
                end_ms=getattr(u, "end", None),
            )
            for u in utterances
            if (u.text or "").strip()
        ]
        logger.info("Transcribed %d utterances", len(segments))
        return segments


def build_transcriber(settings: Settings) -> BaseTranscriber:
    """Factory: pick a transcriber implementation from settings."""
    provider = settings.transcription_provider
    if provider == "openai":
        return OpenAITranscriber(settings)
    if provider == "assemblyai":
        return AssemblyAITranscriber(settings)
    raise TranscriptionError(f"Unknown transcription provider: {provider!r}")
