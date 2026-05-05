"""ARC Reactor — animated holographic core with particle field.

Replaces the simple waveform widget with a JARVIS-grade visualisation:
  - Concentric rotating rings (different speeds)
  - Pulsing core with halo glow
  - Particle field orbiting the core
  - Reactive amplitude display when listening/speaking
"""
import math
import random
import time
import tkinter as tk
from jarvis.utils.config import get

ACCENT = get("ui", "accent_color", "#00D4FF")
SECONDARY = get("ui", "secondary_color", "#0080FF")
BG = get("ui", "bg_color", "#0A0E1A")
PANEL = get("ui", "panel_color", "#0F1729")


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color")

    def __init__(self, cx: float, cy: float):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.3, 1.4)
        self.x = cx
        self.y = cy
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.max_life = random.randint(30, 90)
        self.life = self.max_life
        self.radius = random.uniform(1.0, 2.5)
        self.color = ACCENT


class ArcReactor(tk.Canvas):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"

    def __init__(self, parent, width: int = 760, height: int = 200, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=BG, highlightthickness=0, **kwargs)
        self._w = width
        self._h = height
        self._state = self.IDLE
        self._frame = 0
        self._particles: list[Particle] = []
        self._amplitude = 0.0
        self._target_amplitude = 0.0
        self.after(0, self._animate)

    def set_state(self, state: str):
        self._state = state
        if state in (self.LISTENING, self.SPEAKING):
            self._target_amplitude = 1.0
        elif state == self.THINKING:
            self._target_amplitude = 0.6
        else:
            self._target_amplitude = 0.2

    def _animate(self):
        self.delete("all")
        cx, cy = self._w // 2, self._h // 2
        t = time.time()

        # Smooth amplitude
        self._amplitude += (self._target_amplitude - self._amplitude) * 0.1

        self._draw_grid(cx, cy, t)
        self._draw_outer_ring(cx, cy, t)
        self._draw_mid_ring(cx, cy, t)
        self._draw_inner_segments(cx, cy, t)
        self._update_particles(cx, cy, t)
        self._draw_core(cx, cy, t)
        self._draw_status_text(cx, cy)

        self._frame += 1
        self.after(33, self._animate)

    def _draw_grid(self, cx, cy, t):
        # Subtle horizon grid lines for HUD feel
        for i in range(1, 5):
            r = 30 + i * 20
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline=self._darken(ACCENT, 0.08), width=1)

    def _draw_outer_ring(self, cx, cy, t):
        r = 78 + 4 * self._amplitude
        n = 60
        speed = 0.4 if self._state == self.IDLE else 1.2
        for i in range(n):
            angle = i * (2 * math.pi / n) + t * speed
            x1 = cx + r * math.cos(angle)
            y1 = cy + r * math.sin(angle)
            x2 = cx + (r + 6) * math.cos(angle)
            y2 = cy + (r + 6) * math.sin(angle)
            brightness = 0.4 + 0.6 * abs(math.sin(angle * 3 + t * 2))
            color = self._fade(ACCENT, brightness)
            self.create_line(x1, y1, x2, y2, fill=color, width=1)

    def _draw_mid_ring(self, cx, cy, t):
        r = 56
        # 12 segmented arc chunks with rotation
        n_segments = 12
        speed = -0.8 if self._state != self.IDLE else -0.3
        for i in range(n_segments):
            start = math.degrees(i * (2 * math.pi / n_segments) + t * speed)
            arc_size = 18 if i % 2 == 0 else 8
            color = ACCENT if i % 2 == 0 else SECONDARY
            self.create_arc(cx - r, cy - r, cx + r, cy + r,
                            start=start, extent=arc_size,
                            outline=color, width=2, style="arc")

    def _draw_inner_segments(self, cx, cy, t):
        r = 38
        # 6 triangular wedges
        speed = 1.5 if self._state == self.THINKING else 0.6
        for i in range(6):
            angle = i * (math.pi / 3) + t * speed
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            x2 = cx + (r + 8) * math.cos(angle + 0.05)
            y2 = cy + (r + 8) * math.sin(angle + 0.05)
            x3 = cx + (r + 8) * math.cos(angle - 0.05)
            y3 = cy + (r + 8) * math.sin(angle - 0.05)
            self.create_polygon(x, y, x2, y2, x3, y3,
                                fill=self._fade(ACCENT, 0.7 + 0.3 * self._amplitude),
                                outline="")

    def _update_particles(self, cx, cy, t):
        # Spawn particles
        spawn_rate = {self.IDLE: 1, self.LISTENING: 4,
                      self.THINKING: 3, self.SPEAKING: 5}.get(self._state, 1)
        for _ in range(spawn_rate):
            if len(self._particles) < 80:
                self._particles.append(Particle(cx, cy))

        # Update + draw
        alive = []
        for p in self._particles:
            p.x += p.vx
            p.y += p.vy
            # Slight gravitational pull toward center for orbit feel
            dx = cx - p.x
            dy = cy - p.y
            dist = math.sqrt(dx * dx + dy * dy) + 0.001
            p.vx += dx / dist * 0.02
            p.vy += dy / dist * 0.02
            p.life -= 1
            if p.life > 0 and 0 < p.x < self._w and 0 < p.y < self._h:
                alpha = p.life / p.max_life
                color = self._fade(ACCENT, alpha)
                self.create_oval(p.x - p.radius, p.y - p.radius,
                                 p.x + p.radius, p.y + p.radius,
                                 fill=color, outline="")
                alive.append(p)
        self._particles = alive

    def _draw_core(self, cx, cy, t):
        # Outer halo
        for i in range(5, 0, -1):
            r = 22 + i * 4 + 3 * self._amplitude * math.sin(t * 4)
            color = self._fade(ACCENT, 0.05 * i)
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill="", outline=color, width=1)

        # Pulsing core
        pulse = 0.85 + 0.15 * math.sin(t * 3 + self._amplitude * 5)
        core_r = 18 * pulse
        self.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                         fill=ACCENT, outline="#FFFFFF", width=1)

        # Inner bright
        inner_r = 10 * pulse
        self.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                         fill="#FFFFFF", outline="")

    def _draw_status_text(self, cx, cy):
        label_map = {
            self.IDLE: ("STANDBY", "#3A5570"),
            self.LISTENING: ("LISTENING", "#00FF88"),
            self.THINKING: ("PROCESSING", "#FFB347"),
            self.SPEAKING: ("RESPONDING", ACCENT),
        }
        label, color = label_map.get(self._state, ("STANDBY", "#3A5570"))
        self.create_text(cx, self._h - 14, text=f"⬢ {label} ⬢",
                         fill=color, font=("SF Mono", 10, "bold"))

    @staticmethod
    def _fade(hex_color: str, alpha: float) -> str:
        hex_color = hex_color.lstrip("#")
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Blend toward background instead of true alpha (Tk has no alpha)
        bg_r, bg_g, bg_b = 0x0A, 0x0E, 0x1A
        r = int(bg_r + (r - bg_r) * max(0, min(1, alpha)))
        g = int(bg_g + (g - bg_g) * max(0, min(1, alpha)))
        b = int(bg_b + (b - bg_b) * max(0, min(1, alpha)))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        return ArcReactor._fade(hex_color, factor)
