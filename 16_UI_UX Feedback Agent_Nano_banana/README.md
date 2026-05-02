<div align="center">

# 🎨 🍌 UI/UX Feedback Agent Team

### *A Five-Specialist Design Review Crew Powered by Gemini 2.5 + Nano Banana*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google&logoColor=white)](#)
[![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-1a73e8?logo=googlegemini&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.34%2B-FF4B4B?logo=streamlit&logoColor=white)](#)
[![WCAG 2.2](https://img.shields.io/badge/WCAG-2.2%20AA-2ea44f)](#)

**Drop a screenshot. Get a senior-designer critique, a build-ready spec, an accessibility audit, A/B hypotheses, and a redesigned mockup — in one conversation.**

[Quick Start](#-quick-start) · [Agents](#-meet-the-team) · [Workflows](#-workflows) · [Tools](#%EF%B8%8F-built-in-tools) · [Architecture](#-architecture) · [Tips](#-pro-tips)

</div>

---

## ✨ What's New in This Version

| Upgrade | Why it matters |
|---|---|
| 🧑‍🎨 **5 specialists** instead of 3 | Adds a dedicated WCAG accessibility auditor and a CRO optimizer with A/B test hypotheses. |
| 🎯 **Coordinator routing** | Smart intent detection — uploaded screenshot? full pipeline. "make CTA bigger"? straight to the editor. |
| 🌗 **Streamlit UI** | One-click full audit, drag-and-drop upload, inline image gallery, downloads, color-contrast checker in the sidebar. |
| 📊 **Built-in WCAG calculator** | Real WCAG 2.2 contrast math, not vibes. Verdicts for AA / AAA at body / large / UI sizes. |
| 🆚 **Side-by-side comparison** | Compare any two versions of an asset and get a scored verdict. |
| 📄 **Markdown report export** | Save the full session — analysis, strategy, and version history — to disk. |
| 🗂️ **Version history** | Every iteration is tracked with timestamps. |
| 🧱 **Centralized prompts** | `prompts.py` keeps personas swappable; `agent.py` stays a thin orchestrator. |

---

## 🚀 Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Add your key
cp .env.example .env          # then edit .env

# 3a. Launch the interactive Streamlit UI (recommended)
streamlit run app.py

# 3b. Or use Google's ADK Web UI
adk web
```

> **Need a key?** Grab a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey) and drop it into `.env`.

---

## 👥 Meet the Team

```
                    ┌────────────────────────────┐
                    │    🧭  Coordinator          │   ← you talk to this one
                    └──────────────┬──────────────┘
                                   │ routes by intent
        ┌──────────────────────────┼──────────────────────────┐
        │             │            │             │            │
   ┌────▼────┐  ┌─────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │ ℹ️ Info │  │ 🎨 Critic │  │ 📐 Strat │  │ 🚀 Impl. │  │ ♻️ Editor│
   │  Agent  │  │           │  │ Strategist│  │          │  │          │
   └─────────┘  └─────┬─────┘  └─────┬────┘  └────┬─────┘  └──────────┘
                      └────────►───┬─┴──────►─────┘
                                   │ Sequential Pipeline
                  ┌────────────────┼────────────────┐
                  │                                 │
            ┌─────▼──────┐                  ┌───────▼────────┐
            │ ♿ A11y     │                  │ 📈 CRO         │
            │ Auditor    │                  │ Optimizer      │
            └────────────┘                  └────────────────┘
```

| Agent | What it does |
|---|---|
| 🧭 **Coordinator** | Routes user intent. One sentence ack, then dispatch. |
| 🎨 **UI Critic** | 8-dimension scored critique with first-impression read and conversion-funnel walkthrough. |
| 📐 **Design Strategist** | Build-ready spec: design tokens, hex codes, type scale, priority matrix, responsive breakpoints. |
| 🚀 **Visual Implementer** | Generates the redesigned mockup with Gemini 2.5 image gen + a markdown change log. |
| ♻️ **Design Editor** | Tweaks an existing generation: "make the CTA orange", "add testimonials", "more like Linear". |
| ♿ **Accessibility Auditor** | WCAG 2.2 verdict — perceivable / operable / understandable / robust. Estimates Lighthouse score. |
| 📈 **Conversion Optimizer** | Funnel audit + 3 A/B test hypotheses with success metrics and lift estimates. |
| ℹ️ **Info Agent** | Friendly front desk for general questions and onboarding. |

---

## 🎬 Workflows

### 🔍 Workflow 1 — Full Audit
> *"Here's our pricing page. Critique, redesign, audit accessibility."*

```
Coordinator → Analysis Pipeline (Critic → Strategist → Implementer)
            → Accessibility Auditor (deep dive)
            → exported markdown report
```

### ⚡ Workflow 2 — Quick Critique
> *"Just tell me what's wrong. No redesign yet."*

```
Coordinator → UI Critic only → 8-dim scored report
```

### 🎨 Workflow 3 — Iterative Refinement
> *"Looks good but make the CTA orange and add social proof."*

```
Coordinator → Design Editor → edit_landing_page_image → v2 saved
            → "Compare v1 vs v2?" → side-by-side scorecard
```

### 📈 Workflow 4 — Conversion-First Review
> *"Forget aesthetics, what's killing my conversion rate?"*

```
Coordinator → Conversion Optimizer → friction audit + 3 A/B hypotheses
```

---

## 🛠️ Built-in Tools

| Tool | Purpose |
|---|---|
| `generate_improved_landing_page` | Brand-new improved design via Gemini 2.5 Flash image gen. |
| `edit_landing_page_image` | Refine an existing artifact with a natural-language prompt. |
| `compare_versions` | Side-by-side narrative diff with a scored verdict between any two versions. |
| `list_versions` | Markdown table of every asset and version in the session. |
| `export_design_report` | Persist the session — analysis, strategy, history — to a `.md` file in `./reports`. |
| `estimate_color_contrast` | Real WCAG 2.2 math (sRGB relative luminance + ratio) with AA/AAA verdict. |
| `google_search` | Live UI/UX trend lookups (used by Critic, Strategist, A11y, CRO). |

---

## 🏗️ Architecture

```
16_UI_UX Feedback Agent_Nano_banana/
├── agent.py            ← orchestration: coordinator + 5 specialists + sequential pipeline
├── prompts.py          ← all agent personas in one place (versionable, swappable)
├── tools.py            ← 6 tools: generate, edit, compare, list, export, contrast
├── app.py              ← Streamlit UI with quick-action buttons + chat
├── __init__.py         ← exposes root_agent
├── requirements.txt
└── .env.example
```

### Why this structure?
- **Thin agents, fat prompts.** `agent.py` is just wiring. Iterate personas in `prompts.py`.
- **Shared state, not shared knowledge.** Agents publish to ADK state (`latest_analysis`, `latest_strategy`, `current_asset_name`); downstream agents read from there.
- **Vision-native.** Critic / strategist / implementer all use `gemini-2.5-flash` and see uploaded images directly — no manual image-analysis tool needed.

---

## 💡 Pro Tips

> **Use full-page screenshots.** Above-the-fold only forces the critic to guess.

> **Pin your audience.** *"This is a B2B SaaS targeting CFOs"* unlocks far better critique than a bare upload.

> **Iterate one axis at a time.** Color → typography → CTA → layout. Mixing them makes diffs unreadable.

> **Trust the priority matrix.** Strategist orders changes by impact/effort. P0s alone usually buy 60% of the lift.

> **Compare often.** After every 2–3 edits, ask `compare v3 vs v5` to catch regressions early.

---

## 🧪 Example Conversation

```text
You:        [uploads screenshot]
            Run a full audit. B2B target, conversion-focused.

Coordinator: Routing to the analysis pipeline.

UI Critic:   ### 🎯 First Impression (5/10)
            Cluttered hero, three competing CTAs above the fold…
            **Overall Score: 5.4/10**

Strategist:  ### 🎨 Design Tokens
            Primary: #0A2540 · Accent: #FF6B35 · Body: Inter 16/24…
            ### 🎯 Priority Matrix
            | P0 | Single hero CTA | High | Low |

Implementer: ✅ Improved landing page generated! Saved as
            landing_page_improved_v1.png

You:        Try a darker palette and bigger headline.

Coordinator: Routing to the design editor.

Editor:     ✅ Saved as landing_page_improved_v2.png. v2 swaps the hero
            background to #08111E and bumps H1 from 48px to 64px.

You:        Compare v1 and v2.

Editor:     ### 🔍 What Changed
            - Hero background: #FFFFFF → #08111E (full inversion)
            - H1 size: 48px → 64px (+33%)
            - CTA contrast ratio: 4.1 → 8.7 (now AAA)
            ### 🏆 Verdict
            v2 is stronger for night-mode users…
```

---

## 🧰 Troubleshooting

<details>
<summary><b>“GEMINI_API_KEY not set”</b></summary>

Either your `.env` is missing or wasn’t loaded. Run `cp .env.example .env`, fill it in, then restart Streamlit / `adk web`.
</details>

<details>
<summary><b>Image generation returned no image</b></summary>

The Nano Banana model occasionally drops a frame on vague prompts. Re-run, or make the request more specific (mention sections, colors, copy).
</details>

<details>
<summary><b>“Could not find artifact …_v3.png”</b></summary>

Versioning is per-session. If you reset the chat, prior artifacts disappear. Use `export_design_report` before resetting if you need to keep the history.
</details>

<details>
<summary><b>Streamlit can’t import <code>google.adk</code></b></summary>

Run `pip install -r requirements.txt` in the same Python environment Streamlit is using. On Windows, `where streamlit` and `where python` should resolve to the same `Scripts/` folder.
</details>

---

## 🗺️ Roadmap

- [ ] Heatmap overlay (predicted attention from the critic)
- [ ] Component-level extraction (auto-tokenize colors and fonts from the upload)
- [ ] CSV export of A/B hypotheses for direct paste into experimentation tools
- [ ] Streaming responses in the Streamlit UI
- [ ] Side-by-side image render in `compare_versions` output

---

<div align="center">

**Built as Day 16 of [100 Days · 100 AI Agents](../README.md).**

🍌 *Nano Banana = the Gemini 2.5 Flash image-generation model.*

</div>
