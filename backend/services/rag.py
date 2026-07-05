"""
services/rag.py
Retrieval-Augmented Generation over the loan policy document.

Flow:
  1. build_index() reads data/loan_policy.md, splits it into chunks (one per
     "## Section" heading works well for our policy doc), embeds each chunk,
     and stores them in the policy_chunks table.
  2. retrieve(question) embeds the question and returns the most similar
     chunks using cosine similarity computed in Python.
  3. agent/tools.py's explain_policy() feeds those chunks to ask_llm() so the
     answer is grounded in the actual policy text instead of the LLM guessing.

This intentionally avoids requiring the pgvector Postgres extension so it
works identically on local sqlite and on Supabase out of the box. See the
note in models.py (PolicyChunk) for how to upgrade to native pgvector later.
"""
import json
import re

import numpy as np
from sqlalchemy.orm import Session

from services.llm import get_embedding

DEFAULT_POLICY_PATH = "data/loan_policy.md"


def chunk_markdown(text: str) -> list[dict]:
    """
    Splits the policy doc on '## ' headings so each chunk is one coherent
    section (e.g. "Education Loans"). This keeps retrieval on-topic and
    gives us clean citations.
    """
    parts = re.split(r"\n(?=## )", text.strip())
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        heading_match = re.match(r"##\s*\d*\.?\s*(.+)", part.splitlines()[0])
        section = heading_match.group(1).strip() if heading_match else "Overview"
        chunks.append({"section": section, "content": part})
    return chunks


def build_index(db: Session, filepath: str = DEFAULT_POLICY_PATH) -> int:
    """
    Reads the policy doc, embeds each section, and (re)populates the
    policy_chunks table. Returns the number of chunks indexed.
    Safe to re-run — it clears old chunks from the same source first.
    """
    import models

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_markdown(text)

    db.query(models.PolicyChunk).filter(models.PolicyChunk.source == filepath).delete()

    for chunk in chunks:
        vector = get_embedding(chunk["content"])
        db.add(models.PolicyChunk(
            source=filepath,
            section=chunk["section"],
            content=chunk["content"],
            embedding=json.dumps(vector),
        ))

    db.commit()
    return len(chunks)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def retrieve(db: Session, question: str, top_k: int = 3) -> list[dict]:
    """
    Returns the top_k most relevant policy chunks for `question`, ranked by
    cosine similarity, each with a similarity score for transparency/debugging.
    """
    import models

    all_chunks = db.query(models.PolicyChunk).all()
    if not all_chunks:
        return []

    query_vector = get_embedding(question)

    scored = []
    for chunk in all_chunks:
        chunk_vector = json.loads(chunk.embedding)
        score = _cosine_similarity(query_vector, chunk_vector)
        scored.append({
            "section": chunk.section,
            "content": chunk.content,
            "score": round(score, 4),
        })

    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]
