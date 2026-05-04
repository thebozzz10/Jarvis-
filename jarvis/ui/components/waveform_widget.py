"""Animated orb/waveform widget showing Jarvis status."""
import math
import time
import tkinter as tk
from jarvis.utils.config import get

ACCENT = get("ui", "accent_color", "#00D4FF")
BG = get("ui", "bg_color", "#0A0E1A")


class WaveformWidget(tk.Canvas):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"

    def __init__(self, parent, width: int = 760, height: int = 110, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._state = self.IDLE
        self._frame = 0
        self._animate()

    def set_state(self, state: str):
        self._state = state

    def _animate(self):
        self.delete("all")
        cx, cy = self.winfo_reqwidth() // 2, self.winfo_reqheight() // 2
        t = time.time()
        f = self._frame

        if self._state == self.IDLE:
            self._draw_idle(cx, cy, t)
        elif self._state == self.LISTENING:
            self._draw_listening(cx, cy, t)
        elif self._state == self.THINKING:
            self._draw_thinking(cx, cy, t)
        elif self._state == self.SPEAKING:
            self._draw_speaking(cx, cy, t)

        # Status label
        state_colors = {
            self.IDLE: "#3A5570",
            self.LISTENING: "#00FF88",
            self.THINKING: "#FFB347",
            self.SPEAKING: ACCENT,
        }
        color = state_colors.get(self._state, "#3A5570")
        label = self._state.upper()
        self.create_text(cx, cy + 42, text=f"● {label}", fill=color,
                         font=("SF Mono", 10, "bold"), anchor="center")

        self._frame += 1
        self.after(40, self._animate)  # ~25 fps

    def _draw_idle(self, cx, cy, t):
        # Slow pulsing core
        pulse = 0.8 + 0.2 * math.sin(t * 1.2)
        r = int(18 * pulse)
        glow_color = self._alpha_hex(ACCENT, 0.15)
        for i in range(3, 0, -1):
            gr = r + i * 8
            self.create_oval(cx - gr, cy - gr, cx + gr, cy + gr,
                             fill="", outline=self._darken(ACCENT, 0.2 * i), width=1)
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         fill=self._darken(ACCENT, 0.5), outline=ACCENT, width=2)

    def _draw_listening(self, cx, cy, t):
        # Waveform bars
        bars = 24
        bar_w = 6
        spacing = 14
        start_x = cx - (bars * spacing) // 2
        for i in range(bars):
            h = 10 + 22 * abs(math.sin(t * 4 + i * 0.5))
            x = start_x + i * spacing
            brightness = 0.6 + 0.4 * abs(math.sin(t * 3 + i * 0.4))
            color = self._mix_color(ACCENT, "#ffffff", brightness * 0.3)
            self.create_rectangle(x, cy - h, x + bar_w, cy + h,
                                  fill=color, outline="")

    def _draw_thinking(self, cx, cy, t):
        # Spinning arc segments
        n = 8
        for i in range(n):
            angle = (t * 180 + i * (360 / n)) % 360
            rad = math.radians(angle)
            r_inner, r_outer = 22, 34
            x1 = cx + r_inner * math.cos(rad)
            y1 = cy + r_inner * math.sin(rad)
            x2 = cx + r_outer * math.cos(rad)
            y2 = cy + r_outer * math.sin(rad)
            alpha = 0.3 + 0.7 * (i / n)
            color = self._darken(ACCENT, 1.0 - alpha)
            self.create_line(x1, y1, x2, y2, fill=color, width=3, capstyle=tk.ROUND)

        # Inner pulsing dot
        pulse = 0.85 + 0.15 * math.sin(t * 5)
        r = int(10 * pulse)
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=ACCENT, outline="")

    def _draw_speaking(self, cx, cy, t):
        # Ripple rings
        for i in range(4):
            phase = (t * 2 + i * 0.5) % 2.0
            r = int(15 + phase * 28)
            alpha = max(0, 1.0 - phase / 2.0)
            color = self._darken(ACCENT, 1.0 - alpha * 0.8)
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill="", outline=color, width=2)
        # Core orb
        self.create_oval(cx - 12, cy - 12, cx + 12, cy + 12,
                         fill=ACCENT, outline="#ffffff", width=1)

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _mix_color(c1: str, c2: str, t: float) -> str:
        c1 = c1.lstrip("#")
        c2 = c2.lstrip("#")
        r1, g1, b1 = (int(c1[i:i+2], 16) for i in (0, 2, 4))
        r2, g2, b2 = (int(c2[i:i+2], 16) for i in (0, 2, 4))
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _alpha_hex(hex_color: str, alpha: float) -> str:
        return hex_color
