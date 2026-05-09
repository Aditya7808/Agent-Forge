import os
import logging
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32).hex())
CORS(app)

_llm = None
_memory = None
_router = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(
            temperature=0.1,
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    return _llm


def _get_memory():
    global _memory
    if _memory is None:
        try:
            from langchain.memory import ConversationBufferWindowMemory
        except ImportError:
            from langchain_community.memory.chat_memory import ConversationBufferWindowMemory  # type: ignore
        _memory = ConversationBufferWindowMemory(
            return_messages=True,
            memory_key="chat_history",
            k=20,
        )
    return _memory


def _get_router():
    global _router
    if _router is None:
        from shoppinggpt.router.lib_semantic_router import SemanticRouter
        logger.info("Initializing semantic router...")
        _router = SemanticRouter()
        logger.info("Semantic router ready.")
    return _router


def handle_query(query: str) -> dict:
    from shoppinggpt.router.lib_semantic_router import PRODUCT_ROUTE_NAME, CHITCHAT_ROUTE_NAME
    from shoppinggpt.chain import create_chitchat_chain
    from shoppinggpt.agent import ShoppingAgent

    query = query.strip()
    if not query:
        return {"response": "Please enter a message.", "type": "error"}

    try:
        guided_route = _get_router().guide(query)
    except Exception:
        logger.exception("Router error, falling back to chitchat")
        guided_route = CHITCHAT_ROUTE_NAME

    llm = _get_llm()
    memory = _get_memory()

    try:
        if guided_route == PRODUCT_ROUTE_NAME:
            agent = ShoppingAgent(llm, memory)
            response = agent.invoke(query)
        else:
            chain = create_chitchat_chain(llm, memory)
            raw = chain.invoke({"input": query})
            response = raw.content if hasattr(raw, "content") else str(raw)
    except Exception:
        logger.exception("LLM invocation error")
        response = "Sorry, something went wrong processing your request. Please try again."
        guided_route = "error"

    memory.chat_memory.add_user_message(query)
    memory.chat_memory.add_ai_message(response)

    return {"response": response, "type": guided_route}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    logger.info("User: %s", user_message[:100])
    result = handle_query(user_message)
    logger.info("Route: %s | Response length: %d", result["type"], len(result["response"]))
    return jsonify(result)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@app.route("/get", methods=["GET"])
def get_bot_response_legacy():
    user_message = request.args.get("msg", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    return jsonify(handle_query(user_message))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
