"""Proactive monitor — background daemon that watches the world and speaks up.

Tracks:
  - Calendar (upcoming events → reminders 5 min before)
  - Active app changes (logs context for memory)
  - Battery low / system stress
  - Idle vs active time
"""
import threading
import time
import subprocess
from datetime import datetime, timedelta
from jarvis.core.event_bus import bus
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

CHECK_INTERVAL = 60  # seconds


class ProactiveMonitor:
    def __init__(self, on_alert):
        self._on_alert = on_alert
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_active_app = ""
        self._notified_events: set[str] = set()
        self._battery_warned = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="proactive")
        self._thread.start()
        log.info("Proactive monitor started")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self._check_calendar()
                self._check_battery()
                self._track_active_app()
            except Exception as e:
                log.debug("Monitor cycle error: %s", e)
            time.sleep(CHECK_INTERVAL)

    def _check_calendar(self):
        try:
            script = '''
tell application "Calendar"
    set startDate to (current date)
    set endDate to startDate + (10 * minutes)
    set output to ""
    repeat with cal in (every calendar)
        try
            set evts to (every event of cal whose start date is greater than startDate and start date is less than endDate)
            repeat with evt in evts
                set output to output & (summary of evt) & "|" & (start date of evt as string) & linefeed
            end repeat
        end try
    end repeat
    return output
end tell
'''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            for line in result.stdout.split("\n"):
                if "|" in line:
                    title, start = line.split("|", 1)
                    key = f"{title}@{start}"
                    if key not in self._notified_events:
                        self._notified_events.add(key)
                        self._on_alert(f"You have an event soon: {title.strip()} at {start.strip()}")
        except Exception:
            pass

    def _check_battery(self):
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt is None:
                return
            if batt.percent < 20 and not batt.power_plugged:
                if not self._battery_warned:
                    self._battery_warned = True
                    self._on_alert(f"Battery is low at {int(batt.percent)}%, sir. May I suggest plugging in?")
            elif batt.power_plugged or batt.percent > 30:
                self._battery_warned = False
        except Exception:
            pass

    def _track_active_app(self):
        try:
            from jarvis.utils.macos_utils import get_frontmost_app
            current = get_frontmost_app()
            if current and current != self._last_active_app:
                log.debug("Active app changed: %s → %s", self._last_active_app, current)
                self._last_active_app = current
        except Exception:
            pass
