"""Chitchat chain — friendly conversation with a fashion bias.

Used when the semantic router classifies the query as casual conversation.
Takes an explicit list of ``BaseMessage`` instances as history so the
caller controls memory."""
from __future__ import annotations

from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


CHITCHAT_SYSTEM = """You are ShoppingGPT, a friendly fashion-store assistant.
The user is making small talk. Reply warmly in 1–3 short sentences. When it
feels natural, weave in a fashion angle (a related style trend, a relevant
product category) — but never force it, and never invent specific products.
Always reply in English."""


def chitchat_reply(llm, query: str, history: List[BaseMessage] | None = None) -> str:
    messages: List[BaseMessage] = [SystemMessage(content=CHITCHAT_SYSTEM)]
    if history:
        messages.extend(history)
    messages.append(HumanMessage(content=query))
    response = llm.invoke(messages)
    if isinstance(response, AIMessage):
        return response.content if isinstance(response.content, str) else str(response.content)
    return getattr(response, "content", str(response))
