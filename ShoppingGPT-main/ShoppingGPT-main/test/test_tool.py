import os
from dotenv import load_dotenv

load_dotenv()

from shoppinggpt.tool.policy_search import policy_search_tool
from shoppinggpt.tool.product_search import product_search_tool


def test_policy_search():
    print("=== Policy Search Tool ===")
    queries = [
        "What is the return policy?",
        "How do I change my password?",
    ]
    for q in queries:
        results = policy_search_tool.invoke(q)
        print(f"\nQuery: {q}")
        print(f"Results ({len(results)} found):")
        for i, r in enumerate(results[:2], 1):
            print(f"  {i}. {r[:120]}...")


def test_product_search():
    print("\n=== Product Search Tool ===")
    queries = [
        "Find me a black dress",
        "Show products under 500000",
    ]
    for q in queries:
        results = product_search_tool.invoke(q)
        print(f"\nQuery: {q}")
        print(f"Results: {results}")


if __name__ == "__main__":
    test_policy_search()
    test_product_search()
