"""SQLite database setup, migrations, and connection management."""
import sqlite3
import threading
from pathlib import Path
from jarvis.utils.config import DB_PATH
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def init_db():
    """Create tables and indexes on first run."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            content         TEXT NOT NULL,
            category        TEXT NOT NULL DEFAULT 'general',
            tags            TEXT,
            importance      INTEGER DEFAULT 3,
            access_count    INTEGER DEFAULT 0,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_accessed_at DATETIME,
            source          TEXT DEFAULT 'user'
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL UNIQUE,
            started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at        DATETIME,
            summary         TEXT,
            message_count   INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            tool_name   TEXT,
            tool_input  TEXT,
            tool_result TEXT,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            tokens_used INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE TABLE IF NOT EXISTS preferences (
            key         TEXT PRIMARY KEY,
            value       TEXT NOT NULL,
            data_type   TEXT NOT NULL DEFAULT 'str',
            description TEXT,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS entities (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            entity_type  TEXT NOT NULL,
            attributes   TEXT,
            first_seen   DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen    DATETIME DEFAULT CURRENT_TIMESTAMP,
            mention_count INTEGER DEFAULT 1
        );

        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp DESC);

        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, tags, content='memories', content_rowid='id', tokenize='porter ascii');

        CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
            INSERT INTO memories_fts(rowid, content, tags) VALUES (new.id, new.content, COALESCE(new.tags, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, tags)
                VALUES('delete', old.id, old.content, COALESCE(old.tags, ''));
        END;

        CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
            INSERT INTO memories_fts(memories_fts, rowid, content, tags)
                VALUES('delete', old.id, old.content, COALESCE(old.tags, ''));
            INSERT INTO memories_fts(rowid, content, tags) VALUES (new.id, new.content, COALESCE(new.tags, ''));
        END;
    """)
    conn.commit()

    # Phase 2: knowledge graph + embeddings columns
    try:
        from jarvis.memory.knowledge_graph import init_kg
        init_kg()
    except Exception as e:
        log.debug("KG init skipped: %s", e)
    try:
        from jarvis.memory.embeddings import ensure_embedding_column
        ensure_embedding_column()
    except Exception as e:
        log.debug("Embedding column init skipped: %s", e)

    log.info("Database initialized at %s", DB_PATH)
