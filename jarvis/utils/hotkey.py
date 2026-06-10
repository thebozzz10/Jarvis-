"""Global hotkey listener using pynput."""
import threading
from typing import Callable
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class GlobalHotkey:
    def __init__(self, hotkey: str, callback: Callable):
        self._hotkey = hotkey
        self._callback = callback
        self._listener = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="hotkey")
        self._thread.start()
        log.info("Global hotkey registered: %s", self._hotkey)

    def _run(self):
        try:
            from pynput import keyboard

            def on_activate():
                log.debug("Hotkey triggered")
                try:
                    self._callback()
                except Exception as e:
                    log.error("Hotkey callback error: %s", e)

            with keyboard.GlobalHotKeys({self._hotkey: on_activate}) as h:
                self._listener = h
                h.join()
        except Exception as e:
            log.error("Hotkey listener crashed: %s", e)

    def stop(self):
        if self._listener:
            self._listener.stop()
