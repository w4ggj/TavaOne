"""
HomeEye WOPR Terminal Visualizer v5
Clean rewrite with conversation log panel built in.
"""

import tkinter as tk
import math
import os
import sys
import ctypes
import ctypes.wintypes
import random
import time
from pathlib import Path

# ── File paths ────────────────────────────────────────────────────────────────
STATE_FILE = Path("C:/HomeEye/homeeye_state.txt")
LOG_FILE   = Path("C:/HomeEye/homeeye_log.txt")

def read_state() -> str:
    try:
        return STATE_FILE.read_text().strip()
    except Exception:
        return "listening"

def read_log() -> list:
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
        return [l.strip() for l in lines if l.strip()]
    except Exception:
        return []

# ── Args ──────────────────────────────────────────────────────────────────────
args        = sys.argv[1:]
FULLSCREEN  = "--fullscreen" in args
MONITOR_IDX = 0
if "--monitor" in args:
    try:
        MONITOR_IDX = int(args[args.index("--monitor") + 1])
    except Exception:
        MONITOR_IDX = 0

# ── Monitor detection ─────────────────────────────────────────────────────────
def get_monitors():
    monitors = []
    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        r = lprcMonitor.contents
        monitors.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return 1
    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_double
    )
    ctypes.windll.user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)
    return monitors

def get_monitor_geometry(index):
    monitors = get_monitors()
    if not monitors:
        return 0, 0, 1920, 1080
    index = max(0, min(index, len(monitors) - 1))
    return monitors[index]

# ── Colors ────────────────────────────────────────────────────────────────────
STATE_COLORS = {
    "idle":      "#333333",
    "listening": "#1e90ff",
    "wake":      "#00ff88",
    "thinking":  "#e8a000",
    "speaking":  "#ffffff",
}

STATE_LABELS = {
    "idle":      "Idle",
    "listening": "Listening...",
    "wake":      "Wake Word Detected!",
    "thinking":  "Thinking...",
    "speaking":  "Speaking",
}

STATE_MESSAGES = {
    "listening": ["ACOUSTIC SENSORS: ACTIVE", "WAKE WORD: ARMED", "MONITORING AUDIO STREAM", "STANDING BY...", "AWAITING COMMAND INPUT"],
    "wake":      ["WAKE WORD DETECTED!", "VOICE COMMAND RECEIVED", "PROCESSING INPUT...", "AUTHENTICATION: OK", "ACCESS GRANTED"],
    "thinking":  ["QUERYING CLAUDE API...", "NEURAL NET PROCESSING", "COMPUTING RESPONSE...", "ANALYZING REQUEST...", "GENERATING OUTPUT..."],
    "speaking":  ["SPEECH SYNTHESIS: ACTIVE", "TRANSMITTING RESPONSE", "AUDIO OUTPUT: ONLINE", "VOICE OUTPUT ACTIVE", "BROADCASTING..."],
    "idle":      ["SYSTEM IDLE", "LOW POWER MODE", "STANDING BY", "MONITORING...", "READY"],
}

SCROLL_DATA = [
    "W4GGJ DE WOPR K", "CQ CQ CQ DE W4GGJ", "14.074 MHZ FT8 MONITOR",
    "POTA US-1829 ALAFIA RIVER", "POTA US-6700 SAWGRASS LAKE",
    "XIEGU X6200 QRP 5W", "DIGIPI ONLINE", "TAVAONE.COM UPLINK OK",
    "73 DE W4GGJ", "WORKED ALL STATES: CONFIRMED", "DXCC MIXED: ACTIVE",
    "SMARTTHINGS: 33 DEVICES", "VOICEMEETER: ROUTING OK",
    "FIFINE MIC: LEVEL OK", "CLAUDE-SONNET-4-6: ONLINE",
    "TAMPA BAY FL: MONITORING", "ANTHROPIC API: CONNECTED",
    "SOLAR FLUX: NOMINAL", "K-INDEX: 2", "BAND CONDITIONS: GOOD",
    "ACOUSTIC INTERCEPT: NOMINAL", "SIGNAL PROCESSING: 16KHZ",
    "WAKE WORD ENGINE: ARMED", "DEVICES ONLINE: 33",
]

