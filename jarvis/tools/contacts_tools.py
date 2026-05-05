"""macOS Contacts.app integration."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool


def _osa(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


class SearchContacts(BaseTool):
    name = "search_contacts"
    description = "Search for a person in macOS Contacts.app and return their phone, email, and address."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Name to search for"},
        },
        "required": ["query"],
    }

    def run(self, query: str) -> str:
        try:
            script = f'''
tell application "Contacts"
    set people_found to (every person whose name contains "{query}")
    set output to ""
    repeat with p in people_found
        set output to output & (name of p) & "|"
        try
            set output to output & (value of (every email of p) as string)
        end try
        set output to output & "|"
        try
            set output to output & (value of (every phone of p) as string)
        end try
        set output to output & linefeed
    end repeat
    return output
end tell
'''
            output = _osa(script)
            contacts = []
            for line in output.split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    contacts.append({
                        "name": parts[0].strip(),
                        "emails": parts[1].strip() if len(parts) > 1 else "",
                        "phones": parts[2].strip() if len(parts) > 2 else "",
                    })
            return json.dumps({"contacts": contacts, "count": len(contacts)})
        except Exception as e:
            return json.dumps({"error": str(e)})
