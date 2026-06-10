"""Music.app + Spotify control via AppleScript."""
import json
import subprocess
from jarvis.core.tool_registry import BaseTool


def _osa(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


class ControlMusic(BaseTool):
    name = "control_music"
    description = "Control music playback in Apple Music or Spotify: play, pause, skip, search, volume."
    input_schema = {
        "type": "object",
        "properties": {
            "app": {"type": "string", "enum": ["Music", "Spotify"], "default": "Music"},
            "action": {
                "type": "string",
                "enum": ["play", "pause", "next", "previous", "current", "play_track", "set_volume"],
            },
            "query": {"type": "string", "description": "Track/artist name (for play_track)"},
            "volume": {"type": "integer", "description": "0-100 (for set_volume)"},
        },
        "required": ["action"],
    }

    def run(self, action: str, app: str = "Music", query: str | None = None,
            volume: int | None = None) -> str:
        try:
            if action == "play":
                _osa(f'tell application "{app}" to play')
            elif action == "pause":
                _osa(f'tell application "{app}" to pause')
            elif action == "next":
                _osa(f'tell application "{app}" to next track')
            elif action == "previous":
                _osa(f'tell application "{app}" to previous track')
            elif action == "current":
                track = _osa(f'tell application "{app}" to (name of current track) & " — " & (artist of current track)')
                return json.dumps({"now_playing": track})
            elif action == "play_track" and query:
                if app == "Spotify":
                    # Spotify search and play first result
                    script = f'''
tell application "Spotify"
    play track "spotify:search:{query}"
end tell
'''
                else:
                    script = f'''
tell application "Music"
    set results to (search library 1 for "{query}")
    if (count of results) > 0 then
        play (item 1 of results)
    end if
end tell
'''
                _osa(script)
                return json.dumps({"success": True, "playing": query})
            elif action == "set_volume" and volume is not None:
                vol = max(0, min(100, volume))
                _osa(f'tell application "{app}" to set sound volume to {vol}')
                return json.dumps({"success": True, "volume": vol})
            return json.dumps({"success": True, "action": action})
        except Exception as e:
            return json.dumps({"error": str(e)})
