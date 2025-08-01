"""
Citation 'binary match' demo.

Given a claim text and candidate sources (titles/sections),
score simple string similarity and decide pass/fail.

This is a lightweight proxy for the more robust LLM-based check in production.
"""

from __future__ import annotations
import re, math

def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def jaccard(a: str, b: str) -> float:
    A = set(normalize(a).split())
    B = set(normalize(b).split())
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)

def binary_match(claim: str, candidates: list[dict], threshold: float = 0.25) -> dict:
    best = None
    best_score = -1.0
    for c in candidates:
        score = max(
            jaccard(claim, c.get("title", "")),
            jaccard(claim, c.get("section", "")),
            jaccard(claim, f"{c.get('title','')} {c.get('section','')}")
        )
        if score > best_score:
            best, best_score = c, score
    return {"passed": best_score >= threshold, "best": best, "score": round(best_score, 3)}

if __name__ == "__main__":
    claim = "Employees in DIFC are entitled to minimum leave under Employment Law"
    candidates = [
        {"title": "DIFC Employment Law No. 2 of 2019", "section": "Part 9 — Leave"},
        {"title": "DIFC Data Protection Law 2020", "section": "Article 27"}
    ]
    result = binary_match(claim, candidates)
    print(result)
