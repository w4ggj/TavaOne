"""
HomeEye AI Assistant
====================
Voice-activated home AI assistant with webcam vision and file analysis.
Uses Claude API, sounddevice for mic input, pyttsx3 for voice output.

Author: Built for W4GGJ / Joe
"""

import anthropic
import base64
import cv2
import os
import sys
import time
import json
import tempfile
import wave
from pathlib import Path

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("[ERROR] Run: py -m pip install sounddevice numpy")
    sys.exit(1)

try:
    import speech_recognition as sr
except ImportError:
    print("[ERROR] Run: py -m pip install SpeechRecognition")
    sys.exit(1)

from smartthings import is_smart_command, handle_smart_command
from cameras import is_camera_command, handle_camera_command
from calendar_functions import is_calendar_command, handle_calendar_command, get_events
from sounds import sound_wake, sound_done, sound_thinking, sound_startup, sound_face_recognized, sound_goodnight
from face_recognition_homeeye import identify_from_camera
from face_watcher import start_face_watcher, stop_face_watcher
from hamradio_functions import (
    is_fact_command, handle_fact_command,
    is_band_command, handle_band_command,
    is_dx_command, handle_dx_command,
    is_network_command, handle_network_command,
    is_morning_command, handle_morning_command,
    is_goodnight_command, handle_goodnight_command,
)
from smartthings import handle_smart_command
from homeeye_functions import (
    is_weather_command, handle_weather_command,
    is_time_command, handle_time_command,
    is_timer_command, handle_timer_command,
    is_volume_command, handle_volume_command,
    is_app_command, handle_app_command,
    is_sysinfo_command, handle_sysinfo_command,
    is_screenshot_command, handle_screenshot_command,
    is_media_command, handle_media_command,
    is_dictation_command, handle_dictation_command,
    is_web_command, handle_web_command,
    is_traffic_command, handle_traffic_command,
)
import os
from pathlib import Path

# ── Visualizer state file ─────────────────────────────────────────────────────
_STATE_FILE = Path("C:/HomeEye/homeeye_state.txt")

class VisualizerState:
    IDLE      = "idle"
    LISTENING = "listening"
    WAKE      = "wake"
    THINKING  = "thinking"
    SPEAKING  = "speaking"

def set_state(state: str):
    try:
        _STATE_FILE.write_text(state)
    except Exception:
        pass

_LOG_FILE = Path("C:/HomeEye/homeeye_log.txt")
_log_lines = []

def log(msg: str):
    """Write message to both console and WOPR log file."""
    print(msg)
    try:
        _log_lines.append(msg)
        # Keep last 50 lines
        recent = _log_lines[-50:]
        _LOG_FILE.write_text("\n".join(recent), encoding="utf-8")
    except Exception:
        pass

def launch_visualizer_thread():
    import subprocess
    vis_args = ["py", str(Path(__file__).parent / "visualizer_standalone.py")]
    if config.get("visualizer_fullscreen", False):
        vis_args.append("--fullscreen")
    monitor = config.get("visualizer_monitor", 0)
    vis_args += ["--monitor", str(monitor)]
    subprocess.Popen(vis_args)
    time.sleep(0.8)

try:
    import pyttsx3
except ImportError:
    print("[ERROR] Run: py -m pip install pyttsx3")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    if not CONFIG_FILE.exists():
        print("[ERROR] config.json not found.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

config = load_config()

# ── Anthropic ─────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
MODEL  = "claude-sonnet-4-6"

# ── TTS ───────────────────────────────────────────────────────────────────────
def speak(text: str):
    """Speak text out loud — reinit engine each time to avoid pyttsx3 lockup."""
    log(f"[Assistant]: {text}")
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate",   config.get("tts_speed", 175))
        engine.setProperty("volume", config.get("tts_volume", 1.0))
        engine.say(text)
        engine.runAndWait()
        del engine
    except Exception as e:
        print(f"[TTS Error]: {e}")

# ── Webcam ────────────────────────────────────────────────────────────────────
def capture_frame():
    cam_index = config.get("camera_index", 0)
    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return None
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode("utf-8")

# ── Drive reading ─────────────────────────────────────────────────────────────
def read_linked_drive(query: str) -> str:
    drive_path = config.get("linked_drive_path", "")
    if not drive_path or not Path(drive_path).exists():
        return "No linked drive configured or path doesn't exist."
    supported   = {".txt", ".md", ".csv", ".json", ".log", ".py", ".html"}
    max_chars   = config.get("max_drive_chars", 8000)
    collected   = []
    total_chars = 0
    for fp in Path(drive_path).rglob("*"):
        if fp.suffix.lower() in supported and fp.is_file():
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                snippet = f"\n--- File: {fp.name} ---\n{content[:2000]}"
                collected.append(snippet)
                total_chars += len(snippet)
                if total_chars >= max_chars:
                    break
            except Exception:
                pass
    if not collected:
        return "No readable text files found on the linked drive."
    return "\n".join(collected)[:max_chars]

# ── Conversation ──────────────────────────────────────────────────────────────
conversation_history = []
MAX_HISTORY = config.get("max_history_turns", 10)

def trim_history():
    global conversation_history
    if len(conversation_history) > MAX_HISTORY * 2:
        conversation_history = conversation_history[-(MAX_HISTORY * 2):]

SYSTEM_PROMPT = config.get("system_prompt",
    "You are HomeEye, a helpful home AI assistant with access to a webcam and files. "
    "When the user asks about their appearance or surroundings, describe what you see "
    "in the webcam image. Be conversational, warm, and concise — responses are read "
    "aloud so keep them under 3 sentences unless more detail is needed."
)

def ask_claude(user_text: str, include_camera: bool, include_drive: bool) -> str:
    trim_history()
    content = []

    if include_camera:
        frame_b64 = capture_frame()
        if frame_b64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64}
            })
        else:
            user_text = user_text + " (Note: webcam capture failed, no image available)"

    if include_drive:
        drive_data  = read_linked_drive(user_text)
        user_text   = f"{user_text}\n\n[Linked Drive Content]:\n{drive_data}"

    content.append({"type": "text", "text": user_text})
    conversation_history.append({"role": "user", "content": content})

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=conversation_history,
        )
        reply = response.content[0].text
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"I ran into an error: {e}"

