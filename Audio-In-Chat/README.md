<div align="center">

# 🎧 Audio-In-Chat

### Talk to your audio — industry-grade transcription + RAG, in one library

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/OpenAI-Whisper_+_GPT--4o-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI"/>
  <img src="https://img.shields.io/badge/Qdrant-Vector_DB-DC382D?style=flat-square" alt="Qdrant"/>
  <img src="https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/FastAPI-Server-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/license-Apache_2.0-green?style=flat-square" alt="License"/>
</p>

<em>Drop a meeting · podcast · lecture · voice note → ask anything · get grounded answers with citations</em>

</div>

---

Part of the [🔨 Agent Forge](../README.md) collection.

> Upload any audio file → it gets transcribed with **OpenAI Whisper** (or AssemblyAI for speaker diarization), chunked, embedded with **`text-embedding-3-small`**, stored in **Qdrant**, and made queryable through a streaming **GPT-4o** chat — all behind a single `AudioChatPipeline` class you can drop into any Python app.

📺 See [`demo.mp4`](demo.mp4) for a walkthrough of the UI.

---

## 🌟 Highlights

| | |
|---|---|
| 🟢 **OpenAI-first** | GPT-4o-mini / GPT-4o chat · `text-embedding-3-*` · Whisper — out of the box |
| 🔌 **Pluggable** | Swap embedders (OpenAI ↔ HuggingFace), transcribers (Whisper ↔ AssemblyAI), and vector stores (in-memory ↔ self-hosted Qdrant ↔ Qdrant Cloud) without code changes |
| ⚡ **Zero-config demo** | Default `QDRANT_URL=:memory:` runs the entire stack with no extra infra — only `OPENAI_API_KEY` required |
| 📚 **Library-first** | `from audio_chat import AudioChatPipeline` and integrate into any Python app — Streamlit is just *one* UI |
| 💬 **Streaming chat** | Token-by-token UI updates and HTTP streaming via the FastAPI example |
| 🔍 **Citations** | Every answer can expand to show the source passages with similarity scores |
| 🛡️ **Production hygiene** | Custom exception hierarchy · structured logging · config validation · upload limits · Dockerfile + compose |
| 🧪 **Tested** | Offline-runnable pytest suite (config + chunker), zero API keys required |

---

## 🎬 Quick demo

```python
from audio_chat import AudioChatPipeline

pipe = AudioChatPipeline.from_env()           # reads .env → OPENAI_API_KEY
pipe.ingest_audio("meeting.mp3")              # transcribe → chunk → embed → index

for token in pipe.stream_query("What were the action items?"):
    print(token, end="", flush=True)
```

Or with citations:

```python
result = pipe.query_with_sources("Who proposed the deadline?")
print(result["answer"])
for src in result["sources"]:
    print(f"[score={src['score']:.3f}] {src['text'][:120]}...")
```

---

## 🏗️ Architecture

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

## 📂 Project layout

```
Audio-In-Chat/
├── app.py                       # Streamlit UI (load_dotenv → sidebar pre-populated)
├── code_rag.py                  # Backwards-compat shim (old import paths)
├── requirements.txt
├── pyproject.toml               # Publishable package, optional extras
├── Dockerfile                   # python:3.11-slim + ffmpeg + healthcheck
├── docker-compose.yml           # Streamlit + persistent Qdrant
├── .env.example                 # All ~25 env vars documented
├── demo.mp4                     # UI walkthrough
├── audio_chat/                  # ← the importable library
│   ├── __init__.py              # Public API (AudioChatPipeline, Settings, exceptions)
│   ├── config.py                # Env-driven Settings dataclass + .validate()
│   ├── exceptions.py            # AudioChatError hierarchy
│   ├── logger.py                # Structured logger (JSON or human)
│   ├── embeddings.py            # OpenAIEmbedder · HuggingFaceEmbedder
│   ├── transcriber.py           # OpenAITranscriber · AssemblyAITranscriber + file validation
│   ├── chunking.py              # Speaker-aware overlapping chunker
│   ├── vector_store.py          # QdrantStore (memory / self-hosted / cloud)
│   ├── llm.py                   # OpenAI chat — streaming-first
│   ├── rag.py                   # Retrieval + prompt building + sources
│   └── pipeline.py              # AudioChatPipeline facade
├── examples/
│   ├── basic_usage.py           # CLI: transcribe + answer one question
│   └── api_server.py            # FastAPI: /ingest /query (SSE) /reset /stats
└── tests/
    ├── test_config.py           # 5 tests
    └── test_chunking.py         # 5 tests
```

---

## 🚀 Quick start

### Option 1 — Streamlit UI (recommended)

```bash
cd Audio-In-Chat
pip install -r requirements.txt
cp .env.example .env             # then edit and set OPENAI_API_KEY=sk-...
streamlit run app.py             # → http://localhost:8501
```

The sidebar auto-loads from `.env`. Click **✅ Apply configuration**, drop an audio file, hit **🚀 Transcribe & index**, then ask questions in the chat box.

### Option 2 — Docker (Streamlit + persistent Qdrant)

```bash
cp .env.example .env             # set OPENAI_API_KEY
docker compose up --build        # → http://localhost:8501
```

Compose boots Qdrant on `:6333` with a named volume for persistence and wires the app at `QDRANT_URL=http://qdrant:6333`.

