from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from shoppinggpt.tool.product_search import product_search_tool
from shoppinggpt.tool.policy_search import policy_search_tool

SYSTEM_PROMPT = """You are ShoppingGPT, an expert AI shopping assistant for a Vietnamese fashion store.

Your capabilities:
1. **Product Search** — Find products by name, color, size, material, brand, gender, price range, or stock status.
2. **Policy Lookup** — Answer questions about shipping, returns, payments, membership, and store policies.

Guidelines:
- Always use tools to look up real data. Never fabricate product details or prices.
- Present product results in a clear, structured format with key details (name, price, sizes, colors, stock).
- Format prices in Vietnamese Dong (₫) with thousand separators (e.g., 350,000₫).
- If a search returns no results, suggest alternative queries or related products.
- Be warm, professional, and concise.
- Match the customer's language — reply in Vietnamese if they write in Vietnamese, English if they write in English.
- When recommending products, highlight what makes them a good fit for the customer's stated needs.
"""


class ShoppingAgent:
    def __init__(self, llm, shared_memory):
        self.llm = llm
        self.tools = [product_search_tool, policy_search_tool]
        self.memory = shared_memory
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def invoke(self, query: str) -> str:
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            handle_parsing_errors=True,
            memory=self.memory,
            max_iterations=5,
        )
        result = executor.invoke({"input": query})
        return result["output"]