# ── Web browser ──────────────────────────────────────────────────────────────
import webbrowser

WEB_KEYWORDS = ["open ", "go to ", "browse to ", "navigate to ", "pull up ", "show me "]

def is_web_command(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in WEB_KEYWORDS) and any(
        x in t for x in [".com", ".net", ".org", ".gov", ".io", ".tv", "website", "site"]
    )

def handle_web_command(text: str) -> str:
    import re
    t = text.lower()

    # Strip wake/command words to get the URL
    for kw in sorted(WEB_KEYWORDS, key=len, reverse=True):
        t = t.replace(kw, "").strip()

    # Clean up spoken URL artifacts
    t = t.replace(" dot com", ".com").replace(" dot net", ".net")          .replace(" dot org", ".org").replace(" dot gov", ".gov")          .replace(" dot io", ".io").replace(" dot tv", ".tv")          .replace(" dot ", ".").strip()

    # Add https if missing
    if not t.startswith("http"):
        url = "https://" + t
    else:
        url = t

    # Remove any trailing punctuation
    url = url.rstrip(".,!?")

    try:
        webbrowser.get("chrome").open(url)
        return f"Opening {t} in Chrome."
    except Exception:
        try:
            webbrowser.open(url)
            return f"Opening {t} in your browser."
        except Exception as e:
            return f"I couldn't open that. Error: {e}"

# ── Intent detection ──────────────────────────────────────────────────────────
VISUAL_KEYWORDS = [
    "wearing", "see", "look", "appearance", "dressed", "outfit",
    "room", "behind me", "in front", "surroundings", "what am i",
    "describe", "show", "camera", "face",
]
DRIVE_KEYWORDS = [
    "file", "drive", "document", "data", "folder", "notes",
    "log", "csv", "read", "check my",
]

def needs_camera(text: str) -> bool:
    return any(kw in text.lower() for kw in VISUAL_KEYWORDS)

def needs_drive(text: str) -> bool:
    return any(kw in text.lower() for kw in DRIVE_KEYWORDS)

# ── Wake / exit words ─────────────────────────────────────────────────────────
WAKE_WORDS = [w.lower() for w in config.get("wake_words", ["hey claude", "homeeye", "computer"])]
EXIT_WORDS = ["goodbye", "exit", "quit", "shut down", "stop listening"]

def has_wake_word(text: str) -> bool:
    return any(w in text.lower() for w in WAKE_WORDS)

def is_exit(text: str) -> bool:
    return any(w in text.lower() for w in EXIT_WORDS)

# ── Microphone ────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 16000
CHANNELS       = 1
SILENCE_THRESH = config.get("mic_energy_threshold", 500)
PHRASE_LIMIT   = 15
SILENCE_LIMIT  = 1.5
recognizer     = sr.Recognizer()

def record_until_silence():
    chunk_size    = int(SAMPLE_RATE * 0.1)
    frames        = []
    silent_chunks = 0
    max_silent    = int(SILENCE_LIMIT / 0.1)
    max_chunks    = int(PHRASE_LIMIT  / 0.1)
    has_speech    = False
    mic_index     = config.get("microphone_index", None)

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype="int16", device=mic_index,
                            blocksize=chunk_size, latency="high") as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(chunk_size)
                rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2))
                frames.append(chunk)
                if rms > SILENCE_THRESH:
                    has_speech    = True
                    silent_chunks = 0
                elif has_speech:
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break
        if not has_speech:
            return None
        return np.concatenate(frames, axis=0)
    except Exception as e:
        print(f"[Mic Error]: {e}")
        time.sleep(1)
        return None

