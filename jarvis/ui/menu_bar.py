"""macOS menu bar application using rumps. Must own the main thread."""
import threading
import rumps
from jarvis.core.event_bus import bus, HOTKEY_TRIGGERED, LISTENING_START, STATUS_CHANGED
from jarvis.utils.config import MODEL, get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

ACCENT = get("ui", "accent_color", "#00D4FF")
VERSION = get("jarvis", "version", "1.0.0")


class JarvisMenuBar(rumps.App):
    def __init__(self, on_toggle_window=None, on_quit=None, window=None):
        super().__init__("J", quit_button=None)
        self._on_toggle_window = on_toggle_window
        self._on_quit_cb = on_quit
        self._tk_window = window
        self._status_text = "Online"
        self._memory_count = 0
        self._build_menu()
        self._subscribe()
        if window:
            # Pump the tkinter event loop from the main AppKit thread (~60 fps)
            self._tk_timer = rumps.Timer(self._pump_tk, 0.016)
            self._tk_timer.start()

    def _build_menu(self):
        self.menu = [
            rumps.MenuItem("Open JARVIS Window", callback=self._open_window),
            None,  # separator
            rumps.MenuItem(f"● Status: Online"),
            rumps.MenuItem(f"Model: {MODEL}"),
            rumps.MenuItem(f"Memories: 0"),
            None,
            rumps.MenuItem("Push to Talk", callback=self._push_to_talk),
            rumps.MenuItem("Analyze Screen", callback=self._analyze_screen),
            rumps.MenuItem("Analyze Clipboard", callback=self._analyze_clipboard),
            None,
            rumps.MenuItem("Quit JARVIS", callback=self._quit),
        ]

    def _subscribe(self):
        bus.subscribe(STATUS_CHANGED, self._on_status_changed)

    def _pump_tk(self, _):
        if self._tk_window:
            self._tk_window.update_once()

    def _on_status_changed(self, data):
        if isinstance(data, dict):
            status = data.get("status", "")
            count = data.get("memory_count")
            if status:
                self._status_text = status
                self.menu["● Status: Online"].title = f"● Status: {status}"
            if count is not None:
                self._memory_count = count
                self.menu["Memories: 0"].title = f"Memories: {count}"

    @rumps.clicked("Open JARVIS Window")
    def _open_window(self, _):
        if self._on_toggle_window:
            self._on_toggle_window()

    @rumps.clicked("Push to Talk")
    def _push_to_talk(self, _):
        bus.publish(LISTENING_START)

    @rumps.clicked("Analyze Screen")
    def _analyze_screen(self, _):
        bus.publish("USER_SPEECH_TEXT", "What is currently on my screen? Please describe it.")

    @rumps.clicked("Analyze Clipboard")
    def _analyze_clipboard(self, _):
        bus.publish("USER_SPEECH_TEXT", "Read my clipboard and tell me what's there.")

    @rumps.clicked("Quit JARVIS")
    def _quit(self, _):
        if self._on_quit_cb:
            self._on_quit_cb()
        rumps.quit_application()
