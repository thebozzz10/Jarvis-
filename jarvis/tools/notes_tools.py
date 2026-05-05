"""macOS Notes.app integration."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool


def _osa(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


class CreateNote(BaseTool):
    name = "create_note"
    description = "Create a new note in macOS Notes.app."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "folder": {"type": "string", "default": "Notes"},
        },
        "required": ["title", "body"],
    }

    def run(self, title: str, body: str, folder: str = "Notes") -> str:
        try:
            esc_body = body.replace('"', '\\"').replace("\n", "<br>")
            script = f'''
tell application "Notes"
    make new note at folder "{folder}" with properties {{name:"{title}", body:"{esc_body}"}}
end tell
'''
            _osa(script)
            return json.dumps({"success": True, "title": title})
        except Exception as e:
            return json.dumps({"error": str(e)})


class SearchNotes(BaseTool):
    name = "search_notes"
    description = "Search for notes by title or content in macOS Notes.app."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 10},
        },
        "required": ["query"],
    }

    def run(self, query: str, max_results: int = 10) -> str:
        try:
            script = f'''
tell application "Notes"
    set notes_found to notes whose name contains "{query}" or body contains "{query}"
    set output to ""
    set counter to 0
    repeat with n in notes_found
        if counter >= {max_results} then exit repeat
        set output to output & (name of n) & " | " & (modification date of n as string) & linefeed
        set counter to counter + 1
    end repeat
    return output
end tell
'''
            output = _osa(script)
            notes = []
            for line in output.split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    notes.append({"title": parts[0], "modified": parts[1] if len(parts) > 1 else ""})
            return json.dumps({"notes": notes, "count": len(notes)})
        except Exception as e:
            return json.dumps({"error": str(e)})
