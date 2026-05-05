"""Main Jarvis chat window — high-tech dark theme."""
import asyncio
import threading
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from jarvis.core.event_bus import (bus, JARVIS_TEXT_CHUNK, JARVIS_DONE,
                                    TOOL_CALLED, TOOL_RESULT, STATUS_CHANGED,
                                    LISTENING_START, LISTENING_STOP, USER_SPEECH)
from jarvis.ui.components.chat_widget import ChatWidget
from jarvis.ui.components.arc_reactor import ArcReactor as WaveformWidget
from jarvis.ui.components.arc_reactor import ArcReactor as WF
from jarvis.ui.components.status_bar import StatusBar
from jarvis.utils.config import get
from jarvis.utils.logger import get_logger

log = get_logger(__name__)

BG = get("ui", "bg_color", "#0A0E1A")
PANEL = get("ui", "panel_color", "#0F1729")
ACCENT = get("ui", "accent_color", "#00D4FF")
SECONDARY = get("ui", "secondary_color", "#0080FF")
TEXT_COLOR = get("ui", "text_color", "#E8F4FF")
MUTED = get("ui", "muted_color", "#7BA7C8")
BORDER = "#1A3050"
W = int(get("ui", "window_width", 800))
H = int(get("ui", "window_height", 600))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow:
    def __init__(self, on_user_input=None):
        self._on_user_input = on_user_input
        self._root: ctk.CTk | None = None
        self._chat: ChatWidget | None = None
        self._waveform: WaveformWidget | None = None
        self._status: StatusBar | None = None
        self._input: ctk.CTkEntry | None = None
        self._visible = False
        self._update_queue: list[tuple] = []
        self._lock = threading.Lock()

    def build(self):
        self._root = ctk.CTk()
        self._root.title("JARVIS")
        self._root.geometry(f"{W}x{H}")
        self._root.configure(fg_color=BG)
        self._root.resizable(True, True)
        self._root.protocol("WM_DELETE_WINDOW", self.hide)

        self._setup_layout()
        self._subscribe_events()
        self._root.withdraw()  # start hidden

        log.info("Main window built")

    def _setup_layout(self):
        root = self._root

        # ── Title bar ──────────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(root, fg_color="#080C16", corner_radius=0, height=40)
        title_frame.pack(fill=tk.X, side=tk.TOP)
        title_frame.pack_propagate(False)

        ctk.CTkLabel(
            title_frame, text="  J A R V I S",
            font=("SF Mono", 16, "bold"), text_color=ACCENT,
        ).pack(side=tk.LEFT, padx=12)

        self._title_status = ctk.CTkLabel(
            title_frame, text="● ONLINE",
            font=("SF Mono", 11), text_color="#00FF88",
        )
        self._title_status.pack(side=tk.LEFT, padx=8)

        ctk.CTkLabel(
            title_frame, text="v1.0",
            font=("SF Mono", 10), text_color=MUTED,
        ).pack(side=tk.RIGHT, padx=16)

        # ── ARC Reactor ───────────────────────────────────────────────────
        self._waveform = WaveformWidget(root, width=W - 20, height=200)
        self._waveform.pack(fill=tk.X, padx=10, pady=(6, 0))

        # ── Chat history ──────────────────────────────────────────────────
        self._chat = ChatWidget(root)
        self._chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # ── Input bar ────────────────────────────────────────────────────
        input_frame = ctk.CTkFrame(root, fg_color=PANEL, corner_radius=8, height=50)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
        input_frame.pack_propagate(False)

        mic_btn = ctk.CTkButton(
            input_frame, text="🎤", width=40, height=36,
            fg_color="#1A3050", hover_color="#1E3C66",
            font=("SF Pro Display", 16), corner_radius=6,
            command=self._toggle_voice,
        )
        mic_btn.pack(side=tk.LEFT, padx=(8, 4), pady=7)

        self._input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a command or ask anything...",
            font=("SF Pro Display", 13),
            fg_color="#141E35", border_color=BORDER,
            text_color=TEXT_COLOR, placeholder_text_color=MUTED,
            corner_radius=6, border_width=1,
        )
        self._input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=7)
        self._input.bind("<Return>", self._on_enter)

        send_btn = ctk.CTkButton(
            input_frame, text="SEND ▶", width=80, height=36,
            fg_color=SECONDARY, hover_color=ACCENT,
            font=("SF Mono", 11, "bold"), corner_radius=6,
            text_color="#ffffff", command=self._submit,
        )
        send_btn.pack(side=tk.RIGHT, padx=(4, 8), pady=7)

        # ── Status bar ───────────────────────────────────────────────────
        self._status = StatusBar(root)
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

        self._update_memory_count()

    def _subscribe_events(self):
        bus.subscribe(JARVIS_TEXT_CHUNK, lambda d: self._queue_update("chunk", d))
        bus.subscribe(JARVIS_DONE, lambda d: self._queue_update("done", d))
        bus.subscribe(TOOL_CALLED, lambda d: self._queue_update("tool_call", d))
        bus.subscribe(TOOL_RESULT, lambda d: self._queue_update("tool_result", d))
        bus.subscribe(LISTENING_START, lambda d: self._queue_update("listening", True))
        bus.subscribe(LISTENING_STOP, lambda d: self._queue_update("listening", False))
        bus.subscribe(USER_SPEECH, lambda d: self._queue_update("user_speech", d))
        bus.subscribe(STATUS_CHANGED, lambda d: self._queue_update("status", d))

        self._root.after(50, self._process_update_queue)

    def _queue_update(self, kind: str, data):
        with self._lock:
            self._update_queue.append((kind, data))

    def _process_update_queue(self):
        with self._lock:
            items = self._update_queue[:]
            self._update_queue.clear()
        for kind, data in items:
            self._apply_update(kind, data)
        self._root.after(50, self._process_update_queue)

    def _apply_update(self, kind: str, data):
        if kind == "chunk":
            if not self._jarvis_started:
                self._chat.add_jarvis_message_start()
                self._jarvis_started = True
            self._chat.stream_jarvis_chunk(data)
        elif kind == "done":
            self._chat.end_jarvis_message()
            self._jarvis_started = False
            self._waveform.set_state(WF.IDLE)
            self._status.set_status("IDLE", MUTED)
            self._update_memory_count()
        elif kind == "tool_call":
            self._chat.add_tool_call(data.get("name", ""), data.get("input", {}))
        elif kind == "tool_result":
            self._chat.add_tool_result(data.get("name", ""), data.get("result", ""))
        elif kind == "listening":
            if data:
                self._waveform.set_state(WF.LISTENING)
                self._status.set_status("LISTENING", "#00FF88")
            else:
                self._waveform.set_state(WF.THINKING)
                self._status.set_status("PROCESSING", ACCENT)
        elif kind == "user_speech":
            self._chat.add_user_message(data)
            self._waveform.set_state(WF.THINKING)
            self._status.set_status("THINKING", ACCENT)
        elif kind == "status":
            self._status.set_status(str(data))

    _jarvis_started = False

    def _on_enter(self, event=None):
        self._submit()

    def _submit(self):
        text = self._input.get().strip() if self._input else ""
        if not text:
            return
        self._input.delete(0, tk.END)
        self._chat.add_user_message(text)
        self._waveform.set_state(WF.THINKING)
        self._status.set_status("THINKING", ACCENT)
        if self._on_user_input:
            threading.Thread(target=self._on_user_input, args=(text,), daemon=True).start()

    def _toggle_voice(self):
        bus.publish(LISTENING_START)

    def _update_memory_count(self):
        try:
            from jarvis.memory.memory_store import get_top_memories
            count = len(get_top_memories(limit=9999))
            if self._status:
                self._status.set_memory_count(count)
        except Exception:
            pass

    def show(self):
        if self._root:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
            self._visible = True

    def hide(self):
        if self._root:
            self._root.withdraw()
            self._visible = False

    def toggle(self):
        if self._visible:
            self.hide()
        else:
            self.show()

    def run(self):
        if self._root:
            self._root.mainloop()

    def destroy(self):
        if self._root:
            self._root.destroy()
