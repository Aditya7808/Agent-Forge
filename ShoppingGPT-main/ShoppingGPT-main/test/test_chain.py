import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from shoppinggpt.chain import create_chitchat_chain

load_dotenv()


def main():
    llm = ChatOpenAI(temperature=0.1, model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    memory = ConversationBufferWindowMemory(return_messages=True, memory_key="chat_history", k=10)

    chain = create_chitchat_chain(llm, memory)

    test_queries = [
        "Hello, how are you?",
        "The weather is nice today!",
        "What's your favorite color?",
    ]

    for query in test_queries:
        response = chain.invoke({"input": query})
        content = response.content if hasattr(response, "content") else str(response)
        print(f"User: {query}")
        print(f"Bot: {content}")
        print("---")


if __name__ == "__main__":
    main()
