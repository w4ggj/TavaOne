"""
HomeEye Visualizer — Pulsing Circle
Always-on-top window showing HomeEye status with animated pulsing circle.

States:
  listening  — slow blue pulse
  wake       — green flash
  thinking   — amber spin pulse
  speaking   — white fast pulse
  idle       — dim grey

Author: Built for W4GGJ / Joe
"""

import threading
import time
import math
import tkinter as tk

# ── State ─────────────────────────────────────────────────────────────────────
class VisualizerState:
    IDLE      = "idle"
    LISTENING = "listening"
    WAKE      = "wake"
    THINKING  = "thinking"
    SPEAKING  = "speaking"

current_state = VisualizerState.LISTENING
state_lock    = threading.Lock()
_running      = True

def set_state(state: str):
    global current_state
    with state_lock:
        current_state = state

def get_state() -> str:
    with state_lock:
        return current_state

# ── Colors ────────────────────────────────────────────────────────────────────
STATE_COLORS = {
    VisualizerState.IDLE:      "#333333",
    VisualizerState.LISTENING: "#1e90ff",  # dodger blue
    VisualizerState.WAKE:      "#00ff88",  # green flash
    VisualizerState.THINKING:  "#e8a000",  # amber
    VisualizerState.SPEAKING:  "#ffffff",  # white
}

STATE_LABELS = {
    VisualizerState.IDLE:      "Idle",
    VisualizerState.LISTENING: "Listening...",
    VisualizerState.WAKE:      "Wake Word!",
    VisualizerState.THINKING:  "Thinking...",
    VisualizerState.SPEAKING:  "Speaking",
}

# ── Visualizer Window ─────────────────────────────────────────────────────────
class PulsingCircleVisualizer:
    def __init__(self):
        self.root   = tk.Tk()
        self.root.title("HomeEye")
        self.root.geometry("220x240+10+10")
        self.root.configure(bg="#111111")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.resizable(False, False)

        # Remove title bar decorations for clean look
        # self.root.overrideredirect(True)  # Uncomment for borderless

        self.canvas = tk.Canvas(self.root, width=220, height=190,
                                bg="#111111", highlightthickness=0)
        self.canvas.pack()

        self.label = tk.Label(self.root, text="Listening...",
                              font=("Arial", 11), fg="#888888", bg="#111111")
        self.label.pack(pady=2)

        self.cx     = 110   # center x
        self.cy     = 95    # center y
        self.radius = 55    # base radius
        self.tick   = 0

        self._animate()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        return f"#{r:02x}{g:02x}{b:02x}"

    def _dim_color(self, hex_color: str, factor: float) -> str:
        r, g, b = self._hex_to_rgb(hex_color)
        return self._rgb_to_hex(int(r * factor), int(g * factor), int(b * factor))

    def _animate(self):
        if not _running:
            return

        state = get_state()
        color = STATE_COLORS.get(state, "#333333")
        label = STATE_LABELS.get(state, "")
        t     = self.tick

        self.canvas.delete("all")

        # Calculate pulse based on state
        if state == VisualizerState.LISTENING:
            # Slow gentle pulse
            pulse = 0.5 + 0.5 * math.sin(t * 0.08)
            rings = 3
            speed = 0.08

        elif state == VisualizerState.WAKE:
            # Fast bright flash
            pulse = 0.7 + 0.3 * math.sin(t * 0.4)
            rings = 5
            speed = 0.4

        elif state == VisualizerState.THINKING:
            # Medium amber pulse with rotation feel
            pulse = 0.4 + 0.6 * abs(math.sin(t * 0.15))
            rings = 4
            speed = 0.15

        elif state == VisualizerState.SPEAKING:
            # Fast white pulse
            pulse = 0.5 + 0.5 * math.sin(t * 0.25)
            rings = 4
            speed = 0.25

        else:  # IDLE
            pulse = 0.3
            rings = 2
            speed = 0.05

        # Draw outer glow rings
        for i in range(rings, 0, -1):
            ring_r   = self.radius + (i * 12 * pulse)
            alpha_f  = (1.0 - (i / (rings + 1))) * pulse * 0.6
            ring_col = self._dim_color(color, alpha_f)
            self.canvas.create_oval(
                self.cx - ring_r, self.cy - ring_r,
                self.cx + ring_r, self.cy + ring_r,
                outline=ring_col, width=2, fill=""
            )

        # Draw main circle
        main_r   = self.radius * (0.85 + 0.15 * pulse)
        main_col = self._dim_color(color, 0.4 + 0.6 * pulse)
        self.canvas.create_oval(
            self.cx - main_r, self.cy - main_r,
            self.cx + main_r, self.cy + main_r,
            outline=color, width=3, fill=main_col
        )

        # Draw center dot
        dot_r = 8 * (0.7 + 0.3 * pulse)
        self.canvas.create_oval(
            self.cx - dot_r, self.cy - dot_r,
            self.cx + dot_r, self.cy + dot_r,
            fill=color, outline=""
        )

        # Draw W4GGJ callsign text in center
        self.canvas.create_text(
            self.cx, self.cy,
            text="W4GGJ", font=("Arial", 9, "bold"),
            fill="#111111"
        )

        # Update label
        self.label.config(text=label, fg=color if state != VisualizerState.IDLE else "#555555")

        self.tick += 1
        self.root.after(33, self._animate)  # ~30fps

    def run(self):
        self.root.mainloop()

    def stop(self):
        global _running
        _running = False
        try:
            self.root.quit()
        except Exception:
            pass

# ── Global visualizer instance ────────────────────────────────────────────────
_visualizer = None

def start_visualizer():
    """Start the visualizer in a separate thread."""
    global _visualizer
    _visualizer = PulsingCircleVisualizer()
    _visualizer.run()

def stop_visualizer():
    global _running
    _running = False
    if _visualizer:
        _visualizer.stop()

def launch_visualizer_thread():
    """Launch visualizer in background thread — call from assistant.py."""
    t = threading.Thread(target=start_visualizer, daemon=True)
    t.start()
    time.sleep(0.5)  # Give it time to initialize
