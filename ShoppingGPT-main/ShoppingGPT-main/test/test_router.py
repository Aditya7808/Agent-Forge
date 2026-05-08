from shoppinggpt.router.lib_semantic_router import SemanticRouter


def main():
    router = SemanticRouter()

    test_queries = [
        ("What's the price of this product?", "products"),
        ("What's your favorite food?", "chitchat"),
        ("Does this come in blue?", "products"),
        ("The weather is beautiful today!", "chitchat"),
        ("Do you sell jackets?", "products"),
        ("Can you recommend a movie?", "chitchat"),
        ("What's the return policy?", "products"),
        ("Hello!", "chitchat"),
        ("Tìm áo sơ mi trắng", "products"),
        ("Xin chào bạn", "chitchat"),
    ]

    correct = 0
    for query, expected in test_queries:
        result = router.guide(query)
        match = result == expected
        correct += int(match)
        status = "OK" if match else "MISMATCH"
        print(f"[{status}] '{query}' -> {result} (expected {expected})")

    print(f"\nAccuracy: {correct}/{len(test_queries)} ({100*correct/len(test_queries):.0f}%)")


if __name__ == "__main__":
    main()
