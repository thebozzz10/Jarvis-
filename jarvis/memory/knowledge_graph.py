"""Entity & relation knowledge graph stored in SQLite."""
import json
from jarvis.memory.database import get_conn
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


def init_kg():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS relations (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id    INTEGER NOT NULL,
            target_id    INTEGER NOT NULL,
            relation     TEXT NOT NULL,
            attributes   TEXT,
            confidence   REAL DEFAULT 1.0,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES entities(id),
            FOREIGN KEY (target_id) REFERENCES entities(id)
        );
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id);
        CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id);
        CREATE INDEX IF NOT EXISTS idx_rel_type ON relations(relation);
    """)
    conn.commit()


def add_entity(name: str, entity_type: str, attributes: dict | None = None) -> int:
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM entities WHERE name=? AND entity_type=?", (name, entity_type)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE entities SET attributes=?, last_seen=CURRENT_TIMESTAMP, mention_count=mention_count+1 WHERE id=?",
            (json.dumps(attributes or {}), existing["id"]),
        )
        conn.commit()
        return existing["id"]
    cur = conn.execute(
        "INSERT INTO entities (name, entity_type, attributes) VALUES (?,?,?)",
        (name, entity_type, json.dumps(attributes or {})),
    )
    conn.commit()
    return cur.lastrowid


def add_relation(source: str, source_type: str, target: str, target_type: str,
                 relation: str, attributes: dict | None = None) -> int:
    src_id = add_entity(source, source_type)
    tgt_id = add_entity(target, target_type)
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO relations (source_id, target_id, relation, attributes) VALUES (?,?,?,?)",
        (src_id, tgt_id, relation, json.dumps(attributes or {})),
    )
    conn.commit()
    return cur.lastrowid


def query_entity(name: str) -> dict | None:
    conn = get_conn()
    e = conn.execute("SELECT * FROM entities WHERE name LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()
    if not e:
        return None
    rels_out = conn.execute(
        """SELECT r.relation, e.name AS target FROM relations r
           JOIN entities e ON r.target_id = e.id WHERE r.source_id=?""", (e["id"],)
    ).fetchall()
    rels_in = conn.execute(
        """SELECT r.relation, e.name AS source FROM relations r
           JOIN entities e ON r.source_id = e.id WHERE r.target_id=?""", (e["id"],)
    ).fetchall()
    return {
        "name": e["name"], "type": e["entity_type"],
        "attributes": json.loads(e["attributes"] or "{}"),
        "outgoing": [dict(r) for r in rels_out],
        "incoming": [dict(r) for r in rels_in],
        "mention_count": e["mention_count"],
    }


def list_entities(entity_type: str | None = None, limit: int = 50) -> list[dict]:
    conn = get_conn()
    if entity_type:
        rows = conn.execute(
            "SELECT * FROM entities WHERE entity_type=? ORDER BY mention_count DESC LIMIT ?",
            (entity_type, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM entities ORDER BY mention_count DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{"name": r["name"], "type": r["entity_type"], "mentions": r["mention_count"]} for r in rows]
