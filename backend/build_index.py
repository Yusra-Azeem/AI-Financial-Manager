"""
build_index.py
Run this once (and again any time data/loan_policy.md changes) to embed the
policy document and store it in the policy_chunks table for RAG retrieval.

Requires a real GEMINI_API_KEY or OPENAI_API_KEY in .env — this makes live
calls to the embeddings API, so it will fail without a valid key.

Run with:  python build_index.py
"""
from database import SessionLocal, init_db
from services.rag import build_index, DEFAULT_POLICY_PATH


def run():
    init_db()
    db = SessionLocal()
    try:
        count = build_index(db, DEFAULT_POLICY_PATH)
        print(f"Indexed {count} policy chunks from {DEFAULT_POLICY_PATH}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
