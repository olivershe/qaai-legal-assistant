# QaAI Examples

These examples are **reference implementations** for engineers. They are small, runnable scripts that exercise the planned API surface, RAG ingestion, LangGraph orchestration, and citation verification.

> **Note:** Do not copy examples from other projects; these are purpose-built for QaAI’s architecture and DIFC-first constraints.

## Prerequisites

- Python 3.10+
- `pip install -r examples/requirements.txt`
- Copy `.env.example` to `.env` and fill any keys you have (OpenAI/Anthropic optional for some scripts).

## Files

- `assistant_run.py` — Calls the Assistant endpoint and reads **SSE** thinking states.
- `rag_ingest.py` — Builds a local **FAISS** vector index from PDFs/HTML under `examples/sample_corpus/`.
- `workflow_draft_from_template.graph.py` — Minimal **LangGraph** of the “Draft from Template (DIFC)” workflow.
- `citations_check.py` — Lightweight **citation verification** demo (binary match over candidates).
- `web/` — Static **browser** SSE demo and UI tokens showcase.

## Running

```bash
# 1) Create venv & install deps
python -m venv .venv && source .venv/bin/activate
pip install -r examples/requirements.txt

# 2) Ingest a small corpus (PDFs in examples/sample_corpus)
python examples/rag_ingest.py

# 3) Run Assistant example (requires backend running at BACKEND_URL)
python examples/assistant_run.py --prompt "Summarize recent changes in DIFC Data Protection Law with citations"
