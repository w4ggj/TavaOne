"""
HomeEye Sound Effects
Generates and plays sci-fi chime sounds using numpy + sounddevice.
No external audio files needed — all sounds are generated in code.

Author: Built for W4GGJ / Joe
"""

import numpy as np
import sounddevice as sd
import threading

SAMPLE_RATE = 44100

def _play(audio: np.ndarray, blocking: bool = False):
    """Play audio array through default output."""
    def _run():
        try:
            sd.play(audio, samplerate=SAMPLE_RATE)
            sd.wait()
        except Exception:
            pass
    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()

def _tone(freq: float, duration: float, volume: float = 0.3,
          fade: float = 0.05, wave: str = "sine") -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    if wave == "sine":
        audio = np.sin(2 * np.pi * freq * t)
    elif wave == "square":
        audio = np.sign(np.sin(2 * np.pi * freq * t)) * 0.3
    elif wave == "sawtooth":
        audio = 2 * (t * freq - np.floor(t * freq + 0.5))
    else:
        audio = np.sin(2 * np.pi * freq * t)

    # Fade in/out
    fade_samples = int(SAMPLE_RATE * fade)
    if fade_samples > 0 and len(audio) > fade_samples * 2:
        audio[:fade_samples]  *= np.linspace(0, 1, fade_samples)
        audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    return (audio * volume).astype(np.float32)

def _concat(*arrays) -> np.ndarray:
    return np.concatenate(arrays)

def _silence(duration: float) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)

# ── Sound effects ─────────────────────────────────────────────────────────────

def sound_wake():
    """Ascending chime — wake word detected."""
    audio = _concat(
        _tone(600,  0.08, 0.25),
        _silence(0.02),
        _tone(800,  0.08, 0.25),
        _silence(0.02),
        _tone(1200, 0.12, 0.3),
    )
    _play(audio)

def sound_done():
    """Descending chime — response complete."""
    audio = _concat(
        _tone(1000, 0.08, 0.2),
        _silence(0.02),
        _tone(700,  0.08, 0.2),
        _silence(0.02),
        _tone(500,  0.12, 0.15),
    )
    _play(audio)

def sound_thinking():
    """Subtle blip — processing."""
    audio = _tone(880, 0.05, 0.1)
    _play(audio)

def sound_error():
    """Low buzz — error."""
    audio = _concat(
        _tone(200, 0.15, 0.2, wave="square"),
        _silence(0.05),
        _tone(180, 0.15, 0.2, wave="square"),
    )
    _play(audio)

def sound_startup():
    """Full WOPR startup chime sequence — played on boot."""
    audio = _concat(
        _silence(0.1),
        _tone(440,  0.1,  0.2),
        _tone(554,  0.1,  0.2),
        _tone(659,  0.1,  0.2),
        _tone(880,  0.2,  0.3),
        _silence(0.15),
        _tone(1100, 0.05, 0.2),
        _tone(1320, 0.05, 0.2),
        _tone(1760, 0.3,  0.35),
        _silence(0.1),
    )
    _play(audio, blocking=True)

def sound_face_recognized():
    """Friendly arpeggio — face recognized."""
    audio = _concat(
        _tone(523, 0.08, 0.25),
        _tone(659, 0.08, 0.25),
        _tone(784, 0.08, 0.25),
        _tone(1047,0.15, 0.3),
    )
    _play(audio)

def sound_goodnight():
    """Descending lullaby — goodnight."""
    audio = _concat(
        _tone(880, 0.12, 0.2),
        _tone(784, 0.12, 0.2),
        _tone(659, 0.12, 0.2),
        _tone(523, 0.25, 0.25),
    )
    _play(audio)
