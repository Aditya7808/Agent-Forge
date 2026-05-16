"""Chunker unit tests — pure logic, no external deps."""

from audio_chat.chunking import chunk_segments, segments_to_text
from audio_chat.transcriber import TranscriptSegment


def _segs(*pairs):
    return [TranscriptSegment(speaker=sp, text=tx) for sp, tx in pairs]


def test_empty_input_returns_empty():
    assert chunk_segments([], chunk_size=100, chunk_overlap=10) == []


def test_small_segments_pack_into_single_chunk():
    segs = _segs(("Alice", "hi"), ("Bob", "hello"), ("Alice", "ok"))
    chunks = chunk_segments(segs, chunk_size=500, chunk_overlap=50)
    assert len(chunks) == 1
    assert "Alice: hi" in chunks[0]
    assert "Bob: hello" in chunks[0]


def test_large_input_splits_into_multiple_chunks():
    segs = _segs(*[("Speaker", "word " * 40)] * 10)  # ~200 chars each
    chunks = chunk_segments(segs, chunk_size=400, chunk_overlap=50)
    assert len(chunks) > 1
    for ch in chunks:
        assert len(ch) <= 800  # rough upper bound including overlap pack


def test_segments_to_text_uses_default_speaker():
    segs = [TranscriptSegment(speaker=None, text="solo")]
    assert segments_to_text(segs) == "Speaker: solo"


def test_huge_single_segment_is_hard_split():
    big = "x" * 1000
    segs = [TranscriptSegment(speaker="A", text=big)]
    chunks = chunk_segments(segs, chunk_size=300, chunk_overlap=50)
    # Hard-split path: every chunk no larger than chunk_size, all content present
    assert all(len(c) <= 300 for c in chunks)
    assert sum(len(c) for c in chunks) >= len(big)