### Option 3 — Library (any Python app)

```bash
pip install -r requirements.txt
```

```python
from audio_chat import AudioChatPipeline
pipe = AudioChatPipeline.from_env()
pipe.ingest_audio("meeting.mp3")
print(pipe.query("Summarize the meeting in 3 bullets."))
```

### Option 4 — FastAPI server

```bash
pip install fastapi "uvicorn[standard]" python-multipart
uvicorn examples.api_server:app --reload --port 8000
```

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/ingest` | multipart `file` | `{segments, chunks, indexed}` |
| `POST` | `/query` | `{"question": "...", "top_k": 5}` | **streamed** text (SSE) |
| `POST` | `/reset` | — | `{"status": "ok"}` |
| `GET`  | `/stats` | — | pipeline metadata |

---

## 🔧 Integration recipes

### Use a specific OpenAI model + Qdrant Cloud

```python
from audio_chat import AudioChatPipeline, Settings

settings = Settings(
    openai_api_key="sk-...",
    llm_model="gpt-4o",
    transcription_provider="openai",
    embedding_model="text-embedding-3-large",
    embedding_dim=3072,
    qdrant_url="https://xyz.cloud.qdrant.io",
    qdrant_api_key="...",
    qdrant_collection="my_org_meetings",
)
pipe = AudioChatPipeline(settings)
```

### Override env settings inline

```python
pipe = AudioChatPipeline.from_kwargs(
    llm_model="gpt-4o",
    retrieval_top_k=8,
    chunk_size=1200,
)
```

### Switch transcription to AssemblyAI (for speaker labels)

```python
pipe = AudioChatPipeline.from_kwargs(
    transcription_provider="assemblyai",
    assemblyai_api_key="...",
)
```

### Bring your own embedder / vector store

```python
from audio_chat import Settings, AudioChatPipeline
from audio_chat.vector_store import QdrantStore
from audio_chat.embeddings import build_embedder

settings = Settings.from_env()
embedder = build_embedder(settings)
store = QdrantStore(settings, vector_dim=embedder.dim)
pipe = AudioChatPipeline(settings, embedder=embedder, store=store)
```

---

## ⚙️ Configuration reference

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

## 🛡️ What makes this "industry-grade"?

| Concern | How it's handled |
|---|---|
| **Configuration** | Single env-driven `Settings` dataclass with `.validate()` — fail-fast on missing keys |
| **Error handling** | Typed exception hierarchy (`AudioChatError` → `ConfigurationError`, `TranscriptionError`, `EmbeddingError`, `VectorStoreError`, `LLMError`) |
| **Input validation** | File-size cap, extension whitelist, Whisper 25 MB hard-limit surfaced with a clear message |
| **Observability** | Centralized logger; switch to JSON-line format with `LOG_JSON=true` for ingestion into Datadog/Loki |
| **Deprecations** | Uses Qdrant's current `query_points` API (not the deprecated `search`) |
| **Streaming** | First-class streaming for chat — both UI and HTTP API |
| **Provider lock-in** | Factory pattern (`build_embedder`, `build_transcriber`, `build_llm`) leaves the door open for other providers |
| **Backwards compat** | Old `code_rag` module still works as a thin shim |
| **Tests** | Offline pytest suite — config validator + chunker, 10/10 passing |
| **Reproducible deploy** | Dockerfile with healthcheck + docker-compose with persistent Qdrant volume |
| **Secrets hygiene** | `.env` git-ignored, `.env.example` checked in |

---

## 🧪 Testing

```bash
pip install pytest
pytest -q
```

The default test suite is offline (no API keys needed) — it covers the
config validator and the chunker.

---

## 🐛 Troubleshooting

| Symptom | Fix |
|---|---|
| `ConfigurationError: OPENAI_API_KEY is required` | Set the env var or pass it to `Settings(...)`. |
| `AudioFileTooLargeError` | Whisper has a hard 25 MB limit. Split or compress. Raise `MAX_AUDIO_MB` only after compressing. |
| `VectorStoreError: ... Connection refused` | Either run `docker compose up qdrant`, or fall back to `QDRANT_URL=:memory:`. |
| Embeddings-dim mismatch on a re-used collection | Drop the collection (UI → **Reset index**, or `pipeline.reset_index()`) when changing embedding models. |
| Chat reply is just a `▌` cursor | Almost always a billing/rate-limit issue on the OpenAI key. Check the terminal where Streamlit is running — the exception will be there. The model name (e.g. `gpt-4o-mini`) must also be enabled on your account. |
| Empty `Indexed sources` but you uploaded | Check the terminal for transcription errors; Whisper rejects empty/corrupt audio. |
| Slow first run with HuggingFace embedder | The model is downloaded on first use into `HF_CACHE_DIR`; subsequent runs are fast. |

---

## 🔄 Backwards compatibility

The original [`code_rag.py`](code_rag.py) is preserved as a thin shim that
re-exports the new classes under their old names (`EmbedData`, `QdrantVDB_QB`, `Retriever`, `RAG`, `Transcribe`).
**New code should import from `audio_chat` directly.**

---

## 📄 License

Apache-2.0 — see the root [LICENSE](../LICENSE) of Agent Forge.

---

<div align="center">

🔨 Part of [**Agent Forge**](../README.md) — forging production-ready AI agents, one build at a time.

</div>
