"""ShoppingGPT Flask backend.

Endpoints:
    GET  /              – chat UI
    POST /api/chat      – send a message, receive { reply, route, products, session_id }
    GET  /api/history   – conversation history for the active session
    POST /api/reset     – clear the active session's memory
    GET  /api/health    – liveness probe
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from threading import Lock
from typing import Dict, List, Tuple

from flask import Flask, jsonify, render_template, request, session
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
from shoppinggpt.tool.catalogue import extract_product_codes, fetch_by_codes


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("shoppinggpt")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["JSON_AS_ASCII"] = False

LLM = build_llm()
ROUTER = SemanticRouter()
AGENT = ShoppingAgent(LLM)

_HISTORY_TURN_LIMIT = 12  # keep the last N user/assistant messages per session
_SESSIONS: Dict[str, List[BaseMessage]] = {}
_SESSIONS_LOCK = Lock()


def _get_history() -> Tuple[str, List[BaseMessage]]:
    sid = session.get("sid")
    if not sid:
        sid = secrets.token_urlsafe(16)
        session["sid"] = sid
    with _SESSIONS_LOCK:
        history = _SESSIONS.get(sid)
        if history is None:
            history = []
            _SESSIONS[sid] = history
    return sid, history


def _save_turn(sid: str, user_msg: str, ai_msg: str) -> None:
    with _SESSIONS_LOCK:
        history = _SESSIONS.setdefault(sid, [])
        history.append(HumanMessage(content=user_msg))
        history.append(AIMessage(content=ai_msg))
        # Trim oldest pairs once we exceed the limit so memory stays bounded.
        if len(history) > _HISTORY_TURN_LIMIT * 2:
            del history[0 : len(history) - _HISTORY_TURN_LIMIT * 2]


def _route(query: str) -> str:
    try:
        return ROUTER.guide(query)
    except Exception as err:  # noqa: BLE001
        log.warning("Router failure, falling back to chitchat: %s", err)
        return CHITCHAT_ROUTE_NAME


def _answer(query: str, route: str, history: List[BaseMessage]) -> str:
    if route in {PRODUCT_ROUTE_NAME, POLICY_ROUTE_NAME, RECOMMEND_ROUTE_NAME}:
        return AGENT.invoke(query, history)
    return chitchat_reply(LLM, query, history)


@app.route("/")
def home():
    return render_template("index.html", app_name=APP_NAME)


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message is too long (max 2000 chars)."}), 400

    sid, history = _get_history()
    started = time.time()

    try:
        route = _route(message)
        reply = _answer(message, route, history)
    except Exception as err:  # noqa: BLE001
        log.exception("Chat handler failed")
        return jsonify(
            {
                "error": "Something went wrong handling that message.",
                "detail": str(err),
            }
        ), 500

    _save_turn(sid, message, reply)

    codes = extract_product_codes(reply)
    products = fetch_by_codes(codes) if codes else []

    elapsed_ms = int((time.time() - started) * 1000)
    log.info("[%s] route=%s in=%dms text=%r", sid[:6], route, elapsed_ms, message[:80])

    return jsonify(
        {
            "reply": reply,
            "route": route,
            "products": products,
            "session_id": sid,
            "elapsed_ms": elapsed_ms,
        }
    )


@app.route("/api/history", methods=["GET"])
def history_endpoint():
    sid, history = _get_history()
    messages = []
    for msg in history:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        messages.append({"role": role, "content": content})
    return jsonify({"session_id": sid, "messages": messages})


@app.route("/api/reset", methods=["POST"])
def reset():
    sid = session.get("sid")
    if sid:
        with _SESSIONS_LOCK:
            _SESSIONS.pop(sid, None)
    session.pop("sid", None)
    return jsonify({"ok": True})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": APP_NAME, "sessions": len(_SESSIONS)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
