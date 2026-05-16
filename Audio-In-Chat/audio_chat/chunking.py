"""Transcript chunking: turn diarized segments into retrievable text chunks."""

from __future__ import annotations

from typing import List, Sequence

from audio_chat.transcriber import TranscriptSegment


def segments_to_text(segments: Sequence[TranscriptSegment]) -> str:
    """Render segments as a 'Speaker: text' transcript."""
    lines = []
    for seg in segments:
        speaker = seg.speaker or "Speaker"
        lines.append(f"{speaker}: {seg.text}")
    return "\n".join(lines)


def chunk_segments(
    segments: Sequence[TranscriptSegment],
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> List[str]:
    """Chunk diarized segments into overlapping windows.

    Greedily packs whole segments into a window until adding the next would
    exceed `chunk_size`. The next window starts `chunk_overlap` chars back
    from the end of the previous one, on a segment boundary.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be < chunk_size")
    if not segments:
        return []

    rendered = [
        f"{(s.speaker or 'Speaker')}: {s.text}".strip()
        for s in segments
        if s.text and s.text.strip()
    ]
    if not rendered:
        return []

    chunks: List[str] = []
    i = 0
    n = len(rendered)
    while i < n:
        current: List[str] = []
        cur_len = 0
        j = i
        while j < n and (cur_len + len(rendered[j]) + 1) <= chunk_size:
            current.append(rendered[j])
            cur_len += len(rendered[j]) + 1
            j += 1
        if not current:
            # Single segment is bigger than chunk_size — hard-split it.
            big = rendered[i]
            for k in range(0, len(big), chunk_size):
                chunks.append(big[k : k + chunk_size])
            i += 1
            continue
        chunks.append("\n".join(current))

        # Walk back from j to create overlap on segment boundaries.
        if j >= n:
            break
        back_len = 0
        new_i = j
        while new_i > i and back_len < chunk_overlap:
            new_i -= 1
            back_len += len(rendered[new_i]) + 1
        # Guarantee forward progress.
        i = max(i + 1, new_i)
    return chunks
