"""Interactive CLI for ShoppingGPT — handy for local testing without a browser."""
from __future__ import annotations

import sys
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from shoppinggpt.agent import ShoppingAgent
from shoppinggpt.chain import chitchat_reply
from shoppinggpt.config import APP_NAME, build_llm
from shoppinggpt.router import (
    CHITCHAT_ROUTE_NAME,
    POLICY_ROUTE_NAME,
    PRODUCT_ROUTE_NAME,
    RECOMMEND_ROUTE_NAME,
    SemanticRouter,
)


def run() -> int:
    print(f"{APP_NAME} CLI — type 'exit' or Ctrl-C to quit.\n")
    llm = build_llm()
    router = SemanticRouter()
    agent = ShoppingAgent(llm)
    history: List[BaseMessage] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            return 0

        try:
            route = router.guide(user_input)
        except Exception as err:  # noqa: BLE001
            print(f"[router error: {err}] — defaulting to chitchat")
            route = CHITCHAT_ROUTE_NAME

        if route in {PRODUCT_ROUTE_NAME, POLICY_ROUTE_NAME, RECOMMEND_ROUTE_NAME}:
            reply = agent.invoke(user_input, history)
        else:
            reply = chitchat_reply(llm, user_input, history)

        history.append(HumanMessage(content=user_input))
        history.append(AIMessage(content=reply))
        print(f"\nAssistant ({route}): {reply}\n")


if __name__ == "__main__":
    sys.exit(run())