def listen_once():
    audio_np = record_until_silence()
    if audio_np is None:
        return None

    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_np.tobytes())
    wav_bytes  = buf.getvalue()
    audio_data = sr.AudioData(wav_bytes, SAMPLE_RATE, 2)

    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"[Speech Error]: {e}")
        return None

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  HomeEye AI Assistant  —  by W4GGJ")
    print("=" * 55)
    print(f"  Model  : {MODEL}")
    print(f"  Wake   : {WAKE_WORDS}")
    print(f"  Camera : index {config.get('camera_index', 0)}")
    print(f"  Mic    : index {config.get('microphone_index', 'default')}")
    print(f"  Drive  : {config.get('linked_drive_path', 'not set')}")
    print("=" * 55)
    print("  Listening... Say a wake word to activate.\n")

    launch_visualizer_thread()
    time.sleep(3)  # Let boot sequence play
    sound_startup()
    speak("HomeEye assistant is online and ready.")

    # Start ambient face watcher
    cam_idx = config.get("camera_index", 0)
    cooldown = config.get("face_greet_cooldown", 1800)
    from face_watcher import set_greet_cooldown
    set_greet_cooldown(cooldown)
    start_face_watcher(
        cam_index    = cam_idx,
        speak_func   = speak,
        listen_func  = listen_once,
        config       = config,
        calendar_func= lambda d: get_events(d),
        sound_func   = sound_face_recognized,
    )

    always_on          = config.get("always_on", False)
    conv_timeout       = config.get("conversation_timeout", 10)
    in_conversation    = False
    last_response_time = 0

    while True:
        set_state(VisualizerState.LISTENING)
        text = listen_once()

        # Check if conversation window expired
        if in_conversation and (time.time() - last_response_time) > conv_timeout:
            in_conversation = False
            log("[Conversation window closed]")

        if text is None:
            continue

        log(f"[Heard]: {text}")

        # Good morning — no wake word needed
        if is_morning_command(text):
            set_state(VisualizerState.THINKING)
            handle_morning_command(config, speak, listen_once, lambda d: get_events(d))
            set_state(VisualizerState.LISTENING)
            in_conversation    = True
            last_response_time = time.time()
            continue

        if is_exit(text):
            stop_face_watcher()
            speak("Goodbye! Shutting down.")
            break

        # Allow without wake word if in conversation window or always_on
        if not always_on and not in_conversation and not has_wake_word(text):
            continue

        set_state(VisualizerState.WAKE)
        sound_wake()

        query = text
        for ww in WAKE_WORDS:
            query = query.lower().replace(ww, "").strip()

        if not query:
            speak("Yes? How can I help?")
            follow = listen_once()
            if follow:
                query = follow
            else:
                continue

        # Morning routine?
        if is_morning_command(query):
            set_state(VisualizerState.THINKING)
            handle_morning_command(config, speak, listen_once, lambda d: get_events(d))
            set_state(VisualizerState.LISTENING)
            continue

        # Goodnight routine?
        if is_goodnight_command(query):
            set_state(VisualizerState.THINKING)
            handle_goodnight_command(config, speak,
                lambda t: handle_smart_command(t),
                lambda d: get_events(d))
            set_state(VisualizerState.LISTENING)
            continue

        # Ham radio fact?
        if is_fact_command(query):
            reply = handle_fact_command()
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Band conditions?
        if is_band_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_band_command()
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # DX cluster?
        if is_dx_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_dx_command(config)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Network status?
        if is_network_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_network_command()
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Calendar command?
        if is_calendar_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_calendar_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Time/Date command?
        if is_time_command(query):
            reply = handle_time_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Traffic command?
        if is_traffic_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_traffic_command()
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Weather command?
        if is_weather_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_weather_command(query, config)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Timer command?
        if is_timer_command(query):
            reply = handle_timer_command(query, speak)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Volume command?
        if is_volume_command(query):
            reply = handle_volume_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Media command?
        if is_media_command(query):
            reply = handle_media_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Screenshot command?
        if is_screenshot_command(query):
            reply = handle_screenshot_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # System info command?
        if is_sysinfo_command(query):
            set_state(VisualizerState.THINKING)
            reply = handle_sysinfo_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # App launch command?
        if is_app_command(query):
            reply = handle_app_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Web browser command?
        if is_web_command(query):
            reply = handle_web_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Dictation command?
        if is_dictation_command(query):
            reply = handle_dictation_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        # Camera command?
        if is_camera_command(query):
            reply = handle_camera_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            in_conversation    = True
            last_response_time = time.time()
            continue

        # Smart home command?
        if is_smart_command(query):
            reply = handle_smart_command(query)
            set_state(VisualizerState.SPEAKING)
            speak(reply)
            continue

        camera = needs_camera(query)
        drive  = needs_drive(query)

        if camera:
            speak("Let me take a look.")
        elif drive:
            speak("Let me check your files.")

        set_state(VisualizerState.THINKING)
        reply = ask_claude(query, include_camera=camera, include_drive=drive)
        set_state(VisualizerState.SPEAKING)
        speak(reply)
        sound_done()
        in_conversation    = True
        last_response_time = time.time()

if __name__ == "__main__":
    main()
