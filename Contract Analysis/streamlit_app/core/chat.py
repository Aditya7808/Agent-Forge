"""Grounded Q&A chat over the analyzed contract."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from prompts.prompts import PROMPTS


def build_chat_messages(
    contract_text: str,
    analysis_json: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
) -> List:
    """Build the message list for one chat turn."""
    sys = PROMPTS["qa_chat_system"].format(
        contract_text=contract_text[:24000],
        analysis_json=json.dumps(analysis_json, default=str)[:24000],
    )
    msgs = [SystemMessage(content=sys)]
    for h in history:
        if h["role"] == "user":
            msgs.append(HumanMessage(content=h["content"]))
        else:
            msgs.append(AIMessage(content=h["content"]))
    msgs.append(HumanMessage(content=user_message))
    return msgs


def answer(
    *,
    model: str,
    temperature: float,
    contract_text: str,
    analysis_json: Dict[str, Any],
    history: List[Dict[str, str]],
    user_message: str,
) -> str:
    llm = ChatOpenAI(model=model, temperature=temperature)
    msgs = build_chat_messages(contract_text, analysis_json, history, user_message)
    return llm.invoke(msgs).content
