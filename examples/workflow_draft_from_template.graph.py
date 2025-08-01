"""
LangGraph sketch for 'Draft from Template (DIFC)' workflow.

Graph:
 preflight -> plan -> retrieve(DIFC) -> draft -> verify_citations -> done

This is a minimal, framework-faithful shape that your FastAPI backend can call.
Model calls are stubbed; wire to OpenAI/Anthropic in the actual app layer.
"""

from __future__ import annotations
from typing import TypedDict, List, Optional, Literal
from langgraph.graph import StateGraph, END

# ---- State definition ----
class WFState(TypedDict, total=False):
    prompt: str
    template_doc_id: Optional[str]
    reference_doc_ids: List[str]
    jurisdiction: str
    plan: str
    citations: List[dict]
    draft: str
    thinking: List[str]
    error: Optional[str]

# ---- Node implementations (stubs) ----
def emit(state: WFState, label: str) -> WFState:
    thinking = state.get("thinking", [])
    thinking.append(label)
    state["thinking"] = thinking
    return state

def preflight(state: WFState) -> WFState:
    state = emit(state, "Validating inputs")
    if not state.get("template_doc_id"):
        state["error"] = "Missing template file"
        return state
    return state

def plan(state: WFState) -> WFState:
    state = emit(state, "Planning drafting steps")
    # In real system: call o1/Claude to produce a plan outline conditioned on DIFC
    state["plan"] = "1) Parse template 2) Read references 3) Insert clauses 4) Redline 5) Prepare citations"
    return state

def retrieve(state: WFState) -> WFState:
    state = emit(state, "Retrieving DIFC sources & Vault refs")
    # Real system: query vector store with jurisdiction=DIFC; add best matches to context
    # Here we attach placeholder citations
    state["citations"] = [
        {"title": "DIFC Employment Law No. 2 of 2019", "section": "Part 4", "url": "https://example/difc/employment"},
        {"title": "DIFC Data Protection Law 2020", "section": "Art. 27", "url": "https://example/difc/dpl"}
    ]
    return state

def draft(state: WFState) -> WFState:
    state = emit(state, "Drafting document with redlines")
    # Real system: call gpt-4.1/Claude with plan + retrieved context
    state["draft"] = "DRAFT_CONTENT_WITH_[REDACTED]_REDLINES"
    return state

def verify_citations(state: WFState) -> WFState:
    state = emit(state, "Verifying citations (binary match)")
    # Real system: run knowledge-source ID step and filter bad citations
    return state

# ---- Wiring the graph ----
graph = StateGraph(WFState)
graph.add_node("preflight", preflight)
graph.add_node("plan", plan)
graph.add_node("retrieve", retrieve)
graph.add_node("draft", draft)
graph.add_node("verify_citations", verify_citations)

graph.set_entry_point("preflight")
graph.add_edge("preflight", "plan")
graph.add_edge("plan", "retrieve")
graph.add_edge("retrieve", "draft")
graph.add_edge("draft", "verify_citations")
graph.add_edge("verify_citations", END)

app = graph.compile()

if __name__ == "__main__":
    # Demo run
    state: WFState = {
        "prompt": "Draft from template with DIFC law grounding",
        "template_doc_id": "tmpl-123",
        "reference_doc_ids": ["ref-1", "ref-2"],
        "jurisdiction": "DIFC",
        "thinking": []
    }
    result = app.invoke(state)
    print("Thinking states:", result["thinking"])
    print("Draft (preview):", result["draft"][:80], "...")
    print("Citations:", result.get("citations"))
