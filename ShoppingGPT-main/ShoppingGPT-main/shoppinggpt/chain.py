"""Chitchat chain — greetings only; hard refusal for off-topic.

Used when the semantic router classifies the query as casual conversation.
We do NOT trust the LLM to refuse off-topic reliably (it tends to "be
helpful"), so off-topic messages get a deterministic, hard-coded refusal.
Only true greetings reach the LLM."""
from __future__ import annotations

import re
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


GREETING_SYSTEM = """You are ShoppingGPT, the assistant for one online
fashion store. The user is greeting you or asking what you can do.

Reply in 1–2 short sentences and end with ONE concrete next step
(e.g. "Want me to find something, or check a policy?"). Be warm and
specific, not chatty.

Hard rules:
- Reply in English only, even if the user writes another language.
- Never invent products, prices, or policies. Never recommend a specific
  product here — the catalogue agent handles that.
- No emoji unless the user used one first. No filler ("Great question!",
  "Certainly!", "As an AI…", "I'd be happy to help!").
- Keep the reply under 35 words."""


REFUSAL_REPLY = (
    "That's outside what I can help with — I'm the shopping assistant for "
    "this store. Want me to find something, or check a policy?"
)


# Tokens / phrases that mark a true greeting / about-the-bot question.
# Anything that doesn't hit one of these is treated as off-topic and
# refused without an LLM call.
_GREETING_PATTERNS = [
    r"^\s*(hi+|hey+|hello+|yo|sup|hiya)\b",
    r"\bgood\s+(morning|afternoon|evening|night)\b",
    r"\bhow\s+(are|r)\s+(you|u|ya)\b",
    r"\bwhat'?s\s+up\b",
    r"\bnice\s+to\s+(meet|see)\s+you\b",
    r"^\s*(thanks?|thank\s+you|ty|thx|cheers)\b",
    r"^\s*(bye|goodbye|see\s+ya|see\s+you|later)\b",
    r"\bwho\s+(are|r)\s+(you|u)\b",
    r"\bwhat'?s\s+your\s+name\b",
    r"\bwhat\s+can\s+you\s+(do|help)\b",
    r"\bhow\s+do\s+you\s+work\b",
    r"\bwho\s+(built|made|created)\s+you\b",
]
_GREETING_RE = re.compile("|".join(_GREETING_PATTERNS), re.IGNORECASE)


def _is_greeting(text: str) -> bool:
    if not text:
        return False
    # Cap length: a long message with "hi" buried in it is not a greeting.
    if len(text) > 80:
        return False
    return bool(_GREETING_RE.search(text))


def chitchat_reply(llm, query: str, history: List[BaseMessage] | None = None) -> str:
    if not _is_greeting(query):
        return REFUSAL_REPLY

    messages: List[BaseMessage] = [SystemMessage(content=GREETING_SYSTEM)]
    if history:
        messages.extend(history)
    messages.append(HumanMessage(content=query))
    response = llm.invoke(messages)
    if isinstance(response, AIMessage):
        return response.content if isinstance(response.content, str) else str(response.content)
    return getattr(response, "content", str(response))
