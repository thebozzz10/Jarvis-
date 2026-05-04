"""
JARVIS — main entry point.

Threading model:
  MAIN THREAD  → rumps menu bar (AppKit run loop, macOS requirement)
  THREAD 2     → customtkinter UI window (separate tk mainloop)
  THREAD 3     → pvporcupine wake word detector
  THREAD 4     → STT recorder (triggered by LISTENING_START event)
  THREAD 5     → asyncio event loop for JarvisAgent
  THREAD 6     → TTS playback queue
  THREAD 7     → pynput global hotkey

Usage:
  python -m jarvis.main                  # full system
  python -m jarvis.main --no-voice       # skip wake word + STT/TTS
  python -m jarvis.main --debug          # verbose logging
  python -m jarvis.main --no-voice --no-menubar  # text-only terminal mode
"""
import argparse
import asyncio
import signal
import sys
import threading
from jarvis.utils.logger import get_logger
from jarvis.utils.config import ANTHROPIC_API_KEY, get

log = get_logger(__name__)

_shutdown_event = threading.Event()


def parse_args():
    p = argparse.ArgumentParser(description="JARVIS AI Assistant")
    p.add_argument("--no-voice", action="store_true", help="Disable voice I/O")
    p.add_argument("--no-menubar", action="store_true", help="Disable menu bar")
    p.add_argument("--debug", action="store_true", help="Verbose logging")
    return p.parse_args()


def _check_api_key():
    if not ANTHROPIC_API_KEY:
        print("[JARVIS] ERROR: ANTHROPIC_API_KEY not set. Copy .env.example → .env and add your key.")
        sys.exit(1)


def _start_event_bus():
    from jarvis.core.event_bus import bus
    bus.start()
    log.info("EventBus started")
    return bus


def _init_db():
    from jarvis.memory.database import init_db
    init_db()


def _build_agent(registry, session_id: str):
    from jarvis.core.agent import JarvisAgent
    return JarvisAgent(registry, session_id)


def _start_agent_thread(agent, tts=None):
    """Run an asyncio event loop in a dedicated thread to serve agent requests."""
    from jarvis.core.event_bus import bus, USER_SPEECH, JARVIS_TEXT_CHUNK, JARVIS_DONE
    import queue as q_mod

    request_queue: q_mod.Queue = q_mod.Queue()

    def _on_speech(text: str):
        request_queue.put(("text", text, "voice"))

    def _on_text(text: str):
        request_queue.put(("text", text, "text"))

    bus.subscribe(USER_SPEECH, _on_speech)
    bus.subscribe("USER_SPEECH_TEXT", _on_text)

    def _worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run():
            while not _shutdown_event.is_set():
                try:
                    item = request_queue.get(timeout=0.5)
                except Exception:
                    continue
                _, text, mode = item
                log.info("Processing: %.80s", text)

                chunks = []

                def on_chunk(c: str):
                    bus.publish(JARVIS_TEXT_CHUNK, c)
                    if tts and mode == "voice":
                        chunks.append(c)

                try:
                    full = await agent.process(text, interaction_mode=mode, on_chunk=on_chunk)
                    bus.publish(JARVIS_DONE, full)
                    if tts and mode == "voice":
                        tts.speak(full)
                except Exception as e:
                    log.error("Agent error: %s", e)
                    bus.publish(JARVIS_DONE, "")

        loop.run_until_complete(run())
        loop.close()

    t = threading.Thread(target=_worker, daemon=True, name="agent")
    t.start()
    return t, request_queue


def _start_stt_voice_thread(stt, tts):
    from jarvis.core.event_bus import bus, LISTENING_START, LISTENING_STOP, USER_SPEECH

    def _listener(data=None):
        if tts:
            tts.stop_current()
        bus.publish(LISTENING_STOP)
        try:
            text = stt.listen_and_transcribe()
        except Exception as e:
            log.error("STT error: %s", e)
            return
        if text.strip():
            bus.publish(USER_SPEECH, text)
        else:
            log.debug("No speech detected")

    bus.subscribe(LISTENING_START, lambda d: threading.Thread(
        target=_listener, daemon=True, name="stt"
    ).start())


