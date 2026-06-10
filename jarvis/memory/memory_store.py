"""CRUD operations for all memory tables."""
import json
import uuid
from datetime import datetime
from typing import Any
from jarvis.memory.database import get_conn
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


# ── Memories ──────────────────────────────────────────────────────────────────

def store_memory(content: str, category: str = "general", tags: list[str] | None = None,
                 importance: int = 3, source: str = "user") -> int:
    conn = get_conn()
    tags_json = json.dumps(tags or [])
    cur = conn.execute(
        "INSERT INTO memories (content, category, tags, importance, source) VALUES (?,?,?,?,?)",
        (content, category, tags_json, importance, source),
    )
    conn.commit()
    log.debug("Stored memory #%d: %.60s", cur.lastrowid, content)
    return cur.lastrowid


def search_memories(query: str, category: str = "all", max_results: int = 10,
                    since_days: int | None = None) -> list[dict]:
    conn = get_conn()
    params: list[Any] = [query, max_results]
    cat_clause = "" if category == "all" else "AND m.category = ?"
    if category != "all":
        params.insert(1, category)
    day_clause = ""
    if since_days:
        day_clause = "AND m.created_at >= datetime('now', ?)"
        params.insert(-1, f"-{since_days} days")

    sql = f"""
        SELECT m.* FROM memories m
        JOIN memories_fts fts ON m.id = fts.rowid
        WHERE memories_fts MATCH ? {cat_clause} {day_clause}
        ORDER BY rank
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        # Fallback to LIKE search if FTS fails
        like = f"%{query}%"
        rows = conn.execute(
            f"SELECT * FROM memories WHERE content LIKE ? {cat_clause} ORDER BY importance DESC LIMIT ?",
            [like] + ([category] if category != "all" else []) + [max_results],
        ).fetchall()

    # Update access stats
    ids = [r["id"] for r in rows]
    if ids:
        placeholders = ",".join("?" * len(ids))
        conn.execute(
            f"UPDATE memories SET access_count=access_count+1, last_accessed_at=CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
            ids,
        )
        conn.commit()

    return [dict(r) for r in rows]


def get_top_memories(limit: int = 15) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM memories ORDER BY importance DESC, access_count DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def delete_memory(memory_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
    conn.commit()


# ── Sessions & Messages ────────────────────────────────────────────────────────

def create_session() -> str:
    sid = str(uuid.uuid4())[:8]
    conn = get_conn()
    conn.execute("INSERT INTO sessions (session_id) VALUES (?)", (sid,))
    conn.commit()
    log.info("New session: %s", sid)
    return sid


def close_session(session_id: str, summary: str = ""):
    conn = get_conn()
    conn.execute(
        "UPDATE sessions SET ended_at=CURRENT_TIMESTAMP, summary=? WHERE session_id=?",
        (summary, session_id),
    )
    conn.commit()


def add_message(session_id: str, role: str, content: str,
                tool_name: str = "", tool_input: dict | None = None,
                tool_result: str = "", tokens_used: int = 0):
    conn = get_conn()
    conn.execute(
        """INSERT INTO messages (session_id, role, content, tool_name, tool_input, tool_result, tokens_used)
           VALUES (?,?,?,?,?,?,?)""",
        (session_id, role, content, tool_name,
         json.dumps(tool_input) if tool_input else None,
         tool_result, tokens_used),
    )
    conn.execute(
        "UPDATE sessions SET message_count=message_count+1 WHERE session_id=?", (session_id,)
    )
    conn.commit()


def get_session_messages(session_id: str, limit: int = 100) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY timestamp ASC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Preferences ───────────────────────────────────────────────────────────────

def set_preference(key: str, value: Any, data_type: str = "str", description: str = ""):
    conn = get_conn()
    conn.execute(
        """INSERT INTO preferences (key, value, data_type, description, updated_at)
           VALUES (?,?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
        (key, json.dumps(value), data_type, description),
    )
    conn.commit()


def get_preference(key: str, default: Any = None) -> Any:
    conn = get_conn()
    row = conn.execute("SELECT value, data_type FROM preferences WHERE key=?", (key,)).fetchone()
    if row is None:
        return default
    return json.loads(row["value"])


def get_all_preferences() -> dict[str, Any]:
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM preferences").fetchall()
    return {r["key"]: json.loads(r["value"]) for r in rows}


# ── Entities ──────────────────────────────────────────────────────────────────

def upsert_entity(name: str, entity_type: str, attributes: dict | None = None):
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM entities WHERE name=? AND entity_type=?", (name, entity_type)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE entities SET attributes=?, last_seen=CURRENT_TIMESTAMP, mention_count=mention_count+1 WHERE id=?",
            (json.dumps(attributes or {}), existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO entities (name, entity_type, attributes) VALUES (?,?,?)",
            (name, entity_type, json.dumps(attributes or {})),
        )
    conn.commit()
