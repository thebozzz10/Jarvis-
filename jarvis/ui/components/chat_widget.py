"""Scrollable chat message history with streaming text display."""
import tkinter as tk
from tkinter import font as tkfont
from jarvis.utils.config import get

BG = get("ui", "bg_color", "#0A0E1A")
PANEL = get("ui", "panel_color", "#0F1729")
ACCENT = get("ui", "accent_color", "#00D4FF")
SECONDARY = get("ui", "secondary_color", "#0080FF")
TEXT_COLOR = get("ui", "text_color", "#E8F4FF")
MUTED = get("ui", "muted_color", "#7BA7C8")
BORDER = "#1A3050"
TOOL_COLOR = "#FFB347"
TOOL_RESULT_COLOR = "#3A5570"


class ChatWidget(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG, **kwargs)
        self._build()

    def _build(self):
        self._text = tk.Text(
            self,
            bg=PANEL,
            fg=TEXT_COLOR,
            font=("SF Pro Display", 13),
            wrap=tk.WORD,
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=12,
            cursor="arrow",
            state=tk.DISABLED,
            selectbackground=SECONDARY,
            insertbackground=ACCENT,
        )
        scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self._text.yview,
                                 bg=PANEL, troughcolor=BG, bd=0, width=6)
        self._text.configure(yscrollcommand=scrollbar.set)

        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure text tags
        self._text.tag_configure("jarvis_name", foreground=ACCENT, font=("SF Mono", 11, "bold"))
        self._text.tag_configure("jarvis_msg", foreground=TEXT_COLOR, font=("SF Pro Display", 13))
        self._text.tag_configure("user_name", foreground=SECONDARY, font=("SF Mono", 11, "bold"))
        self._text.tag_configure("user_msg", foreground=TEXT_COLOR, font=("SF Pro Display", 13))
        self._text.tag_configure("tool_call", foreground=TOOL_COLOR, font=("SF Mono", 11))
        self._text.tag_configure("tool_result", foreground=TOOL_RESULT_COLOR, font=("SF Mono", 10))
        self._text.tag_configure("separator", foreground=BORDER)
        self._text.tag_configure("timestamp", foreground="#2A4060", font=("SF Mono", 9))
        self._text.tag_configure("error", foreground="#FF6B35", font=("SF Mono", 11))

        self._streaming_active = False

    def _insert(self, text: str, tag: str = ""):
        self._text.configure(state=tk.NORMAL)
        if tag:
            self._text.insert(tk.END, text, tag)
        else:
            self._text.insert(tk.END, text)
        self._text.see(tk.END)
        self._text.configure(state=tk.DISABLED)

    def add_jarvis_message_start(self):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        self._insert("\n")
        self._insert("JARVIS", "jarvis_name")
        self._insert(f"  {ts}\n", "timestamp")
        self._streaming_active = True

    def stream_jarvis_chunk(self, chunk: str):
        if self._streaming_active:
            self._insert(chunk, "jarvis_msg")

    def end_jarvis_message(self):
        self._streaming_active = False
        self._insert("\n")

    def add_user_message(self, text: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M")
        self._insert("\n")
        self._insert("YOU", "user_name")
        self._insert(f"  {ts}\n", "timestamp")
        self._insert(text + "\n", "user_msg")

    def add_tool_call(self, tool_name: str, inputs: dict):
        import json
        self._insert(f"  ▶ {tool_name}", "tool_call")
        short = str(inputs)[:80]
        self._insert(f"  {short}\n", "tool_result")

    def add_tool_result(self, tool_name: str, result: str):
        self._insert(f"  ◀ {result[:120]}\n", "tool_result")

    def add_separator(self):
        self._insert("\n" + "─" * 60 + "\n", "separator")

    def add_error(self, msg: str):
        self._insert(f"\n[ERROR] {msg}\n", "error")

    def clear(self):
        self._text.configure(state=tk.NORMAL)
        self._text.delete(1.0, tk.END)
        self._text.configure(state=tk.DISABLED)
