"""Custom exception hierarchy for audio_chat."""


class AudioChatError(Exception):
    """Base exception for all audio_chat errors."""


class ConfigurationError(AudioChatError):
    """Raised when required configuration is missing or invalid."""


class TranscriptionError(AudioChatError):
    """Raised when audio transcription fails."""


class EmbeddingError(AudioChatError):
    """Raised when embedding generation fails."""


class VectorStoreError(AudioChatError):
    """Raised when vector store operations fail."""


class LLMError(AudioChatError):
    """Raised when LLM inference fails."""


class UnsupportedAudioFormatError(TranscriptionError):
    """Raised when an audio file format is not supported."""


class AudioFileTooLargeError(TranscriptionError):
    """Raised when an audio file exceeds size limits."""
