"""Minimal library example — transcribe an audio file and ask one question.

Run:
    export OPENAI_API_KEY=sk-...
    python examples/basic_usage.py path/to/audio.mp3 "What was discussed?"
"""

from __future__ import annotations

import sys

from audio_chat import AudioChatPipeline


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python examples/basic_usage.py <audio_path> <question>")
        return 1

    audio_path, question = sys.argv[1], sys.argv[2]

    pipeline = AudioChatPipeline.from_env()
    summary = pipeline.ingest_audio(audio_path)
    print(
        f"Indexed: {summary['segments']} segments → "
        f"{summary['chunks']} chunks → {summary['indexed']} vectors\n"
    )

    print("Q:", question)
    print("A: ", end="", flush=True)
    for token in pipeline.stream_query(question):
        print(token, end="", flush=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
