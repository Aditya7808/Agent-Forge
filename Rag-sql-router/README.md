# RAG + SQL Router: Intelligent Hybrid Query Engine

A production-grade AI agent that intelligently routes natural language queries between a **SQL database** and a **RAG (Retrieval-Augmented Generation) pipeline** — with built-in response validation and trust scoring via Cleanlab Codex.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?logo=react&logoColor=black)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?logo=tailwindcss&logoColor=white)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React + Tailwind UI                     │
│         (Chat Interface, Database Explorer, Upload)       │
└───────────────────────────┬─────────────────────────────┘
                            │ REST API
┌───────────────────────────▼─────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Intelligent Query Router                │   │
│  │         (GPT-4o-mini Classification)              │   │
│  └──────────┬──────────────────────┬────────────────┘   │
│             │                      │                     │
│  ┌──────────▼──────────┐  ┌───────▼────────────────┐   │
│  │    SQL Engine        │  │    RAG Engine           │   │
│  │  • NL → SQL Gen     │  │  • ChromaDB Vectors     │   │
│  │  • SQLite Query      │  │  • OpenAI Embeddings    │   │
│  │  • Response Synth    │  │  • Context Retrieval    │   │
│  └─────────────────────┘  │  • Answer Generation    │   │
│                            └───────────┬────────────┘   │
│                                        │                 │
│                            ┌───────────▼────────────┐   │
│                            │  Cleanlab Codex         │   │
│                            │  Trust Scoring          │   │
│                            └────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Key Features

- **Intelligent Routing** — GPT-4o-mini classifies queries and routes them to the optimal engine (SQL or RAG) automatically
- **Text-to-SQL** — Converts natural language to SQL queries against a city statistics database
- **RAG Pipeline** — Upload documents (PDF, DOCX, PPTX, TXT) and ask questions with semantic search
- **Trust Scoring** — Cleanlab Codex validates RAG responses with trustworthiness metrics
- **Modern UI** — Dark-themed React frontend with real-time chat, database explorer, and interactive charts
- **Production API** — FastAPI backend with proper error handling, validation, and CORS support

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | OpenAI GPT-4o-mini |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Vector Store** | ChromaDB (persistent, local) |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | React 18 + Tailwind CSS + Recharts |
| **Database** | SQLite (city statistics) |
| **Validation** | Cleanlab Codex |
| **Build Tool** | Vite |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key

### 1. Clone & Install Backend

```bash
cd Rag-sql-router

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

```env
OPENAI_API_KEY=sk-your-key-here
CODEX_API_KEY=your-codex-key-here  # Optional
```

### 3. Start Backend

```bash
python run.py
```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### 4. Install & Start Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat/` | Send a query (auto-routed to SQL or RAG) |
| `POST` | `/api/documents/upload` | Upload documents for RAG |
| `GET` | `/api/database/stats` | Get database statistics |
| `GET` | `/api/database/data` | Get all city data |
| `POST` | `/api/database/query` | Run custom SQL query |
| `GET` | `/api/health` | Health check |

### Example Request

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the population of Houston, Texas?"}'
```

### Example Response

```json
{
  "response": "Houston, Texas has a population of 2,304,580.",
  "route_used": "sql",
  "trust_score": null,
  "sql_query": "SELECT population FROM city_stats WHERE city_name = 'Houston' AND state = 'Texas'",
  "metadata": {"data": [{"population": 2304580}]}
}
```

## How the Router Works

1. **Query Classification** — The router uses GPT-4o-mini with a specialized system prompt to classify incoming queries into `sql` or `rag` categories based on intent

2. **SQL Path** — For city/population queries:
   - Generates SQL from natural language
   - Executes against SQLite database
   - Synthesizes a human-readable response

3. **RAG Path** — For document queries:
   - Retrieves top-k relevant chunks from ChromaDB
   - Generates an answer grounded in the retrieved context
   - Validates the response through Cleanlab Codex for trust scoring

## Project Structure

```
Rag-sql-router/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and settings
│   ├── models.py            # Pydantic request/response schemas
│   ├── routes/
│   │   ├── chat.py          # Chat endpoint (routing logic)
│   │   ├── documents.py     # Document upload & processing
│   │   └── database.py      # Database exploration endpoints
│   ├── services/
│   │   ├── router.py        # Query classification (SQL vs RAG)
│   │   ├── sql_engine.py    # Natural language to SQL
│   │   ├── rag_engine.py    # RAG pipeline (ChromaDB + OpenAI)
│   │   └── trust_scorer.py  # Cleanlab Codex integration
│   └── data/
│       └── city_database.sqlite
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main application
│   │   ├── api.js           # API client
│   │   ├── components/      # React components
│   │   └── hooks/           # Custom hooks
│   ├── package.json
│   └── vite.config.js
├── notebook.ipynb           # Development notebook
├── requirements.txt
├── run.py                   # Backend start script
└── .env.example
```

## Trust Scoring

When documents are uploaded and RAG is used, responses include a trust score powered by Cleanlab Codex:

- **70-100%** (High Trust) — Response is well-grounded in the source documents
- **50-69%** (Medium Trust) — Response may have some unsupported claims
- **Below 50%** (Low Trust) — Response may be unreliable; system may apply guardrails

## Development

### Backend Development

```bash
# Run with auto-reload
python run.py

# API docs available at http://localhost:8000/docs
```

### Frontend Development

```bash
cd frontend
npm run dev    # Dev server with HMR
npm run build  # Production build
```

## License

MIT
