"""Thread-safe publish/subscribe event bus."""
import queue
import threading
from typing import Callable, Any
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

# Event types
USER_SPEECH = "USER_SPEECH"
JARVIS_TEXT_CHUNK = "JARVIS_TEXT_CHUNK"
JARVIS_DONE = "JARVIS_DONE"
TOOL_CALLED = "TOOL_CALLED"
TOOL_RESULT = "TOOL_RESULT"
LISTENING_START = "LISTENING_START"
LISTENING_STOP = "LISTENING_STOP"
HOTKEY_TRIGGERED = "HOTKEY_TRIGGERED"
STATUS_CHANGED = "STATUS_CHANGED"
ERROR = "ERROR"


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}
        self._queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def subscribe(self, event_type: str, handler: Callable):
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data: Any = None):
        self._queue.put((event_type, data))

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._dispatch_loop, daemon=True, name="event-bus")
        self._thread.start()

    def stop(self):
        self._running = False
        self._queue.put(None)  # poison pill

    def _dispatch_loop(self):
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            event_type, data = item
            with self._lock:
                handlers = list(self._handlers.get(event_type, []))
            for handler in handlers:
                try:
                    handler(data)
                except Exception as e:
                    log.error("EventBus handler error [%s]: %s", event_type, e)


# Global singleton
bus = EventBus()
