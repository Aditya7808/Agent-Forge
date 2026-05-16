<div align="center">

# Audio-In-Chat

### Talk to your audio — production-grade transcription + RAG, in one library

[![Python](https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?logo=openai&logoColor=white)](https://platform.openai.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-DC382D)](https://qdrant.tech/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-Apache_2.0-green)](../LICENSE)

</div>

Upload a meeting, podcast, lecture, or voice note → get a chat interface that
answers grounded in the transcript with optional source citations.

Part of the [Agent Forge](https://github.com/ayusingh-54/agent-forge) collection.

---

## Highlights

- **OpenAI-first**: GPT-4o-mini / GPT-4o chat + `text-embedding-3-*` embeddings + Whisper, out of the box.
- **Pluggable**: swap embedders (OpenAI ↔ HuggingFace), transcribers (Whisper ↔ AssemblyAI), and vector stores (in-memory ↔ self-hosted Qdrant ↔ Qdrant Cloud).
- **Zero-config demo mode**: `QDRANT_URL=:memory:` runs end-to-end without any infra.
- **Library-first design**: import `AudioChatPipeline` and integrate in any Python app — no Streamlit lock-in.
- **Streaming chat**: token-by-token UI updates and HTTP streaming via the FastAPI example.
- **Citations**: every answer can be expanded to show the retrieved source passages.
- **Production hygiene**: typed dataclasses, custom exception hierarchy, structured logging, input validation, configurable upload limits, Dockerfile + compose.

---

## Architecture

```
┌──────────────┐  audio   ┌────────────────┐ segments ┌─────────────┐ vectors ┌──────────┐
│   user       │ ───────► │  Transcriber   │ ───────► │  Chunker +  │ ──────► │  Qdrant  │
│ (UI / API)   │          │ Whisper/AssAI  │          │  Embedder   │         │  store   │
└──────────────┘          └────────────────┘          └─────────────┘         └────┬─────┘
       ▲                                                                            │
       │ streamed answer                                                            │
       │                                ┌──────────────┐  top-k chunks              │
       └────────────────────────────────│   RAGEngine  │◄───────────────────────────┘
                                        │  (OpenAI)    │
                                        └──────────────┘
```

| Layer | Module | Notes |
|---|---|---|
| Facade | `audio_chat.pipeline.AudioChatPipeline` | One object orchestrating the full flow |
| Transcription | `audio_chat.transcriber` | `OpenAITranscriber` (default) or `AssemblyAITranscriber` |
| Chunking | `audio_chat.chunking` | Speaker-aware overlapping chunks |
| Embeddings | `audio_chat.embeddings` | `OpenAIEmbedder` (default) or `HuggingFaceEmbedder` |
| Vector store | `audio_chat.vector_store` | Qdrant — in-memory / self-hosted / cloud |
| RAG | `audio_chat.rag` | Prompt building, retrieval, source attribution |
| LLM | `audio_chat.llm` | OpenAI chat completions, streaming-first |
| Config | `audio_chat.config` | Env-driven `Settings` dataclass |

---

## Project layout

```
Audio-In-Chat/
├── app.py                       # Streamlit UI
├── code_rag.py                  # Backwards-compat shim (old import paths)
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml           # Streamlit + Qdrant stack
├── .env.example
├── audio_chat/                  # ← the importable library
│   ├── __init__.py
│   ├── config.py
│   ├── exceptions.py
│   ├── logger.py
│   ├── embeddings.py
│   ├── transcriber.py
│   ├── chunking.py
│   ├── vector_store.py
│   ├── llm.py
│   ├── rag.py
│   └── pipeline.py
├── examples/
│   ├── basic_usage.py           # CLI: transcribe + answer one question
│   └── api_server.py            # FastAPI streaming endpoints
└── tests/
    ├── test_config.py
    └── test_chunking.py
```

---

## Quick start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...
```

The default config requires **only** `OPENAI_API_KEY` — everything else has safe
defaults (`QDRANT_URL=:memory:`, GPT-4o-mini chat, `text-embedding-3-small`,
Whisper transcription).

### 3. Run the Streamlit UI

```bash
streamlit run app.py
```

Then in the browser:

1. Paste your OpenAI key in the sidebar (or rely on the `.env`).
2. Click **Apply configuration**.
3. Upload an audio file and click **Transcribe & index**.
4. Ask questions in the chat box.

### Docker (Streamlit + persistent Qdrant)

```bash
cp .env.example .env   # set OPENAI_API_KEY
docker compose up --build
# → http://localhost:8501
```

The compose file boots Qdrant on `:6333` (with a named volume for persistence)
and points the app at it via `QDRANT_URL=http://qdrant:6333`.

---

## Use as a library

```python
from audio_chat import AudioChatPipeline

pipeline = AudioChatPipeline.from_env()  # reads OPENAI_API_KEY etc.

# 1. Ingest
summary = pipeline.ingest_audio("meeting.mp3")
print(summary)  # {'segments': 42, 'chunks': 11, 'indexed': 11, ...}

# 2. Stream an answer
for token in pipeline.stream_query("What were the action items?"):
    print(token, end="", flush=True)

# 3. Get an answer with source citations
result = pipeline.query_with_sources("Who proposed the deadline?")
print(result["answer"])
for src in result["sources"]:
    print(f"[{src['score']:.3f}] {src['text'][:120]}...")
```

### Override settings programmatically

```python
from audio_chat import AudioChatPipeline, Settings

settings = Settings(
    openai_api_key="sk-...",
    llm_model="gpt-4o",
    transcription_provider="assemblyai",
    assemblyai_api_key="...",
    qdrant_url="https://xyz.cloud.qdrant.io",
    qdrant_api_key="...",
    qdrant_collection="my_org_meetings",
)
pipeline = AudioChatPipeline(settings)
```

Or use kwargs as overrides on top of env:

```python
pipeline = AudioChatPipeline.from_kwargs(llm_model="gpt-4o", retrieval_top_k=8)
```

### Integrate into an existing app

```python
# Bring your own Qdrant client / collection name:
from audio_chat import Settings, AudioChatPipeline
from audio_chat.vector_store import QdrantStore
from audio_chat.embeddings import build_embedder

settings = Settings.from_env()
embedder = build_embedder(settings)
store = QdrantStore(settings, vector_dim=embedder.dim)

pipeline = AudioChatPipeline(settings, embedder=embedder, store=store)
```

### FastAPI server

```bash
pip install fastapi "uvicorn[standard]" python-multipart
export OPENAI_API_KEY=sk-...
uvicorn examples.api_server:app --reload --port 8000
```

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/ingest` | multipart `file` | `{segments, chunks, indexed}` |
| `POST` | `/query` | `{"question": "...", "top_k": 5}` | streamed text |
| `POST` | `/reset` | — | `{"status": "ok"}` |
| `GET`  | `/stats` | — | pipeline metadata |

---

## Configuration reference

All settings can be set via env vars (`Settings.from_env()`) or kwargs (`Settings(...)`).
See [`.env.example`](.env.example) for the complete list. Highlights:

| Env var | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | _(required)_ | Used for chat, embeddings, Whisper |
| `OPENAI_BASE_URL` | OpenAI | Override for Azure / vLLM / proxies |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model |
| `LLM_TEMPERATURE` | `0.3` | |
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `huggingface` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | |
| `EMBEDDING_DIM` | `1536` | Must match the model (1536 / 3072) |
| `TRANSCRIPTION_PROVIDER` | `openai` | `openai` (Whisper) or `assemblyai` |
| `ASSEMBLYAI_API_KEY` | — | Required if provider=assemblyai |
| `QDRANT_URL` | `:memory:` | Or `http://localhost:6333`, or cloud URL |
| `QDRANT_API_KEY` | — | Required for Qdrant Cloud |
| `QDRANT_COLLECTION` | `audio_chat_default` | |
| `RETRIEVAL_TOP_K` | `5` | Chunks per query |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `100` | Char-based |
| `MAX_AUDIO_MB` | `50` | Upload cap (Whisper hard limit is 25 MB) |
| `LOG_LEVEL` | `INFO` | |
| `LOG_JSON` | `false` | Switch to JSON log lines for ingestion |

---

## Why these choices?

- **OpenAI by default** — best general quality / lowest setup friction. The
  factory pattern (`build_embedder`, `build_transcriber`, `build_llm`) keeps the
  door open for other providers.
- **Qdrant** — single backend that gracefully scales from `:memory:` to Qdrant
  Cloud without code changes.
- **Cosine distance + normalised vectors** — both OpenAI embeddings and modern
  HF sentence-transformers ship normalised, so cosine is the safe universal choice.
- **`query_points`** (not the deprecated `search`) — uses the current Qdrant API.
- **Char-based chunker** — provider-independent, no tokenizer dependency, fast.
- **Streaming-first LLM** — better UX in the UI, and trivial to adapt for HTTP SSE.

---

## Testing

```bash
pip install pytest
pytest -q
```

The default test suite is offline (no API keys needed) — it covers the
config validator and the chunker.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ConfigurationError: OPENAI_API_KEY is required` | Set the env var or pass it to `Settings(...)`. |
| `AudioFileTooLargeError` | Whisper has a hard 25 MB limit. Split or compress. Raise `MAX_AUDIO_MB` only after compressing. |
| `VectorStoreError: ... Connection refused` | Either run `docker compose up qdrant`, or fall back to `QDRANT_URL=:memory:`. |
| Embeddings dim mismatch on a re-used collection | Drop the collection (UI: **Reset index**, or `pipeline.reset_index()`) when changing embedding models. |
| Slow first run with HuggingFace embedder | Model is downloaded on first use into `HF_CACHE_DIR`; subsequent runs are fast. |

---

## Backwards compatibility

The original [`code_rag.py`](code_rag.py) is still present as a thin shim that
re-exports the new classes under their old names. New code should import from
`audio_chat` directly.

---

## License

Apache-2.0 — see the root [LICENSE](../LICENSE) of Agent Forge.
