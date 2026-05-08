"""Synthetic conversation generator (OpenAI-only).

Original version targeted Groq with a custom rate limiter. This rewrite uses
the same OpenAI client the rest of the project uses, keeps things simple,
and is safe to run repeatedly. Generates fashion-store conversations and
appends them to data/synthetic_conversations.json.

    python generate_synthesic_data.py --count 50
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from langchain_core.prompts import PromptTemplate

from shoppinggpt.config import build_llm

ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "data" / "synthetic_conversations.json"

PROMPT = PromptTemplate.from_template(
    """Generate one realistic chat between a customer and a fashion-store
assistant. Topics: product availability, sizing, returns, outfit advice,
or small talk. Keep it 4–8 turns. Output strict JSON of the form:
{{"turns": [{{"role": "user"|"assistant", "content": "..."}}, ...]}}.
"""
)


def generate_one(llm) -> dict:
    response = llm.invoke(PROMPT.format())
    text = getattr(response, "content", str(response)).strip()
    # Handle accidental markdown fences from the model.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.9)
    args = parser.parse_args()

    llm = build_llm(temperature=args.temperature)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    if not isinstance(existing, list):
        existing = []

    generated = 0
    for i in range(args.count):
        try:
            convo = generate_one(llm)
            existing.append(convo)
            generated += 1
            print(f"[{i + 1}/{args.count}] ok ({len(convo.get('turns', []))} turns)")
        except Exception as err:  # noqa: BLE001
            print(f"[{i + 1}/{args.count}] failed: {err}", file=sys.stderr)
        time.sleep(0.2)

    OUTPUT_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {generated} new conversations to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
