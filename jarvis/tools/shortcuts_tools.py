"""macOS Shortcuts.app integration via the `shortcuts` CLI."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool


class RunShortcut(BaseTool):
    name = "run_shortcut"
    description = "Run a macOS Shortcut by name. Shortcuts are user-created automations from the Shortcuts app."
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Exact shortcut name"},
            "input_text": {"type": "string", "description": "Optional input string passed to the shortcut"},
        },
        "required": ["name"],
    }

    def run(self, name: str, input_text: str | None = None) -> str:
        try:
            cmd = ["shortcuts", "run", name]
            kwargs = {"capture_output": True, "text": True, "timeout": 60}
            if input_text:
                proc = subprocess.run(cmd, input=input_text, **kwargs)
            else:
                proc = subprocess.run(cmd, **kwargs)
            if proc.returncode != 0:
                return json.dumps({"error": proc.stderr.strip() or "Shortcut failed"})
            return json.dumps({"success": True, "output": proc.stdout.strip()})
        except FileNotFoundError:
            return json.dumps({"error": "shortcuts CLI not found (requires macOS 12+)"})
        except Exception as e:
            return json.dumps({"error": str(e)})


class ListShortcuts(BaseTool):
    name = "list_shortcuts"
    description = "List all available macOS Shortcuts."
    input_schema = {"type": "object", "properties": {}, "required": []}

    def run(self) -> str:
        try:
            proc = subprocess.run(["shortcuts", "list"], capture_output=True, text=True, timeout=10)
            shortcuts = [s.strip() for s in proc.stdout.splitlines() if s.strip()]
            return json.dumps({"shortcuts": shortcuts, "count": len(shortcuts)})
        except FileNotFoundError:
            return json.dumps({"error": "shortcuts CLI not found"})
        except Exception as e:
            return json.dumps({"error": str(e)})
