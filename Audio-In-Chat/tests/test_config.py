"""Settings validation tests — no network, no API keys required."""

import pytest

from audio_chat import Settings
from audio_chat.exceptions import ConfigurationError


def test_missing_openai_key_raises():
    s = Settings(openai_api_key=None, llm_provider="openai")
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        s.validate()


def test_chunk_overlap_must_be_smaller_than_size():
    s = Settings(
        openai_api_key="sk-test",
        chunk_size=200,
        chunk_overlap=200,
    )
    with pytest.raises(ConfigurationError, match="chunk_overlap"):
        s.validate()


def test_assemblyai_provider_requires_key():
    s = Settings(
        openai_api_key="sk-test",
        transcription_provider="assemblyai",
        assemblyai_api_key=None,
    )
    with pytest.raises(ConfigurationError, match="ASSEMBLYAI_API_KEY"):
        s.validate()


def test_valid_openai_config_passes():
    s = Settings(openai_api_key="sk-test")
    s.validate()  # should not raise


def test_retrieval_top_k_must_be_positive():
    s = Settings(openai_api_key="sk-test", retrieval_top_k=0)
    with pytest.raises(ConfigurationError, match="retrieval_top_k"):
        s.validate()
