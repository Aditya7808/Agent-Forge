# ClauseAI Streamlit App

Industry-grade contract analysis built on **LangGraph + OpenAI**. Same workflow as the [`ClauseAI.ipynb`](../ClauseAI.ipynb) notebook, wrapped in a production-ready multi-tab UI with streaming progress, risk dashboards, redline export, and grounded Q&A chat.

## Features

| Tab            | What you get |
| -------------- | ------------ |
| 📤 Upload      | PDF / DOCX / TXT / MD upload, sample contract, primary objective and focus |
| 🚀 Run         | One-click analysis with live per-node progress and token/cost telemetry |
| 📊 Dashboard   | Top-line metrics, risk distribution, compliance status, top findings |
| 🧾 Entities    | Parties, financial terms, key dates, obligations |
| 📝 Modifications | Filterable redline list with original / suggested / risk level |
| ✅ Compliance & Gaps | Compliance findings, missing clauses, internal conflicts, PII flags |
| 📄 Report      | Full markdown report |
| 💬 Chat        | Grounded Q&A over the contract + analysis JSON |
| ⬇️ Export      | Markdown, JSON, DOCX, redlined DOCX downloads |

## Architecture

```
┌─ classify ─┬─ extract_entities ──┐
            ├─ detect_pii ─────────┤
            ├─ retrieve_clauses ─→ check_clause (parallel fan-out via Send)
            ├─ missing_clauses ────┤
            ├─ detect_conflicts ───┤
            ├─ compliance ─────────┤
            └─ review_plan ──→ role_review (parallel fan-out via Send)
                                   ↓
                            aggregate_risk → final_report → END
```

All heavy branches run in **parallel** via LangGraph's `Send` map-reduce, dramatically reducing wall-clock time.

## Project layout

```
streamlit_app/
├── app.py                  # Entrypoint
├── config.py               # Env-driven settings
├── requirements.txt
├── .env.example
├── .streamlit/config.toml
├── core/
│   ├── state.py            # Pydantic schemas + LangGraph TypedDict
│   ├── nodes.py            # All graph nodes (classify, extract, compliance, etc.)
│   ├── graph.py            # Builds the LangGraph + run_analysis() helper
│   ├── reporter.py         # Markdown + JSON report generator
│   ├── retrievers.py       # FAISS-backed clause retriever
│   ├── exporters.py        # DOCX redline / report exporters
│   ├── chat.py             # Grounded Q&A
│   └── utils.py            # File parsing, sectioning
├── prompts/
│   └── prompts.py          # Centralized prompts — tune behavior here
└── ui/
    ├── sidebar.py
    ├── components.py       # Risk badges, charts
    └── views.py            # Tab views
```

## Setup

```bash
cd "Contract Analysis/streamlit_app"
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

## Run

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (default `http://localhost:8501`).

## Configuration

All settings can come from environment variables (or `.env`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | _required_ | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Primary model for most nodes |
| `OPENAI_MODEL_STRONG` | `gpt-4o` | Strong model for compliance + conflict detection |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for FAISS |
| `LLM_TEMPERATURE` | `0` | Determinism vs creativity |
| `CLAUSES_PATH` | `../data/clauses.json` | Reference clause library |
| `COMPLIANCE_FRAMEWORKS` | `GDPR,CCPA` | Frameworks to evaluate |
| `MAX_CLAUSE_CHECKS` | `12` | How many reference clauses to compare in parallel |

## Extending

- **Add a clause type:** edit [`../data/clauses.json`](../data/clauses.json). It is reloaded on app start.
- **Tune behavior:** edit [`prompts/prompts.py`](prompts/prompts.py).
- **Add a new node:** add a function in [`core/nodes.py`](core/nodes.py), expose it via `make_nodes`, then wire it into [`core/graph.py`](core/graph.py).
- **Swap vector backend:** [`core/retrievers.py`](core/retrievers.py) currently uses FAISS. Replace with Pinecone/Weaviate/etc. behind the same interface (`by_contract_type`, `similarity`, `expected_clause_titles`).

## Notes

- The OpenAI key entered in the sidebar is **session-only**. For persistence put it in `.env`.
- Token cost is reported per run via `langchain_community.callbacks.get_openai_callback`.
- `MemorySaver` is used as the LangGraph checkpointer; for multi-user production deployments swap in `SqliteSaver` or `PostgresSaver`.
