"""
Assistant SSE example for QaAI.

Streams 'thinking states' and final answer from the backend:
POST /api/assistant/query  (SSE stream)

Usage:
  python examples/assistant_run.py --prompt "Explain DIFC Employment Law basics with citations"

Requires:
  - BACKEND_URL in .env (default http://localhost:8000)
  - python-dotenv, requests
"""

from __future__ import annotations
import argparse, json, os, sys
from typing import Iterator
from dotenv import load_dotenv
import requests

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def stream_sse(url: str, json_payload: dict) -> Iterator[dict]:
    """
    Minimal SSE reader for a POST stream.
    Assumes server sends 'data: {...}\\n\\n' JSON chunks.
    """
    with requests.post(url, json=json_payload, stream=True) as r:
        r.raise_for_status()
        buffer = ""
        for raw in r.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                # end of event
                if buffer.startswith("data:"):
                    data = buffer[5:].strip()
                    try:
                        yield json.loads(data)
                    except Exception:
                        print("[warn] non-JSON SSE data:", data)
                buffer = ""
                continue
            if line.startswith("data:"):
                buffer = line
            else:
                buffer += line  # handle multi-line payloads


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, help="User prompt")
    parser.add_argument("--mode", default="assist", choices=["assist", "draft"])
    parser.add_argument("--jurisdiction", default=os.getenv("DEFAULT_JURISDICTION", "DIFC"))
    args = parser.parse_args()

    url = f"{BACKEND_URL}/api/assistant/query"
    payload = {
        "mode": args.mode,
        "prompt": args.prompt,
        "knowledge": {
            "jurisdiction": args.jurisdiction,
            "sources": ["DIFC_LAWS", "DFSA_RULEBOOK", "DIFC_COURTS_RULES", "VAULT"]
        },
        # Optional: point to a Vault project or attach file IDs known to backend
        "vault_project_id": None,
        "attachments": []
    }

    print(f"[info] POST {url}")
    for event in stream_sse(url, payload):
        etype = event.get("type")
        if etype == "thinking_state":
            print(f"  • {event.get('label')}", flush=True)
        elif etype == "chunk":
            sys.stdout.write(event.get("text", ""))
            sys.stdout.flush()
        elif etype == "citation":
            print(f"\n[citation] {event.get('title')} — {event.get('url')}")
        elif etype == "done":
            print("\n[done]")
        else:
            print(f"[event] {event}")


if __name__ == "__main__":
    main()
