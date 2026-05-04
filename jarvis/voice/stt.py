"""Speech-to-text using faster-whisper with VAD-based silence detection."""
import numpy as np
import queue
import threading
from jarvis.utils.config import get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = float(get("voice", "vad_silence_threshold", 1.5))
CHUNK_DURATION = 0.1  # seconds per audio chunk
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)
SILENCE_RMS = 0.01  # RMS below this = silence
MAX_RECORD_SECS = 30


class SpeechToText:
    def __init__(self, model_size: str | None = None):
        self._model_size = model_size or get("voice", "stt_model", "base.en")
        self._model = None
        self._lock = threading.Lock()

    def _load_model(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel
                log.info("Loading Whisper model: %s", self._model_size)
                self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
                log.info("Whisper model loaded")

    def listen_and_transcribe(self) -> str:
        """Record until silence, then transcribe. Returns transcript string."""
        self._load_model()
        audio = self._record_utterance()
        if audio is None or len(audio) < SAMPLE_RATE * 0.3:
            return ""
        return self._transcribe(audio)

    def _record_utterance(self) -> np.ndarray | None:
        try:
            import sounddevice as sd

            log.debug("Recording utterance...")
            chunks: list[np.ndarray] = []
            silence_chunks = 0
            max_silence = int(SILENCE_THRESHOLD / CHUNK_DURATION)
            max_chunks = int(MAX_RECORD_SECS / CHUNK_DURATION)
            has_speech = False

            q: queue.Queue = queue.Queue()

            def callback(indata, frames, time_info, status):
                q.put(indata.copy())

            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                blocksize=CHUNK_SAMPLES, callback=callback):
                while len(chunks) < max_chunks:
                    chunk = q.get(timeout=5.0)
                    rms = float(np.sqrt(np.mean(chunk ** 2)))
                    chunks.append(chunk)
                    if rms > SILENCE_RMS:
                        has_speech = True
                        silence_chunks = 0
                    elif has_speech:
                        silence_chunks += 1
                        if silence_chunks >= max_silence:
                            break

            if not has_speech:
                return None
            return np.concatenate(chunks).flatten()
        except Exception as e:
            log.error("Recording error: %s", e)
            return None

    def _transcribe(self, audio: np.ndarray) -> str:
        try:
            segments, info = self._model.transcribe(audio, beam_size=5, language="en")
            text = " ".join(seg.text.strip() for seg in segments).strip()
            log.debug("Transcribed: %s", text[:100])
            return text
        except Exception as e:
            log.error("Transcription error: %s", e)
            return ""
