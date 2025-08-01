# QaAI – INITIAL.md
*A Harvey-style, DIFC-focused legal AI demo built with free/low-cost tooling. Frontend in React; backend in FastAPI with LangChain + LangGraph. Uses OpenAI + Anthropic APIs (no fine-tuning).*

---

FEATURE:

- **Assistant surface (two modes)**  
  - *Assist Mode:* quick answers, multi‑file Q&A, summaries, comparisons, and tables with **visible “thinking states.”**  
  - *Draft Mode:* structured outputs (memos, contracts, filings) with an **in‑app draft editor** (revise/compare before export).  
  - **Knowledge sources:** query **Vault projects** + DIFC/DFSA corpora; always **return citations**.

- **Vault (projects & review)**  
  - Projects hold documents; *demo target:* hundreds of files (UI copy shows “up to 10,000”).  
  - **Review Tables** with typed columns (date/currency/verbatim/quote).  
  - **One‑Click Workflows** run over an entire project (e.g., deal‑point extraction).  
  - **Assistant ↔ Vault linking:** query a Vault from Assistant and **save Assistant outputs back to Vault**.

- **Workflows (agentic, guided, transparent)**  
  - **Draft from Template (DIFC)**: upload `.docx` template + references → redlined draft + citations; steps show **thinking states**.  
  - **DIFC Data Protection Check (DPL 2020)**: checklist-style analysis for startups (non‑legal‑advice).  
  - **Employment Basics (DIFC Law No. 2 of 2019)**: starter offer/contract + compliance pointers.  
  - **Gallery** entries (Translate, Proofread, Timeline) to match the Assistant “Discover” area.

- **Agent orchestration (LangGraph over LangChain)**  
  - Deterministic, inspectable graph:  
    `preflight → plan → retrieve(jurisdiction=DIFC) → analyze_draft → verify_citations → human_review → export`.  
  - Per‑step **model routing** (reasoning vs drafting vs verification) and **retry/fallback** policies.

- **Models (API only; Plus subscriptions)**  
  - **OpenAI:** `gpt-4.1` (primary drafting/QA), `o1` (planner/reasoning), `o3` (verification/cheap steps).  
  - **Anthropic:** `claude-3.7-sonnet` (long-context reasoning/drafting).  
  - **Manual model override** toggle in UI + logging of token usage.

- **RAG & data (free/near‑free)**  
  - **Local FS** storage for files (`/data`).  
  - **SQLite** for metadata.  
  - **FAISS** on disk for vectors (default).  
  - Optional **Supabase** (free tier) for Postgres + pgvector + auth (switch via env).

- **Citations & verification (MVP)**  
  - Attach source list with URLs/section refs.  
  - Lightweight *Knowledge Source ID* check: parse citation → retrieve candidates → **LLM binary match**.

- **UI design system**  
  - React + Tailwind + shadcn/ui using **the JSON design profiles** (Assistant, Vault, Workflow) provided in this chat as the **single source of truth** for tokens (colors/spacing/radii/typography), components, and layout.

- **Jurisdiction awareness (DIFC-first)**  
  - Retrieval boosts **DIFC Laws/Regulations**, **DIFC Courts Rules**, **DFSA Rulebook**.  
  - UI **Knowledge Source Picker** defaults to DIFC sources (toggle on/off).  
  - All outputs include a **non‑legal‑advice** disclaimer.

- **API surface (initial)**  
  - `POST /api/assistant/query`  → SSE stream (Assist/Draft; accepts files + knowledge filters).  
  - `POST /api/vault/projects` • `GET /api/vault/projects`  
  - `POST /api/vault/:id/upload` • `GET /api/vault/:id/search`  
  - `POST /api/workflows/draft-from-template/run` → SSE thinking states + artifact link  
  - `GET /api/workflows/runs/:id` (status, citations, artifacts)  
  - `POST /api/ingest` (batch ingest for DIFC/DFSA PDFs/HTML)

- **Dev constraints**  
  - Free/near‑free infra; local‑first; no training on user data; logs redacted; simple auth (Supabase magic link) or demo “no‑auth” mode.

---

EXAMPLES:

- In the **`examples/`** folder, there is a **README** explaining each demo and how to structure future examples for this project.
- 'examples/design/assistant.profile.json' — Assistant design profile (tokens + structure)
- 'examples/design/vault.profile.json' — Vault design profile
- 'examples/design/workflow.draft-from-template.profile.json' — Workflow (Draft from Template) design profile
- How to use: Frontend should load these JSONs and map core tokens to CSS vars. Do not hard‑code colors/spacing.
- `examples/assistant_run.py` — minimal call into `POST /api/assistant/query` with SSE, showing **Assist** mode over local files.  
- `examples/rag_ingest.py` — ingest a handful of **DIFC/DFSA** PDFs/HTML into FAISS + SQLite with metadata (`jurisdiction`, `instrument_type`, `section_ref`, dates).  
- `examples/workflow_draft_from_template.graph.py` — a **LangGraph** sketch of the “Draft from Template (DIFC)” workflow (nodes, edges, retries, per‑step model hints).  
- `examples/citations_check.py` — demonstrates the **binary match** verification step on a small citation set.  


> Don’t copy examples from other projects directly; use these as **inspiration** and to enforce **best practices** for this repo (graph structure, SSE streaming, citations, and UI token use).

---

DOCUMENTATION:

- **LangChain:** https://python.langchain.com/  
- **LangGraph:** https://langchain-ai.github.io/langgraph/  
- **OpenAI API:** https://platform.openai.com/docs/  
- **Anthropic API:** https://docs.anthropic.com/  
- **FastAPI:** https://fastapi.tiangolo.com/  
- **FAISS:** https://faiss.ai/  
- **Supabase (optional):** https://supabase.com/docs

*(DIFC/DFSA primary materials will be ingested locally for RAG; link lists for engineers can live in `docs/SOURCES.md`.)*

---

OTHER CONSIDERATIONS:

- USE Context7 mcp to retreave the most upto date documentation for code
- Use Brave-search mcp to websearch if your websearch isnt working

- UI single source of truth: use examples/design/*.profile.json (not /apps/web/src/design). The app can import/copy these into /apps/web at build time, but the canonical source lives in examples/ for the template process.

- **`.env.example`** (place at repo root)

  ```env
  # Model providers
  OPENAI_API_KEY=
  ANTHROPIC_API_KEY=

  # Storage & DB
  STORAGE_PATH=./data/files
  DB_URL=sqlite:///./data/qaai.db
  VECTOR_STORE=faiss  # options: faiss|supabase

  # Optional Supabase (switch DB_URL & vectors accordingly)
  SUPABASE_URL=
  SUPABASE_ANON_KEY=

  # App
  APP_ENV=dev
  LOG_LEVEL=INFO
