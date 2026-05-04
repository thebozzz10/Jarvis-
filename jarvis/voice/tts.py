"""Text-to-speech using edge-tts with a queued playback worker."""
import asyncio
import io
import queue
import threading
import tempfile
import os
from jarvis.utils.config import TTS_VOICE
from jarvis.utils.logger import get_logger

log = get_logger(__name__)


class TextToSpeech:
    def __init__(self, voice: str = TTS_VOICE):
        self._voice = voice
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._playing = threading.Event()
        self._stop_flag = threading.Event()

    def start(self):
        self._thread = threading.Thread(target=self._worker, daemon=True, name="tts")
        self._thread.start()
        log.info("TTS started with voice: %s", self._voice)

    def speak(self, text: str):
        if text.strip():
            self._queue.put(text)

    def stop_current(self):
        """Interrupt current playback (barge-in support)."""
        self._stop_flag.set()

    def _worker(self):
        while True:
            text = self._queue.get()
            if text is None:
                break
            self._stop_flag.clear()
            self._playing.set()
            try:
                asyncio.run(self._synthesize_and_play(text))
            except Exception as e:
                log.error("TTS error: %s", e)
            finally:
                self._playing.clear()

    async def _synthesize_and_play(self, text: str):
        try:
            import edge_tts
            import sounddevice as sd
            import numpy as np
            from pydub import AudioSegment

            communicate = edge_tts.Communicate(text, self._voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
                    if self._stop_flag.is_set():
                        return

            if not audio_data:
                return

            # Convert mp3 bytes → numpy array for sounddevice
            audio_seg = AudioSegment.from_mp3(io.BytesIO(audio_data))
            audio_seg = audio_seg.set_channels(1).set_frame_rate(22050)
            samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32) / 32768.0

            if self._stop_flag.is_set():
                return

            sd.play(samples, samplerate=22050)
            # Poll stop flag while playing
            while sd.get_stream().active:
                if self._stop_flag.is_set():
                    sd.stop()
                    return
                await asyncio.sleep(0.05)

        except Exception as e:
            log.error("TTS synthesis error: %s", e)

    def stop(self):
        self._queue.put(None)
