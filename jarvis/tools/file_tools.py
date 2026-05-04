"""File system read/write/search tools."""
import json
import os
from pathlib import Path
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.config import get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)
MAX_BYTES = int(get("tools", "max_file_read_bytes", 50000))


def _expand(path: str) -> Path:
    return Path(path).expanduser().resolve()


class ReadFile(BaseTool):
    name = "read_file"
    description = "Read the contents of a file. Supports text files up to 50 KB."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or ~ path to file"},
            "encoding": {"type": "string", "default": "utf-8"},
            "max_bytes": {"type": "integer", "default": 50000},
        },
        "required": ["path"],
    }

    def run(self, path: str, encoding: str = "utf-8", max_bytes: int = MAX_BYTES) -> str:
        try:
            p = _expand(path)
            if not p.exists():
                return json.dumps({"error": f"File not found: {path}"})
            size = p.stat().st_size
            with open(p, encoding=encoding, errors="replace") as f:
                content = f.read(max_bytes)
            truncated = size > max_bytes
            return json.dumps({"content": content, "size_bytes": size, "truncated": truncated})
        except Exception as e:
            return json.dumps({"error": str(e)})


class WriteFile(BaseTool):
    name = "write_file"
    description = "Write or append content to a file. Creates parent directories if needed."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "mode": {"type": "string", "enum": ["write", "append"], "default": "write"},
        },
        "required": ["path", "content"],
    }

    def run(self, path: str, content: str, mode: str = "write") -> str:
        try:
            p = _expand(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            file_mode = "a" if mode == "append" else "w"
            with open(p, file_mode, encoding="utf-8") as f:
                f.write(content)
            return json.dumps({"success": True, "path": str(p), "bytes_written": len(content.encode())})
        except Exception as e:
            return json.dumps({"error": str(e)})


class ListDirectory(BaseTool):
    name = "list_directory"
    description = "List files and directories at a given path with size and modification time."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "default": "~"},
            "show_hidden": {"type": "boolean", "default": False},
            "recursive": {"type": "boolean", "default": False},
            "max_depth": {"type": "integer", "default": 2},
        },
        "required": [],
    }

    def run(self, path: str = "~", show_hidden: bool = False,
            recursive: bool = False, max_depth: int = 2) -> str:
        try:
            p = _expand(path)
            if not p.is_dir():
                return json.dumps({"error": f"Not a directory: {path}"})

            entries = []

            def scan(d: Path, depth: int):
                if depth > max_depth:
                    return
                try:
                    for item in sorted(d.iterdir()):
                        if not show_hidden and item.name.startswith("."):
                            continue
                        stat = item.stat()
                        entries.append({
                            "name": item.name,
                            "path": str(item),
                            "type": "dir" if item.is_dir() else "file",
                            "size": stat.st_size,
                        })
                        if recursive and item.is_dir():
                            scan(item, depth + 1)
                except PermissionError:
                    pass

            scan(p, 1)
            return json.dumps({"path": str(p), "entries": entries, "count": len(entries)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class FindFiles(BaseTool):
    name = "find_files"
    description = "Search for files by name pattern or extension. Returns matching file paths."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Filename pattern or partial name"},
            "search_path": {"type": "string", "default": "~"},
            "extension": {"type": "string", "description": "e.g. '.py', '.txt'"},
            "max_results": {"type": "integer", "default": 20},
        },
        "required": ["query"],
    }

    def run(self, query: str, search_path: str = "~", extension: str | None = None,
            max_results: int = 20) -> str:
        try:
            p = _expand(search_path)
            results = []
            pattern = f"*{query}*"
            for match in p.rglob(pattern):
                if extension and not match.suffix == extension:
                    continue
                results.append(str(match))
                if len(results) >= max_results:
                    break
            return json.dumps({"results": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"error": str(e)})
