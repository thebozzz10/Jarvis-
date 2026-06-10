"""macOS Calendar.app + Reminders.app integration via AppleScript."""
import json
import subprocess
from datetime import datetime, timedelta
from jarvis.core.tool_registry import BaseTool
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


def _osa(script: str, timeout: int = 15) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "osascript failed")
    return result.stdout.strip()


class GetCalendarEvents(BaseTool):
    name = "get_calendar_events"
    description = "Get upcoming events from macOS Calendar within a date range."
    input_schema = {
        "type": "object",
        "properties": {
            "days_ahead": {"type": "integer", "description": "How many days forward to look", "default": 7},
            "calendar": {"type": "string", "description": "Optional calendar name (e.g. 'Work')"},
        },
        "required": [],
    }

    def run(self, days_ahead: int = 7, calendar: str | None = None) -> str:
        try:
            cal_filter = f'whose name is "{calendar}"' if calendar else ""
            script = f'''
tell application "Calendar"
    set startDate to current date
    set endDate to startDate + ({days_ahead} * days)
    set output to ""
    repeat with cal in (every calendar {cal_filter})
        set evts to (every event of cal whose start date is greater than or equal to startDate and start date is less than endDate)
        repeat with evt in evts
            set output to output & (summary of evt) & " | " & (start date of evt as string) & " | " & (name of cal) & linefeed
        end repeat
    end repeat
    return output
end tell
'''
            output = _osa(script)
            events = []
            for line in output.split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        events.append({"title": parts[0], "start": parts[1], "calendar": parts[2]})
            return json.dumps({"events": events, "count": len(events)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class CreateCalendarEvent(BaseTool):
    name = "create_calendar_event"
    description = "Create a new event in macOS Calendar."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "start_iso": {"type": "string", "description": "ISO 8601 start datetime e.g. 2026-05-10T14:00"},
            "duration_minutes": {"type": "integer", "default": 60},
            "calendar": {"type": "string", "description": "Calendar name", "default": "Calendar"},
            "notes": {"type": "string", "default": ""},
            "location": {"type": "string", "default": ""},
        },
        "required": ["title", "start_iso"],
    }

    def run(self, title: str, start_iso: str, duration_minutes: int = 60,
            calendar: str = "Calendar", notes: str = "", location: str = "") -> str:
        try:
            dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            end_dt = dt + timedelta(minutes=duration_minutes)
            start_str = dt.strftime("%m/%d/%Y %I:%M:%S %p")
            end_str = end_dt.strftime("%m/%d/%Y %I:%M:%S %p")
            script = f'''
tell application "Calendar"
    tell calendar "{calendar}"
        make new event with properties {{summary:"{title}", start date:date "{start_str}", end date:date "{end_str}", description:"{notes}", location:"{location}"}}
    end tell
end tell
'''
            _osa(script)
            return json.dumps({"success": True, "event": title, "start": start_iso})
        except Exception as e:
            return json.dumps({"error": str(e)})


class GetReminders(BaseTool):
    name = "get_reminders"
    description = "Get incomplete reminders from macOS Reminders.app."
    input_schema = {
        "type": "object",
        "properties": {
            "list_name": {"type": "string", "description": "Optional list name"},
        },
        "required": [],
    }

    def run(self, list_name: str | None = None) -> str:
        try:
            list_filter = f'in list "{list_name}"' if list_name else ""
            script = f'''
tell application "Reminders"
    set output to ""
    set rems to (every reminder {list_filter} whose completed is false)
    repeat with r in rems
        set dueStr to ""
        try
            set dueStr to (due date of r as string)
        end try
        set output to output & (name of r) & " | " & dueStr & linefeed
    end repeat
    return output
end tell
'''
            output = _osa(script)
            reminders = []
            for line in output.split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    reminders.append({"name": parts[0], "due": parts[1] if len(parts) > 1 else ""})
            return json.dumps({"reminders": reminders, "count": len(reminders)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class CreateReminder(BaseTool):
    name = "create_reminder"
    description = "Create a new reminder in macOS Reminders.app."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "due_iso": {"type": "string", "description": "Optional ISO 8601 due datetime"},
            "list_name": {"type": "string", "default": "Reminders"},
            "notes": {"type": "string", "default": ""},
        },
        "required": ["title"],
    }

    def run(self, title: str, due_iso: str | None = None,
            list_name: str = "Reminders", notes: str = "") -> str:
        try:
            due_clause = ""
            if due_iso:
                dt = datetime.fromisoformat(due_iso.replace("Z", "+00:00"))
                due_str = dt.strftime("%m/%d/%Y %I:%M:%S %p")
                due_clause = f', due date:date "{due_str}"'
            script = f'''
tell application "Reminders"
    tell list "{list_name}"
        make new reminder with properties {{name:"{title}", body:"{notes}"{due_clause}}}
    end tell
end tell
'''
            _osa(script)
            return json.dumps({"success": True, "reminder": title})
        except Exception as e:
            return json.dumps({"error": str(e)})
