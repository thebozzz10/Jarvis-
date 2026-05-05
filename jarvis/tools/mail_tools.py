"""macOS Mail.app + Messages.app integration."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool


def _osa(script: str, timeout: int = 20) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


class GetUnreadMail(BaseTool):
    name = "get_unread_mail"
    description = "Get unread emails from macOS Mail.app."
    input_schema = {
        "type": "object",
        "properties": {
            "max_results": {"type": "integer", "default": 10},
        },
        "required": [],
    }

    def run(self, max_results: int = 10) -> str:
        try:
            script = f'''
tell application "Mail"
    set unreadMsgs to messages of inbox whose read status is false
    set output to ""
    set counter to 0
    repeat with msg in unreadMsgs
        if counter >= {max_results} then exit repeat
        set output to output & (subject of msg) & " | " & (sender of msg) & " | " & (date received of msg as string) & linefeed
        set counter to counter + 1
    end repeat
    return output
end tell
'''
            output = _osa(script)
            messages = []
            for line in output.split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 3:
                        messages.append({"subject": parts[0], "from": parts[1], "date": parts[2]})
            return json.dumps({"messages": messages, "count": len(messages)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class SendMail(BaseTool):
    name = "send_mail"
    description = "Compose and send an email via macOS Mail.app. Confirms before sending."
    input_schema = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "send_immediately": {"type": "boolean", "default": False, "description": "If false, opens compose window"},
        },
        "required": ["to", "subject", "body"],
    }

    def run(self, to: str, subject: str, body: str, send_immediately: bool = False) -> str:
        try:
            send_clause = "send newMsg" if send_immediately else "activate"
            esc_body = body.replace('"', '\\"').replace("\n", "\\n")
            script = f'''
tell application "Mail"
    set newMsg to make new outgoing message with properties {{subject:"{subject}", content:"{esc_body}", visible:true}}
    tell newMsg
        make new to recipient at end of to recipients with properties {{address:"{to}"}}
    end tell
    {send_clause}
end tell
'''
            _osa(script)
            return json.dumps({"success": True, "to": to, "sent": send_immediately})
        except Exception as e:
            return json.dumps({"error": str(e)})


class SendMessage(BaseTool):
    name = "send_message"
    description = "Send an iMessage via macOS Messages.app."
    input_schema = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Phone number or Apple ID"},
            "text": {"type": "string"},
        },
        "required": ["to", "text"],
    }

    def run(self, to: str, text: str) -> str:
        try:
            esc = text.replace('"', '\\"')
            script = f'''
tell application "Messages"
    set targetService to 1st service whose service type = iMessage
    set targetBuddy to buddy "{to}" of targetService
    send "{esc}" to targetBuddy
end tell
'''
            _osa(script)
            return json.dumps({"success": True, "to": to})
        except Exception as e:
            return json.dumps({"error": str(e)})
