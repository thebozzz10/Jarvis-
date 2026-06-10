"""Floating HUD overlay — appears during listening/processing."""
import tkinter as tk
import math, time, threading
from jarvis.utils.config import get

ACCENT = get("ui", "accent_color", "#00D4FF")
BG = get("ui", "bg_color", "#0A0E1A")


class HUDOverlay:
    def __init__(self):
        self._root: tk.Tk | None = None
        self._label: tk.Label | None = None
        self._canvas: tk.Canvas | None = None
        self._visible = False
        self._state = "idle"
        self._frame = 0

    def build(self):
        self._root = tk.Tk()
        self._root.overrideredirect(True)  # no window decorations
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.92)
        self._root.configure(bg=BG)
        self._root.geometry("400x70+{}+{}".format(
            self._root.winfo_screenwidth() - 420,
            self._root.winfo_screenheight() - 120,
        ))
        self._root.withdraw()

        # Border frame
        border = tk.Frame(self._root, bg=ACCENT, bd=1)
        border.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner = tk.Frame(border, bg=BG)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        self._canvas = tk.Canvas(inner, bg=BG, highlightthickness=0, width=60, height=60)
        self._canvas.pack(side=tk.LEFT, padx=(8, 0))

        self._label = tk.Label(inner, text="JARVIS ONLINE", fg=ACCENT, bg=BG,
                                font=("SF Mono", 13, "bold"))
        self._label.pack(side=tk.LEFT, padx=12)

        self._animate()

    def _animate(self):
        if self._canvas:
            self._canvas.delete("all")
            t = time.time()
            cx, cy = 30, 30
            if self._state == "listening":
                for i in range(5):
                    h = 6 + 12 * abs(math.sin(t * 5 + i))
                    x = 10 + i * 10
                    self._canvas.create_rectangle(x, cy - h, x + 6, cy + h,
                                                  fill=ACCENT, outline="")
            elif self._state == "thinking":
                for i in range(6):
                    angle = math.radians((t * 200 + i * 60) % 360)
                    x = cx + 18 * math.cos(angle)
                    y = cy + 18 * math.sin(angle)
                    alpha = (i / 6)
                    r = int(3 + alpha * 3)
                    color = self._fade(ACCENT, alpha)
                    self._canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
            else:
                pulse = 0.7 + 0.3 * math.sin(t * 2)
                r = int(14 * pulse)
                self._canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                         fill=ACCENT, outline="")
        if self._root:
            self._root.after(40, self._animate)

    def show(self, state: str = "listening", message: str = "LISTENING..."):
        self._state = state
        if self._label:
            self._label.configure(text=message)
        if self._root:
            self._root.deiconify()
            self._visible = True

    def hide(self):
        if self._root:
            self._root.withdraw()
            self._visible = False

    def run(self):
        if self._root:
            self._root.mainloop()

    @staticmethod
    def _fade(hex_color: str, alpha: float) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, int(r * (0.2 + alpha * 0.8)))
        g = max(0, int(g * (0.2 + alpha * 0.8)))
        b = max(0, int(b * (0.2 + alpha * 0.8)))
        return f"#{r:02x}{g:02x}{b:02x}"
