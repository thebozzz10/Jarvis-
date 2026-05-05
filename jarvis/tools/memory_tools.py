"""Memory storage/retrieval, time, and clipboard tools."""
import json
import subprocess
from datetime import datetime
from jarvis.core.tool_registry import BaseTool
from jarvis.memory import memory_store
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class Remember(BaseTool):
    name = "remember"
    description = "Store a piece of information in persistent memory for future sessions. Always call this when the user tells you something important about themselves, their preferences, or their projects."
    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The information to remember"},
            "category": {
                "type": "string",
                "enum": ["preference", "fact", "task", "person", "project", "general"],
                "default": "general",
            },
            "tags": {"type": "array", "items": {"type": "string"}},
            "importance": {"type": "integer", "description": "1-5 priority score", "default": 3},
        },
        "required": ["content"],
    }

    def run(self, content: str, category: str = "general", tags: list[str] | None = None,
            importance: int = 3) -> str:
        try:
            mid = memory_store.store_memory(content, category, tags, importance)
            # Compute embedding asynchronously so semantic recall works
            try:
                from jarvis.memory import embeddings
                embeddings.update_embedding(mid, content)
            except Exception as e:
                log.debug("Embedding update skipped: %s", e)
            return json.dumps({"success": True, "memory_id": mid, "stored": content[:80]})
        except Exception as e:
            return json.dumps({"error": str(e)})


class Recall(BaseTool):
    name = "recall"
    description = "Search persistent memory for information matching a query. Use this to retrieve things the user told you in past sessions."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for"},
            "category": {
                "type": "string",
                "enum": ["preference", "fact", "task", "person", "project", "general", "all"],
                "default": "all",
            },
            "max_results": {"type": "integer", "default": 10},
            "since_days": {"type": "integer", "description": "Only memories from the last N days"},
        },
        "required": ["query"],
    }

    def run(self, query: str, category: str = "all", max_results: int = 10,
            since_days: int | None = None) -> str:
        try:
            results = memory_store.search_memories(query, category, max_results, since_days)
            clean = [{"id": r["id"], "content": r["content"], "category": r["category"],
                      "importance": r["importance"], "created_at": r["created_at"]}
                     for r in results]
            return json.dumps({"query": query, "memories": clean, "count": len(clean)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class GetTimeAndDate(BaseTool):
    name = "get_time_and_date"
    description = "Get the current date, time, day of week, and timezone."
    input_schema = {
        "type": "object",
        "properties": {
            "timezone": {"type": "string", "description": "IANA timezone name (uses system default if omitted)"},
        },
        "required": [],
    }

    def run(self, timezone: str | None = None) -> str:
        try:
            if timezone:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(timezone)
                now = datetime.now(tz)
            else:
                now = datetime.now().astimezone()
            return json.dumps({
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "date": now.strftime("%A, %B %d %Y"),
                "time": now.strftime("%I:%M %p"),
                "timezone": str(now.tzinfo),
                "iso8601": now.isoformat(),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})


class ClipboardControl(BaseTool):
    name = "clipboard_control"
    description = "Read from or write to the macOS clipboard."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "write", "clear"]},
            "content": {"type": "string", "description": "Content to write (required when action=write)"},
        },
        "required": ["action"],
    }

    def run(self, action: str, content: str | None = None) -> str:
        try:
            if action == "read":
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return json.dumps({"content": result.stdout, "length": len(result.stdout)})
            elif action == "write" and content is not None:
                proc = subprocess.run(["pbcopy"], input=content, text=True, capture_output=True)
                return json.dumps({"success": True, "bytes_written": len(content)})
            elif action == "clear":
                subprocess.run(["pbcopy"], input="", text=True)
                return json.dumps({"success": True})
            return json.dumps({"error": "Invalid action or missing content"})
        except Exception as e:
            return json.dumps({"error": str(e)})