# ── Main class ────────────────────────────────────────────────────────────────
class WOPRTerminal:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WOPR // HomeEye W4GGJ")
        self.root.configure(bg="#000000")
        self.root.attributes("-topmost", True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        if FULLSCREEN:
            x, y, w, h = get_monitor_geometry(MONITOR_IDX)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.overrideredirect(True)
            self.W, self.H = w, h
            self.fs   = max(11, w // 90)   # font size
            self.tfs  = max(18, w // 45)   # title font size
        else:
            self.W, self.H = 800, 600
            self.root.geometry(f"800x600+10+10")
            self.root.resizable(False, False)
            self.fs  = 11
            self.tfs = 16

        self.canvas = tk.Canvas(self.root, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.tick          = 0
        self.scroll_lines  = list(SCROLL_DATA) * 3
        self.scroll_offset = 0
        self.status_idx    = 0
        self.start_time    = time.time()
        self.booting       = True
        self.boot_tick     = 0
        self.boot_lines    = []
        self.boot_log      = [
            "WOPR HOMEEYE SYSTEM v2.0",
            "ANTHROPIC CLAUDE API.......... OK",
            "SMARTTHINGS LINK.............. OK",
            "GOOGLE CALENDAR............... OK",
            "GOOGLE TRAFFIC API............ OK",
            "VOICE RECOGNITION ENGINE...... OK",
            "SPEECH SYNTHESIZER............ OK",
            "WEBCAM SUBSYSTEM.............. OK",
            "FACE RECOGNITION.............. OK",
            "WEATHER SERVICE............... OK",
            "DX CLUSTER MONITOR............ OK",
            "SMARTTHINGS DEVICES: 33....... OK",
            "WAKE WORD ENGINE: HEY CLAUDE.. ARMED",
            "W4GGJ STATION TAVAONE......... ONLINE",
            "",
            "SHALL WE PLAY A GAME?",
            "",
            "GREETINGS PROFESSOR FALKEN.",
            "",
            "HOMEEYE IS ONLINE.",
        ]

        self._boot_sequence()

    def g(self, b=1.0):
        v = int(255 * max(0, min(1, b)))
        return f"#00{v:02x}00"

    def a(self, b=1.0):
        r = int(255 * max(0, min(1, b)))
        g2 = int(180 * max(0, min(1, b)))
        return f"#{r:02x}{g2:02x}00"

    def _animate(self):
        state  = read_state()
        t      = self.tick
        W, H   = self.W, self.H
        fs     = self.fs
        tfs    = self.tfs
        C      = self.canvas

        C.delete("all")

        # Scanlines
        for y in range(0, H, 4):
            C.create_line(0, y, W, y, fill="#001100", width=1)

        # ── Layout math ───────────────────────────────────────────────────────
        border  = self.g(0.5)
        title_h = tfs * 2 + 16
        bot_h   = 80
        log_h   = max(80, H // 6)
        main_h  = H - title_h - log_h - bot_h - 20

        title_y   = 0
        main_y    = title_h + 5
        log_y     = main_y + main_h + 5
        bot_y     = log_y + log_h + 5

        # ── Title ─────────────────────────────────────────────────────────────
        C.create_rectangle(5, 5, W-5, title_h, fill="#001a00", outline=border, width=2)
        C.create_text(W//2, title_h//2 - 4,
                      text="W O P R  //  H O M E E Y E  A I",
                      font=("Courier", tfs, "bold"), fill=self.g(0.9))
        uptime = int(time.time() - self.start_time)
        d, h2, m = uptime//86400, (uptime%86400)//3600, (uptime%3600)//60
        C.create_text(W//2, title_h//2 + tfs - 2,
                      text=f"W4GGJ STATION  //  UPTIME: {d:02d}D {h2:02d}H {m:02d}M",
                      font=("Courier", fs, "bold"), fill=self.g(0.45))

        # ── Main area ─────────────────────────────────────────────────────────
        half = (W - 30) // 2

        # Left — scrolling data
        C.create_rectangle(10, main_y, 10+half, main_y+main_h,
                           outline=self.g(0.3), width=1, fill="#000800")
        C.create_text(10+half//2, main_y+12,
                      text="[ DATA STREAM ]", font=("Courier", fs, "bold"),
                      fill=self.g(0.7))

        if t % 8 == 0:
            self.scroll_offset = (self.scroll_offset + 1) % len(self.scroll_lines)
        line_h   = fs + 6
        max_ln   = (main_h - 30) // line_h
        for i in range(max_ln):
            idx  = (self.scroll_offset + i) % len(self.scroll_lines)
            age  = i / max_ln
            C.create_text(20, main_y+28+i*line_h, anchor="w",
                          text=self.scroll_lines[idx][:33],
                          font=("Courier", fs),
                          fill=self.g(0.15 + 0.45*(1-age)))

        # Right — status circle
        rx = 20 + half
        C.create_rectangle(rx, main_y, rx+half, main_y+main_h,
                           outline=self.g(0.3), width=1, fill="#000800")
        C.create_text(rx+half//2, main_y+12,
                      text="[ SYSTEM STATUS ]", font=("Courier", fs, "bold"),
                      fill=self.g(0.7))

        scol = self.a(0.9) if state in ("wake","thinking","speaking") else self.g(0.9)
        pulse = 0.5 + 0.5 * math.sin(t * (0.4 if state=="wake" else 0.3 if state=="speaking" else 0.15 if state=="thinking" else 0.08))
        cx2  = rx + half//2
        cy2  = main_y + main_h//2 - 10
        r    = min(half, main_h)//5

        for ring in range(4, 0, -1):
            rr = r + ring*10*pulse
            gc = self.a(0.25*pulse) if state in ("wake","thinking","speaking") else self.g(0.25*pulse)
            C.create_oval(cx2-rr, cy2-rr, cx2+rr, cy2+rr, outline=gc, width=1, fill="")

        fc = self.a(0.15*pulse) if state in ("wake","thinking","speaking") else self.g(0.15*pulse)
        C.create_oval(cx2-r, cy2-r, cx2+r, cy2+r, outline=scol, width=3, fill=fc)
        C.create_text(cx2, cy2, text="W4GGJ",
                      font=("Courier", max(9, fs), "bold"), fill="#000000")

        msgs = STATE_MESSAGES.get(state, STATE_MESSAGES["idle"])
        if t % 40 == 0:
            self.status_idx = (self.status_idx + 1) % len(msgs)
        msg = msgs[self.status_idx] + ("_" if t%20<10 else "")
        C.create_text(cx2, main_y+main_h-35, text=msg,
                      font=("Courier", fs+1, "bold"), fill=scol)

        # ── Conversation Log ───────────────────────────────────────────────────
        C.create_rectangle(10, log_y, W-10, log_y+log_h,
                           outline=self.g(0.4), width=2, fill="#000d00")
        C.create_text(W//2, log_y+10,
                      text="[ CONVERSATION LOG ]",
                      font=("Courier", fs, "bold"), fill=self.g(0.7))

        log_lines = read_log()
        llh       = fs + 4
        max_log   = max(1, (log_h - 26) // llh)
        visible   = log_lines[-max_log:]
        for i, line in enumerate(visible):
            age    = (i+1) / max(len(visible), 1)
            bright = 0.3 + 0.6 * age
            col    = self.a(bright) if "[Assistant]" in line else self.g(bright)
            C.create_text(18, log_y+22+i*llh, anchor="w",
                          text=line[:95],
                          font=("Courier", fs), fill=col)

        # ── Bottom bar ────────────────────────────────────────────────────────
        C.create_rectangle(5, bot_y, W-5, H-5,
                           fill="#001a00", outline=border, width=1)

        indicators = [("VOICE",True),("CLAUDE",True),("SMARTTHINGS",True),("CAMERA",True),("DRIVE",True)]
        iw = (W-20)//len(indicators)
        for i, (name, active) in enumerate(indicators):
            ix = 15 + i*iw + iw//2
            iy = bot_y + 28
            col = self.g(0.9) if active else self.g(0.3)
            C.create_text(ix, iy-10, text="●" if active else "○",
                          font=("Courier", 13), fill=col)
            C.create_text(ix, iy+10, text=name,
                          font=("Courier", fs-1, "bold"), fill=col)

        prompt = f"HOMEEYE> {msg.rstrip('_')}" + ("█" if t%20<10 else "")
        C.create_text(15, H-10, anchor="w", text=prompt,
                      font=("Courier", fs, "bold"), fill=self.g(0.8))

        self.tick += 1
        self.root.after(33, self._animate)

    def _boot_sequence(self):
        """Animated WOPR boot sequence."""
        if not self.booting:
            self._animate()
            return

        W, H = self.W, self.H
        C    = self.canvas
        fs   = self.fs
        tfs  = self.tfs

        C.delete("all")

        # Black background with scanlines
        for y in range(0, H, 4):
            C.create_line(0, y, W, y, fill="#001100", width=1)

        # Border
        C.create_rectangle(5, 5, W-5, H-5, outline=self.g(0.4), width=2)

        # Title
        C.create_text(W//2, 40, text="W O P R  //  H O M E E Y E  A I",
                      font=("Courier", tfs, "bold"), fill=self.g(0.9))
        C.create_text(W//2, 40 + tfs + 4, text="W4GGJ — TAVAONE.COM",
                      font=("Courier", fs, "bold"), fill=self.g(0.4))

        # Separator
        C.create_line(20, 80, W-20, 80, fill=self.g(0.4), width=1)

        # Boot log lines
        line_h   = fs + 6
        start_y  = 100
        max_show = self.boot_tick // 3  # Reveal one line every 3 ticks

        for i, line in enumerate(self.boot_log[:max_show]):
            if not line:
                continue
            age    = i / max(len(self.boot_log), 1)
            bright = 0.4 + 0.5 * (1 - age * 0.3)

            # Color OK lines green, special lines amber
            if "OK" in line:
                col = self.g(bright)
            elif any(x in line for x in ["ARMED", "ONLINE", "SHALL", "GREETINGS", "HOMEEYE"]):
                col = self.a(bright)
            else:
                col = self.g(bright * 0.7)

            C.create_text(30, start_y + i * line_h, anchor="w",
                          text=line, font=("Courier", fs), fill=col)

        # Blinking cursor after last line
        cursor_y = start_y + min(max_show, len(self.boot_log)) * line_h
        if self.boot_tick % 20 < 10:
            C.create_text(30, cursor_y, anchor="w", text="█",
                          font=("Courier", fs), fill=self.g(0.8))

        self.boot_tick += 1

        # Boot complete after all lines shown + pause
        if self.boot_tick > len(self.boot_log) * 3 + 60:
            self.booting = False
            self._animate()
        else:
            self.root.after(50, self._boot_sequence)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    WOPRTerminal().run()
