"""Bottom status bar widget."""
import tkinter as tk
from jarvis.utils.config import MODEL, get

BG = get("ui", "bg_color", "#0A0E1A")
MUTED = get("ui", "muted_color", "#7BA7C8")
ACCENT = get("ui", "accent_color", "#00D4FF")
BORDER = "#1A3050"


class StatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG, height=28, **kwargs)
        self.pack_propagate(False)
        self._build()
        self._start_time = None
        self._tick()

    def _build(self):
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(self, bg=BG)
        inner.pack(fill=tk.X, padx=12, pady=4)

        self._status_dot = tk.Label(inner, text="●", fg=MUTED, bg=BG, font=("SF Mono", 9))
        self._status_dot.pack(side=tk.LEFT)

        self._status_label = tk.Label(inner, text=" IDLE", fg=MUTED, bg=BG, font=("SF Mono", 9))
        self._status_label.pack(side=tk.LEFT)

        sep2 = tk.Label(inner, text="  |  ", fg=BORDER, bg=BG, font=("SF Mono", 9))
        sep2.pack(side=tk.LEFT)

        tk.Label(inner, text=f"MODEL: {MODEL}", fg=MUTED, bg=BG, font=("SF Mono", 9)).pack(side=tk.LEFT)

        self._mem_label = tk.Label(inner, text="  |  MEMORIES: 0", fg=MUTED, bg=BG, font=("SF Mono", 9))
        self._mem_label.pack(side=tk.LEFT)

        self._time_label = tk.Label(inner, text="", fg=MUTED, bg=BG, font=("SF Mono", 9))
        self._time_label.pack(side=tk.RIGHT)

    def set_status(self, status: str, color: str = MUTED):
        self._status_dot.configure(fg=color)
        self._status_label.configure(text=f" {status.upper()}", fg=color)

    def set_memory_count(self, count: int):
        self._mem_label.configure(text=f"  |  MEMORIES: {count}")

    def _tick(self):
        import time
        t = time.strftime("%H:%M:%S")
        self._time_label.configure(text=t)
        self.after(1000, self._tick)
