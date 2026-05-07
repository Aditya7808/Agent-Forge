<div align="center">

# 🏠 AI Real Estate Agent Team

### _Multi-Agent Property Search · Deterministic Investment Scoring · Live Market Analytics_

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-1.36+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Agno-Multi--Agent-blueviolet?style=flat-square" />
  <img src="https://img.shields.io/badge/Firecrawl-Extract-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Plotly-Analytics-3F4F75?style=flat-square&logo=plotly&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-History-003B57?style=flat-square&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/License-Apache_2.0-green?style=flat-square" />
</p>

<p>
  <strong>Part of <a href="../README.md">🔨 Agent Forge — 100 Days · 100 AI Agents</a></strong><br/>
  <em>An industry-grade multi-agent system that finds, scores, and benchmarks real-estate listings end-to-end.</em>
</p>

</div>

---

## 📋 Table of Contents

- [Why This Agent](#-why-this-agent)
- [What's New in v2](#-whats-new-in-v2)
- [Architecture](#-architecture)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Investment Scoring Algorithm](#-investment-scoring-algorithm)
- [Analytics Dashboard](#-analytics-dashboard)
- [Caching & History](#-caching--history)
- [Multi-Provider LLM Support](#-multi-provider-llm-support)
- [Testing](#-testing)
- [Roadmap](#-roadmap)

---

## 🎯 Why This Agent

Most "AI real estate" demos do exactly one thing: call an LLM with a property scraper and dump the raw text into a chat window. That's fine for a tutorial, but it produces results that are slow, expensive, non-reproducible, and impossible to compare across runs.

**This project takes a different stance.** It treats real-estate analysis as a *production* workload:

- **Scraping is cached and retried** so duplicate searches are free and transient failures don't kill the run.
- **Ranking is deterministic** — a transparent 0–100 score derived from price/sqft, budget fit, criteria match, and listing completeness. The LLM provides commentary, but the *order* is reproducible.
- **Every analysis is persisted** in SQLite, so you can re-open prior searches without paying for them again.
- **Analytics are computed, not narrated** — Plotly charts driven by real metrics, not hallucinated bullet points.
- **The LLM provider is pluggable** — swap Gemini, OpenAI, Anthropic, or a local Ollama model with a single env var.

---

## ✨ What's New in v2

| Layer | v1 (legacy) | v2 (this version) |
| :---- | :---------- | :---------------- |
| **Code structure** | 2 monolithic 800-line scripts (~95% duplicated) | Modular `src/real_estate/` package (config, schemas, services, agents, analytics, exporters, UI) |
| **LLM providers** | Hard-coded Gemini *or* hard-coded Ollama | Unified `LLMHandle` factory — Gemini · OpenAI · Anthropic · Ollama via env var |
| **Reliability** | One-shot Firecrawl call; failures bubble up | Retries with exponential backoff, normalized response handling, file-based cache (6h TTL) |
| **Ranking** | Sort order = whatever the LLM emits | Deterministic 0–100 investment score (price/sqft vs. market median, budget fit, criteria match, completeness) |
| **Analytics** | None | 6 Plotly charts (price dist, $/sqft by type, score dist, beds×price scatter, source mix, type pie) + summary metrics |
| **Persistence** | None | SQLite search history; reload, delete, re-export prior runs |
| **Exports** | Single Markdown blob | Markdown · JSON · CSV |
| **Configuration** | Scattered `os.getenv` calls | Single Pydantic `Settings` + `.env.example` |
| **Logging** | `print()` | Structured logging (text or JSON) with quieted third-party loggers |
| **Tests** | None | `pytest` suite for URL builder + scoring algorithm |
| **IDE support** | None | `pyrightconfig.json` with `extraPaths` for `src/` |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                       AI REAL ESTATE AGENT TEAM                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────┐     ┌──────────────┐      ┌──────────────────────┐   │
│  │  STREAMLIT   │     │   PIPELINE   │      │   LLM PROVIDERS      │   │
│  │              │     │              │      │                      │   │
│  │ • Search     │────▶│ 1. Firecrawl │◀────▶│  Gemini 2.5 Flash    │   │
│  │ • Analytics  │     │ 2. Scoring   │      │  OpenAI gpt-4o-mini  │   │
│  │ • Compare    │     │ 3. Market    │      │  Claude Haiku 4.5    │   │
│  │ • History    │     │ 4. Valuation │      │  Ollama (local)      │   │
│  │ • Export     │     │              │      │                      │   │
│  └──────────────┘     └──────┬───────┘      └──────────────────────┘   │
│                              │                                         │
│         ┌────────────────────┴─────────────────────┐                   │
│         ▼                                          ▼                   │
│  ┌──────────────────┐                     ┌─────────────────────┐      │
│  │ FIRECRAWL CACHE  │                     │  SQLITE HISTORY     │      │
│  │  (.cache/)       │                     │  (history.sqlite3)  │      │
│  │  6h TTL · SHA256 │                     │  Indexed · JSON     │      │
│  └──────────────────┘                     └─────────────────────┘      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Multi-Agent Flow

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Property Search │     │  Market Analysis │     │ Property Valuation│
│   (Firecrawl)    │ ──▶ │      Agent       │ ──▶ │       Agent       │
│   + Scoring      │     │ (LLM-grounded)   │     │ (LLM, per-listing)│
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                          │                          │
        ▼                          ▼                          ▼
   Structured                 Concise market              Per-property
   listings + 0-100           insight bullets             value assessment
   investment score
```

---

## 🚀 Features

### 🤖 Multi-Agent Pipeline

- **Property Search** — direct Firecrawl extraction with normalized response handling
- **Market Analysis Agent** — concise, bullet-form market commentary (≤100 words/section)
- **Property Valuation Agent** — fixed-format per-property assessments

### 🧮 Deterministic Investment Scoring

A transparent 0–100 score blended from four signals:

| Signal | Weight | What it measures |
| :----- | :----: | :--------------- |
| Price / sqft vs. market median | 35% | Pure value compared to in-search comps |
| Budget fit | 25% | How close to the user's sweet spot (~70% of max budget) |
| Criteria match | 25% | Beds, baths, sqft, property type alignment |
| Listing completeness | 15% | Penalizes thin listings missing key fields |

→ Bands: **High (≥75) · Medium (≥55) · Low (≥30) · Unrated (<30)**

### 📊 Analytics Dashboard

- Price distribution histogram
- Price-per-sqft box plot per property type
- Property type mix (donut)
- Investment score distribution with band thresholds
- Bedrooms × price scatter (color-coded by score)
- Source comparison bar chart
- Raw metrics JSON for inspection

### 🆚 Side-by-Side Comparison

Pick up to 4 properties and compare price, $/sqft, score, beds/baths, and listing links in a single view.

### 📥 Exports

- **Markdown** — human-readable report (default)
- **JSON** — full structured result for downstream tools
- **CSV** — flat sheet of scored properties for Excel/Sheets

### 📜 Search History

Every successful analysis is persisted to SQLite with:
- Reload prior runs (no re-paying for Firecrawl + LLM)
- Delete individual entries
- Indexed by city + timestamp

### ⚡ Performance

- **File-based Firecrawl cache** keyed by `sha256(urls + criteria)` with configurable TTL
- **Exponential backoff** retries (1, 2, 4, 8s) on transient errors
- **Lazy provider imports** — install only the LLM SDKs you actually use
- **Logging quieted** for `httpx`, `urllib3`, `openai`, `anthropic` to keep stdout readable

### 🌐 Multi-Source

Searches across **Zillow · Realtor.com · Trulia · Homes.com** in a single run.

---

## 📂 Project Structure

```
AI Real Estate Agent Team/
├── ai_real_estate_agent_team.py         # Cloud entry (Gemini/OpenAI/Anthropic)
├── local_ai_real_estate_agent_team.py   # Local entry (Ollama)
├── requirements.txt
├── .env.example
├── pyrightconfig.json
├── README.md
│
├── src/
│   └── real_estate/
│       ├── __init__.py
│       ├── config.py                # Pydantic Settings + structured logging
│       ├── schemas.py               # PropertyDetails, SearchCriteria, AnalysisResult, ScoredProperty
│       ├── firecrawl_service.py     # Retry + cache + URL builder
│       ├── llm_factory.py           # Unified provider factory (Gemini/OpenAI/Anthropic/Ollama)
│       ├── prompts.py               # Centralized agent personas + prompt templates
│       ├── pipeline.py              # 4-stage pipeline orchestration
│       ├── scoring.py               # Deterministic 0-100 investment score
│       ├── analytics.py             # Metrics + Plotly chart factories
│       ├── history.py               # SQLite-backed search history
│       ├── exporters.py             # Markdown / JSON / CSV
│       └── ui.py                    # Streamlit views (search, results, analytics, compare, history)
│
└── tests/
    ├── conftest.py
    ├── test_url_builder.py          # URL construction + budget formatting
    └── test_scoring.py              # Investment scoring edges
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Notes |
| :---------- | :-----: | :---- |
| Python      | ≥ 3.10  | |
| Firecrawl   | API key | https://firecrawl.dev |
| LLM         | Pick one | Gemini · OpenAI · Anthropic · or Ollama (local) |

### Cloud version (Gemini · OpenAI · Anthropic)

```bash
# 1. Clone and enter the agent folder
cd "AI Real Estate Agent Team"

# 2. Create a virtual env
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env       # then edit .env

# 5. Launch
streamlit run ai_real_estate_agent_team.py
```

### Local version (Ollama)

```bash
# 1. Pull a model (16GB RAM recommended for gpt-oss:20b; smaller models work too)
ollama pull gpt-oss:20b
ollama serve

# 2. Same setup as above, then:
streamlit run local_ai_real_estate_agent_team.py
```

---

## ⚙️ Configuration

All configuration is centralized in [`src/real_estate/config.py`](src/real_estate/config.py) and driven by environment variables (load from `.env`).

| Variable | Default | Purpose |
| :------- | :-----: | :------ |
| `FIRECRAWL_API_KEY` | — | **Required.** Property extraction. |
| `REAL_ESTATE_LLM_PROVIDER` | `gemini` | One of `gemini` · `openai` · `anthropic` · `ollama` |
| `GOOGLE_API_KEY` | — | For `gemini` provider |
| `OPENAI_API_KEY` | — | For `openai` provider |
| `ANTHROPIC_API_KEY` | — | For `anthropic` provider |
| `GEMINI_MODEL` | `gemini-2.5-flash` | |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | |
| `OLLAMA_MODEL` | `gpt-oss:20b` | |
| `OLLAMA_HOST` | `http://localhost:11434` | |
| `REAL_ESTATE_CACHE` | `1` | `0` to disable Firecrawl cache |
| `REAL_ESTATE_CACHE_TTL` | `21600` | Seconds (6h default) |
| `REAL_ESTATE_CACHE_DIR` | `.cache/real_estate` | Cache directory |
| `REAL_ESTATE_HISTORY_DB` | `.cache/real_estate/history.sqlite3` | SQLite history file |
| `FIRECRAWL_TIMEOUT` | `120` | Seconds |
| `FIRECRAWL_MAX_RETRIES` | `3` | Backoff: 1, 2, 4, 8s |
| `LOG_LEVEL` | `INFO` | |
| `LOG_JSON` | `0` | `1` for JSON-formatted logs |

---

## 📖 Usage Guide

1. **Configure keys in the sidebar** (or set them in `.env` ahead of time).
2. **Pick search sources** — at minimum one of Zillow / Realtor.com / Trulia / Homes.com.
3. **Fill the search form** — city, optional state, budget, beds/baths, sqft, features.
4. **Hit `Start Property Analysis`** — progress is reported live as agents complete.
5. **Explore the result tabs:**
   - **🏠 Properties** — sortable, filterable cards with score breakdown
   - **📊 Analytics** — six interactive Plotly charts
   - **📈 Market & Valuation** — LLM-generated commentary
   - **🆚 Compare** — pick up to 4 listings to benchmark side-by-side
   - **📥 Export** — download Markdown, JSON, or CSV
6. **Reload prior runs** from the **📜 History** page in the sidebar.

---

## 🧮 Investment Scoring Algorithm

Implemented in [`src/real_estate/scoring.py`](src/real_estate/scoring.py).

```
score = 35 · ppsf_component
      + 25 · budget_fit_component
      + 25 · criteria_match_component
      + 15 · completeness_component
```

| Component | How it's computed |
| :-------- | :---------------- |
| **ppsf_component** | Compare each listing's $/sqft to the in-search median. ≤0.7× median → 1.0; 1.0× → 0.6; ≥1.5× → 0.0 |
| **budget_fit_component** | Sweet spot at ~70% of max budget. Below budget → 0.6 (could indicate stale listing). Over budget → drops linearly. |
| **criteria_match_component** | Hard checks on bedrooms/bathrooms/sqft/property type; each violation reduces the soft score and may flag `matches_criteria=False`. |
| **completeness_component** | Fraction of (price, beds, baths, sqft, type, listing_url, description) that are filled. |

**Why deterministic?** LLM-based ranking changes between runs. With this approach you can re-run the same query and get the same ordering — making it possible to track price/sqft trends over time and trust comparisons.

---

## 📊 Analytics Dashboard

Implemented in [`src/real_estate/analytics.py`](src/real_estate/analytics.py). Six Plotly charts are rendered when there's enough signal in the data:

| Chart | What it shows |
| :---- | :------------ |
| **Price Distribution** | Histogram across all extracted listings |
| **$/sqft by Property Type** | Box plot — spot which segment is over- or under-priced |
| **Property Type Mix** | Donut chart of inventory composition |
| **Investment Score Distribution** | Histogram with `High (75)` and `Medium (55)` threshold lines |
| **Beds × Price Scatter** | Color-coded by investment score (Viridis) |
| **Listings by Source** | Where the listings came from |

Charts are skipped when there aren't enough data points — no empty placeholders.

---

## 💾 Caching & History

### Firecrawl cache

- **Key:** `sha256(sorted_urls + serialized_criteria)`
- **Location:** `.cache/real_estate/firecrawl_<key>.json`
- **TTL:** 6 hours (configurable)
- **Bypass:** toggle off in the sidebar or set `REAL_ESTATE_CACHE=0`

### Search history (SQLite)

- **Schema:** `searches(id, timestamp, city, state, budget_min, budget_max, total_properties, avg_score, elapsed_seconds, provider, model, payload)`
- **Indexes:** by `timestamp DESC` and `city`
- **Reload:** the History page rebuilds full `AnalysisResult` objects from the JSON payload column — no Firecrawl/LLM calls.

---

## 🔌 Multi-Provider LLM Support

Switch providers with one env var:

```bash
# Use OpenAI
REAL_ESTATE_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Use Anthropic Claude
REAL_ESTATE_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Stay local with Ollama (run local entry script)
streamlit run local_ai_real_estate_agent_team.py
```

The provider factory in [`src/real_estate/llm_factory.py`](src/real_estate/llm_factory.py) lazy-imports each Agno model class, so unused providers don't have to be installed.

---

## 🧪 Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Coverage:

- **`test_url_builder.py`** — URL construction across all four sources, edge cases (missing state, multi-word city, budget formatting)
- **`test_scoring.py`** — investment-score determinism, budget bands, criteria filtering, score bounds (0..100)

---

## 🗺️ Roadmap

- [ ] Add a Folium map view (cluster markers, color by score)
- [ ] Mortgage estimator (PITI, principal, interest, taxes, insurance) per property
- [ ] Cold-call email drafting agent — pre-filled outreach to listing agents
- [ ] Image quality analysis (cover photo scoring)
- [ ] Schedule recurring searches (Streamlit + APScheduler) and email diffs

---

<div align="center">

**Part of [Agent Forge — 100 Days · 100 AI Agents](../README.md)**

🔨 _Forging production-ready AI agents, one build at a time — no finish line._ 🔨

</div>
