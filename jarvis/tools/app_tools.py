"""macOS application and window management tools."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class LaunchApp(BaseTool):
    name = "launch_app"
    description = "Launch a macOS application by name. Works with any app in /Applications or ~/Applications."
    input_schema = {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "App name e.g. 'Safari', 'Finder', 'Terminal', 'Spotify'"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "Optional command-line arguments"},
        },
        "required": ["app_name"],
    }

    def run(self, app_name: str, args: list[str] | None = None) -> str:
        try:
            cmd = ["open", "-a", app_name]
            if args:
                cmd += ["--args"] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return json.dumps({"success": True, "launched": app_name})
            return json.dumps({"error": result.stderr.strip() or f"Could not open {app_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})


class ListWindows(BaseTool):
    name = "list_windows"
    description = "List all running macOS applications and their open windows."
    input_schema = {
        "type": "object",
        "properties": {
            "app_filter": {"type": "string", "description": "Optional app name to filter results"},
        },
        "required": [],
    }

    def run(self, app_filter: str | None = None) -> str:
        try:
            script = '''
tell application "System Events"
    set appList to {}
    repeat with proc in (every application process whose background only is false)
        set appName to name of proc
        set winList to {}
        try
            repeat with w in (every window of proc)
                set end of winList to name of w
            end repeat
        end try
        set end of appList to {appName, winList}
    end repeat
    return appList
end tell
'''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            raw = result.stdout.strip()
            apps = []
            # Parse AppleScript list output (simplified)
            for line in raw.split(","):
                line = line.strip().strip("{").strip("}")
                if line:
                    apps.append(line)

            if app_filter:
                apps = [a for a in apps if app_filter.lower() in a.lower()]

            return json.dumps({"apps": apps, "count": len(apps)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class FocusWindow(BaseTool):
    name = "focus_window"
    description = "Bring an application window to the foreground by app name."
    input_schema = {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Application name e.g. 'Safari'"},
        },
        "required": ["app_name"],
    }

    def run(self, app_name: str) -> str:
        try:
            script = f'tell application "{app_name}" to activate'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return json.dumps({"success": True, "focused": app_name})
            return json.dumps({"error": result.stderr.strip()})
        except Exception as e:
            return json.dumps({"error": str(e)})
