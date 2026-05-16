"""
audio_chat — Production-grade audio transcription + RAG chat library.

Public API:
    AudioChatPipeline  — high-level facade (transcribe + index + query)
    Settings           — configuration via env vars / kwargs
    AudioChatError     — base exception

Example:
    >>> from audio_chat import AudioChatPipeline
    >>> pipeline = AudioChatPipeline.from_env()
    >>> pipeline.ingest_audio("meeting.mp3")
    >>> for chunk in pipeline.stream_query("What were the action items?"):
    ...     print(chunk, end="")
"""

from audio_chat.config import Settings, get_settings
from audio_chat.exceptions import (
    AudioChatError,
    ConfigurationError,
    TranscriptionError,
    EmbeddingError,
    VectorStoreError,
    LLMError,
)
from audio_chat.pipeline import AudioChatPipeline

__version__ = "1.0.0"

__all__ = [
    "AudioChatPipeline",
    "Settings",
    "get_settings",
    "AudioChatError",
    "ConfigurationError",
    "TranscriptionError",
    "EmbeddingError",
    "VectorStoreError",
    "LLMError",
    "__version__",
]