def _start_hotkey(toggle_fn):
    from jarvis.utils.hotkey import GlobalHotkey
    hotkey = get("ui", "hotkey", "<cmd>+<space>")
    hk = GlobalHotkey(hotkey, toggle_fn)
    hk.start()
    return hk


def _run_ui_thread(window):
    """Run the customtkinter window in its own thread."""
    window.build()
    window.run()


def main():
    args = parse_args()
    _check_api_key()

    if args.debug:
        import logging
        logging.getLogger("jarvis").setLevel(logging.DEBUG)

    log.info("=" * 50)
    log.info("  J A R V I S  —  Starting up")
    log.info("=" * 50)

    _init_db()
    bus = _start_event_bus()

    # ── Tool registry + agent ─────────────────────────────────────────────
    from jarvis.core.tool_registry import build_registry
    from jarvis.memory.memory_store import create_session

    registry = build_registry()
    session_id = create_session()
    log.info("Session: %s", session_id)

    # ── TTS / STT / Wake word ─────────────────────────────────────────────
    tts = None
    if not args.no_voice:
        try:
            from jarvis.voice.tts import TextToSpeech
            tts = TextToSpeech()
            tts.start()
        except Exception as e:
            log.warning("TTS unavailable: %s", e)
            tts = None

    agent = _build_agent(registry, session_id)
    agent_thread, _ = _start_agent_thread(agent, tts)

    if not args.no_voice:
        try:
            from jarvis.voice.stt import SpeechToText
            from jarvis.voice.wake_word import WakeWordDetector

            stt = SpeechToText()
            _start_stt_voice_thread(stt, tts)

            def _on_wake():
                from jarvis.core.event_bus import bus, LISTENING_START
                bus.publish(LISTENING_START)

            wake = WakeWordDetector(on_detected=_on_wake)
            wake.start()
        except Exception as e:
            log.warning("Voice input unavailable: %s", e)

    # ── UI window (own thread) ────────────────────────────────────────────
    window = None
    if not args.no_menubar:
        from jarvis.ui.main_window import MainWindow
        from jarvis.core.event_bus import bus as _bus, USER_SPEECH

        def on_user_text(text: str):
            _bus.publish("USER_SPEECH_TEXT", text)

        window = MainWindow(on_user_input=on_user_text)
        ui_thread = threading.Thread(target=_run_ui_thread, args=(window,), daemon=True, name="ui")
        ui_thread.start()

        _start_hotkey(window.toggle)

        log.info("UI window started")

    # ── Announce startup ──────────────────────────────────────────────────
    def _announce():
        import time
        time.sleep(2)
        if tts:
            tts.speak("JARVIS online. All systems nominal. How can I assist you?")
        else:
            log.info("JARVIS online.")
        from jarvis.core.event_bus import bus, STATUS_CHANGED
        bus.publish(STATUS_CHANGED, {"status": "Online"})

    threading.Thread(target=_announce, daemon=True, name="startup").start()

    # ── Signal handling ───────────────────────────────────────────────────
    def _shutdown(sig, frame):
        log.info("Shutdown signal received")
        _shutdown_event.set()
        if tts:
            tts.stop()
        bus.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ── Menu bar (blocks main thread on macOS) ────────────────────────────
    if not args.no_menubar:
        try:
            from jarvis.ui.menu_bar import JarvisMenuBar
            menu_bar = JarvisMenuBar(
                on_toggle_window=window.toggle if window else None,
                on_quit=lambda: _shutdown(None, None),
            )
            log.info("Menu bar starting (main thread)")
            menu_bar.run()
        except ImportError:
            log.warning("rumps not available — running without menu bar")
            _shutdown_event.wait()
    else:
        log.info("Running in headless mode — press Ctrl+C to quit")
        _shutdown_event.wait()


if __name__ == "__main__":
    main()
