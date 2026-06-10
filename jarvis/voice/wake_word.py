"""Wake word detection using Picovoice Porcupine."""
import threading
from typing import Callable
from jarvis.utils.config import PORCUPINE_ACCESS_KEY, get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

WAKE_WORD = get("voice", "wake_word", "jarvis")


class WakeWordDetector:
    def __init__(self, on_detected: Callable):
        self._on_detected = on_detected
        self._thread: threading.Thread | None = None
        self._running = False
        self._porcupine = None
        self._recorder = None

    def start(self):
        if not PORCUPINE_ACCESS_KEY:
            log.warning("PORCUPINE_ACCESS_KEY not set — wake word disabled")
            return
        self._running = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True, name="wake-word")
        self._thread.start()
        log.info("Wake word detector started: '%s'", WAKE_WORD)

    def stop(self):
        self._running = False
        if self._recorder:
            try:
                self._recorder.stop()
            except Exception:
                pass
        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass

    def _detect_loop(self):
        try:
            import pvporcupine
            import pvrecorder

            self._porcupine = pvporcupine.create(
                access_key=PORCUPINE_ACCESS_KEY,
                keywords=[WAKE_WORD],
            )
            self._recorder = pvrecorder.PvRecorder(
                frame_length=self._porcupine.frame_length,
                device_index=-1,
            )
            self._recorder.start()
            log.info("Listening for wake word...")

            while self._running:
                pcm = self._recorder.read()
                result = self._porcupine.process(pcm)
                if result >= 0:
                    log.info("Wake word detected!")
                    try:
                        self._on_detected()
                    except Exception as e:
                        log.error("Wake word callback error: %s", e)

        except ImportError:
            log.error("pvporcupine/pvrecorder not installed — wake word unavailable")
        except Exception as e:
            log.error("Wake word detector error: %s", e)
        finally:
            self.stop()
