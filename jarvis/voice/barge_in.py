"""Real-time barge-in: detects voice while Jarvis is speaking and interrupts."""
import threading
import time
import numpy as np
from typing import Callable
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

SAMPLE_RATE = 16000
CHUNK_DURATION = 0.05
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)
SPEECH_RMS = 0.025
CONSECUTIVE_FRAMES = 6  # ~300ms of consistent speech


class BargeInDetector:
    """Continuously monitors mic; calls interrupt_callback() if speech detected while is_speaking is True."""

    def __init__(self, is_speaking_fn: Callable[[], bool], on_interrupt: Callable[[], None]):
        self._is_speaking_fn = is_speaking_fn
        self._on_interrupt = on_interrupt
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="barge-in")
        self._thread.start()
        log.info("Barge-in detector started")

    def stop(self):
        self._running = False

    def _loop(self):
        try:
            import sounddevice as sd
            import queue as q

            audio_q: q.Queue = q.Queue()

            def callback(indata, frames, time_info, status):
                audio_q.put(indata.copy())

            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                blocksize=CHUNK_SAMPLES, callback=callback):
                consecutive = 0
                while self._running:
                    try:
                        chunk = audio_q.get(timeout=1.0)
                    except q.Empty:
                        continue
                    if not self._is_speaking_fn():
                        consecutive = 0
                        continue
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    if rms > SPEECH_RMS:
                        consecutive += 1
                        if consecutive >= CONSECUTIVE_FRAMES:
                            log.info("Barge-in detected — interrupting")
                            try:
                                self._on_interrupt()
                            except Exception as e:
                                log.error("Interrupt callback error: %s", e)
                            consecutive = 0
                            time.sleep(0.5)
                    else:
                        consecutive = max(0, consecutive - 1)
        except Exception as e:
            log.warning("Barge-in detector unavailable: %s", e)
