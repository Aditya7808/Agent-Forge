import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from shoppinggpt.router.lib_semantic_router import (
    SemanticRouter,
    PRODUCT_ROUTE_NAME,
    CHITCHAT_ROUTE_NAME,
)
from shoppinggpt.chain import create_chitchat_chain
from shoppinggpt.agent import ShoppingAgent

load_dotenv()

LLM = ChatOpenAI(
    temperature=0.1,
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

SHARED_MEMORY = ConversationBufferWindowMemory(
    return_messages=True,
    memory_key="chat_history",
    k=20,
)

SEMANTIC_ROUTER = SemanticRouter()


def handle_query(query: str) -> dict:
    try:
        guided_route = SEMANTIC_ROUTER.guide(query)
    except Exception:
        guided_route = CHITCHAT_ROUTE_NAME

    if guided_route == PRODUCT_ROUTE_NAME:
        agent = ShoppingAgent(LLM, SHARED_MEMORY)
        content = agent.invoke(query)
    else:
        chain = create_chitchat_chain(LLM, SHARED_MEMORY)
        raw = chain.invoke({"input": query})
        content = raw.content if hasattr(raw, "content") else str(raw)

    SHARED_MEMORY.chat_memory.add_user_message(query)
    SHARED_MEMORY.chat_memory.add_ai_message(content)

    return {"response": content, "type": guided_route}


def main():
    print("\n  ShoppingGPT - AI Fashion Store Assistant")
    print("  Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break
        try:
            result = handle_query(user_input)
            print(f"\nShoppingGPT [{result['type']}]: {result['response']}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
