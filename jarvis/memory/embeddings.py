"""Local sentence-transformer embeddings for semantic memory recall."""
import threading
import numpy as np
import sqlite3
from typing import List
from jarvis.memory.database import get_conn
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

_model = None
_model_lock = threading.Lock()
_MODEL_NAME = "all-MiniLM-L6-v2"


def _load_model():
    global _model
    with _model_lock:
        if _model is None:
            try:
                from sentence_transformers import SentenceTransformer
                log.info("Loading embedding model: %s", _MODEL_NAME)
                _model = SentenceTransformer(_MODEL_NAME)
            except Exception as e:
                log.warning("Embedding model unavailable: %s", e)
                _model = False
    return _model


def embed(texts: List[str]) -> np.ndarray | None:
    m = _load_model()
    if not m:
        return None
    return m.encode(texts, normalize_embeddings=True)


def ensure_embedding_column():
    conn = get_conn()
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN embedding BLOB")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column exists


def update_embedding(memory_id: int, content: str):
    vec = embed([content])
    if vec is None:
        return
    blob = vec[0].astype(np.float32).tobytes()
    conn = get_conn()
    conn.execute("UPDATE memories SET embedding=? WHERE id=?", (blob, memory_id))
    conn.commit()


def vector_search(query: str, k: int = 10, threshold: float = 0.35) -> list[dict]:
    """Cosine similarity search over stored memory embeddings."""
    qvec = embed([query])
    if qvec is None:
        return []
    qvec = qvec[0]

    conn = get_conn()
    rows = conn.execute(
        "SELECT id, content, category, importance, embedding FROM memories WHERE embedding IS NOT NULL"
    ).fetchall()
    if not rows:
        return []

    scored = []
    for r in rows:
        vec = np.frombuffer(r["embedding"], dtype=np.float32)
        sim = float(np.dot(qvec, vec))
        if sim >= threshold:
            scored.append({"id": r["id"], "content": r["content"],
                           "category": r["category"], "importance": r["importance"],
                           "similarity": round(sim, 3)})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:k]


def reembed_all():
    """Re-compute embeddings for memories that don't have one."""
    conn = get_conn()
    rows = conn.execute("SELECT id, content FROM memories WHERE embedding IS NULL").fetchall()
    if not rows:
        return 0
    contents = [r["content"] for r in rows]
    vecs = embed(contents)
    if vecs is None:
        return 0
    for r, v in zip(rows, vecs):
        conn.execute("UPDATE memories SET embedding=? WHERE id=?",
                     (v.astype(np.float32).tobytes(), r["id"]))
    conn.commit()
    return len(rows)
