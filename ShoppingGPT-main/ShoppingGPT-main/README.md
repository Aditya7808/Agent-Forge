# ShoppingGPT

An AI personal-shopper for an online fashion store. Built on **OpenAI** + **LangChain** + **Flask**, with a custom multi-intent semantic router, SQLite product catalogue, FAISS-backed policy search, and a modern dark/light chat UI that renders real product cards.

> v2 rewrite — switched from Gemini → OpenAI, replaced the legacy storefront template with a custom UI, added multi-intent routing, structured product responses, per-session memory, and safer tool execution.

## Features

- **Multi-intent semantic router** — classifies queries as `products`, `policy`, `recommend`, or `chitchat` using OpenAI embeddings and cosine similarity over curated example utterances. Falls back gracefully when scores are ambiguous.
- **Tool-calling agent** — uses the right tool per intent: catalogue lookup, policy retrieval, or grounded outfit recommendation.
- **Guarded SQL** — the agent's product tool only generates `SELECT` queries; an allow-list refuses `INSERT`/`UPDATE`/`DELETE`/`DROP`/`PRAGMA`/etc., even if the LLM is jailbroken.
- **Grounded recommendations** — the stylist tool reads the live catalogue before suggesting outfits, so it never hallucinates products that don't exist.
- **English-only** — clean, consistent product catalogue and policy doc; agent always replies in English.
- **Per-session memory** — each browser session keeps its own conversation history; reset with one click.
- **Modern UI** — custom CSS design system with dark/light themes, animated message bubbles, product cards rendered from agent output, voice input, typing indicator, suggestion chips. No Bootstrap, no template fluff.
- **Production-ready Flask** — JSON API, structured logging, request validation, health probe, configurable via `.env`.

## Architecture

```
                 ┌─────────────┐
   user msg ────▶│  /api/chat  │────▶ SemanticRouter (OpenAI embeddings, cosine)
                 └─────┬───────┘                │
                       │                        ▼
                       │             ┌──────────────────────┐
                       │             │ products / policy /  │
                       │             │ recommend            │
                       │             └─────────┬────────────┘
                       │                       ▼
                       │             ShoppingAgent (tool-calling)
                       │             ├─ product_search_tool  (SQLite, guarded SQL)
                       │             ├─ policy_search_tool   (FAISS over policy.txt)
                       │             └─ outfit_recommendation_tool (grounded LLM)
                       │
                       └─ chitchat ─▶ ChitChat chain (mirror language, fashion bias)

       reply  ◀── extract [P###] codes ── attach product cards from SQLite
```

## Quick start

```bash
git clone <this-repo>
cd ShoppingGPT-main
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...

python scripts/init_db.py     # build SQLite catalogue from products.csv
python app.py                 # launch on http://localhost:5000
```

The first time the policy tool runs, it builds a FAISS index from `data/policy.txt` and caches it in `data/datastore/`.

## API

| Method | Path           | Body / Query                  | Returns                                                       |
|-------:|----------------|-------------------------------|---------------------------------------------------------------|
| `GET`  | `/`            | —                             | Chat UI                                                       |
| `POST` | `/api/chat`    | `{ "message": "..." }`        | `{ reply, route, products[], session_id, elapsed_ms }`        |
| `GET`  | `/api/history` | —                             | `{ session_id, messages: [{role, content}, ...] }`            |
| `POST` | `/api/reset`   | —                             | `{ ok: true }`                                                |
| `GET`  | `/api/health`  | —                             | `{ status, app, sessions }`                                   |

The `products` array contains structured rows pulled from SQLite for any product codes (`P001`, `P002`, …) the agent mentions in its reply, ready for the frontend to render as cards.

## Configuration

All configuration is environment-driven (see `.env.example`):

| Variable                 | Default                  | Notes                                           |
|--------------------------|--------------------------|-------------------------------------------------|
| `OPENAI_API_KEY`         | —                        | **Required**                                    |
| `OPENAI_CHAT_MODEL`      | `gpt-4o-mini`            | Any chat model the SDK accepts                  |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Used for routing + policy index                 |
| `OPENAI_TEMPERATURE`     | `0.2`                    | Lower = more deterministic                      |
| `FLASK_SECRET_KEY`       | random                   | Set this in production                          |
| `PORT`                   | `5000`                   |                                                 |
| `APP_NAME`               | `ShoppingGPT`            | Shown in the UI header                          |

## Project layout

```
ShoppingGPT-main/
├─ app.py                       # Flask backend, JSON API, sessions
├─ main.py                      # CLI entry point
├─ scripts/init_db.py           # build SQLite from products.csv
├─ shoppinggpt/
│  ├─ config.py                 # env, paths, OpenAI factories
│  ├─ agent.py                  # tool-calling shopping agent
│  ├─ chain.py                  # chitchat chain
│  ├─ router/router.py          # multi-intent semantic router
│  └─ tool/
│     ├─ product_search.py      # NL → guarded SELECT against SQLite
│     ├─ policy_search.py       # FAISS similarity over policy.txt
│     ├─ recommend.py           # outfit suggestions grounded in inventory
│     └─ catalogue.py           # parameterised helpers used by the API
├─ static/                      # style.css + app.js (vanilla, no framework)
├─ templates/index.html         # single-page chat UI
└─ data/
   ├─ products.csv              # canonical catalogue source
   ├─ products.db               # SQLite (regenerated by init_db.py)
   ├─ policy.txt                # company policies — embedded into FAISS
   └─ datastore/                # cached FAISS index (built on first run)
```

## Adapting it to your own store

1. Replace `data/products.csv` with your catalogue (keep the column names) and run `python scripts/init_db.py`.
2. Replace `data/policy.txt` with your store policies and delete `data/datastore/` so the index rebuilds.
3. (Optional) Edit the example utterances in `shoppinggpt/router/router.py` so they match your domain language.
4. (Optional) Tweak the agent's tone in `shoppinggpt/agent.py` (`SYSTEM_PROMPT`).

## Safety notes

- The `product_search_tool` enforces a `SELECT`-only allow-list and rejects any other SQL keyword — even if the model produces destructive output.
- Per-session memory lives in process memory only; deploy behind a session-aware proxy (or move memory to Redis) if you run multiple workers.
- API responses include `elapsed_ms` and a server-side `session_id` you can use for tracing.

## License

MIT — see [LICENSE](LICENSE).
