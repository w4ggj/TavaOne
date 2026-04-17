"""
HomeEye AI Assistant — Raspberry Pi Version
============================================
Voice-activated home AI assistant optimized for Raspberry Pi 4/5.
Uses Claude API, sounddevice for mic, espeak for TTS.

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
import subprocess
import threading
from pathlib import Path
from datetime import datetime

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("[ERROR] Run: pip3 install sounddevice numpy")
    sys.exit(1)

try:
    import speech_recognition as sr
except ImportError:
    print("[ERROR] Run: pip3 install SpeechRecognition")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path(__file__).parent / "config_pi.json"

def load_config():
    if not CONFIG_FILE.exists():
        print("[ERROR] config_pi.json not found.")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)

config = load_config()

# ── Anthropic ─────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
MODEL  = "claude-sonnet-4-6"

# ── TTS via espeak (Pi native) ────────────────────────────────────────────────
def speak(text: str):
    """Speak using espeak — native Pi TTS, no dependencies needed."""
    print(f"\n[Assistant]: {text}\n")
    try:
        speed  = config.get("tts_speed", 150)
        pitch  = config.get("tts_pitch", 50)
        volume = config.get("tts_volume", 100)
        subprocess.run([
            "espeak",
            "-s", str(speed),
            "-p", str(pitch),
            "-a", str(volume),
            "-v", config.get("tts_voice", "en-us"),
            text
        ], check=True, capture_output=True)
    except FileNotFoundError:
        print("[TTS] espeak not found. Install: sudo apt install espeak")
    except Exception as e:
        print(f"[TTS Error]: {e}")

# ── Webcam ────────────────────────────────────────────────────────────────────
def capture_frame():
    cam_index = config.get("camera_index", 0)
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    time.sleep(1.5)
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        return None
    brightness = frame.mean() if frame is not None else 0
    if brightness < 10:
        return None
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode("utf-8")

# ── Drive reading ─────────────────────────────────────────────────────────────
def read_linked_drive(query: str) -> str:
    drive_path = config.get("linked_drive_path", "")
    if not drive_path or not Path(drive_path).exists():
        return "No linked drive configured."
    supported   = {".txt", ".md", ".csv", ".json", ".log"}
    max_chars   = config.get("max_drive_chars", 8000)
    collected   = []
    total_chars = 0
    for fp in Path(drive_path).rglob("*"):
        if fp.suffix.lower() in supported and fp.is_file():
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                snippet = f"\n--- {fp.name} ---\n{content[:2000]}"
                collected.append(snippet)
                total_chars += len(snippet)
                if total_chars >= max_chars:
                    break
            except Exception:
                pass
    return "\n".join(collected)[:max_chars] if collected else "No files found."

# ── Conversation ──────────────────────────────────────────────────────────────
conversation_history = []
MAX_HISTORY = config.get("max_history_turns", 10)

def trim_history():
    global conversation_history
    if len(conversation_history) > MAX_HISTORY * 2:
        conversation_history = conversation_history[-(MAX_HISTORY * 2):]

SYSTEM_PROMPT = config.get("system_prompt",
    "You are HomeEye, a helpful home AI assistant for W4GGJ Joe in Tampa Bay FL. "
    "You have access to a webcam and files. Be conversational, warm and concise — "
    "responses are read aloud so keep them under 3 sentences unless more detail is needed. "
    "Joe's last name Leone is pronounced Lee-own."
)

def ask_claude(user_text: str, include_camera: bool, include_drive: bool) -> str:
    trim_history()
    content = []
    if include_camera:
        frame_b64 = capture_frame()
        if frame_b64:
            content.append({"type": "image", "source": {
                "type": "base64", "media_type": "image/jpeg", "data": frame_b64}})
        else:
            user_text += " (Note: webcam image unavailable)"
    if include_drive:
        drive_data = read_linked_drive(user_text)
        user_text  = f"{user_text}\n\n[Drive]:\n{drive_data}"
    content.append({"type": "text", "text": user_text})
    conversation_history.append({"role": "user", "content": content})
    try:
        response = client.messages.create(
            model=MODEL, max_tokens=512,
            system=SYSTEM_PROMPT, messages=conversation_history
        )
        reply = response.content[0].text
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"API error: {e}"

# ── Intent detection ──────────────────────────────────────────────────────────
VISUAL_KEYWORDS  = ["wearing","see","look","appearance","dressed","outfit",
                    "room","behind me","surroundings","describe","camera","face"]
DRIVE_KEYWORDS   = ["file","drive","document","data","folder","notes","check my"]
SMART_KEYWORDS   = ["turn on","turn off","dim","lights on","lights off"]
TIME_KEYWORDS    = ["what time","what's the time","what day","what date","today's date"]
WEATHER_KEYWORDS = ["weather","temperature","forecast","rain","humidity"]
TRAFFIC_KEYWORDS = ["traffic","commute","how long to","drive time"]
TIMER_KEYWORDS   = ["set a timer","timer for","remind me in"]
VOLUME_KEYWORDS  = ["volume up","volume down","mute","unmute","louder","quieter"]
MORNING_KEYWORDS = ["good morning","morning routine","start my day"]
EXIT_WORDS       = ["goodbye","exit","quit","shut down","stop listening"]

def needs_camera(t): return any(k in t.lower() for k in VISUAL_KEYWORDS)
def needs_drive(t):  return any(k in t.lower() for k in DRIVE_KEYWORDS)
def is_exit(t):      return any(k in t.lower() for k in EXIT_WORDS)

# ── SmartThings ───────────────────────────────────────────────────────────────
def handle_smart(query: str) -> str:
    try:
        from smartthings import is_smart_command, handle_smart_command
        if is_smart_command(query):
            return handle_smart_command(query)
    except Exception as e:
        return f"Smart home error: {e}"
    return None

# ── Time ──────────────────────────────────────────────────────────────────────
def handle_time(query: str) -> str:
    now = datetime.now()
    if "date" in query or "day" in query:
        return f"Today is {now.strftime('%A, %B %d, %Y')}."
    return f"The time is {now.strftime('%I:%M %p')}."

# ── Weather ───────────────────────────────────────────────────────────────────
def handle_weather(query: str) -> str:
    try:
        from homeeye_functions import get_weather, handle_weather_command
        return handle_weather_command(query, config)
    except Exception as e:
        return f"Weather unavailable: {e}"

# ── Traffic ───────────────────────────────────────────────────────────────────
def handle_traffic() -> str:
    try:
        from homeeye_functions import get_traffic
        return f"Traffic: {get_traffic()}"
    except Exception as e:
        return f"Traffic unavailable: {e}"

# ── Timer ────────────────────────────────────────────────────────────────────
def handle_timer(query: str) -> str:
    try:
        from homeeye_functions import is_timer_command, handle_timer_command
        return handle_timer_command(query, speak)
    except Exception as e:
        return f"Timer error: {e}"

# ── Wake / conversation ───────────────────────────────────────────────────────
WAKE_WORDS = [w.lower() for w in config.get("wake_words", ["hey claude", "homeeye"])]

def has_wake_word(text: str) -> bool:
    return any(w in text.lower() for w in WAKE_WORDS)

# ── Microphone ────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 16000
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
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
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
        return np.concatenate(frames, axis=0) if has_speech else None
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
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_np.tobytes())
    try:
        return recognizer.recognize_google(sr.AudioData(buf.getvalue(), SAMPLE_RATE, 2))
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print(f"[Speech Error]: {e}")
        return None

# ── Log ───────────────────────────────────────────────────────────────────────
LOG_FILE  = Path("/tmp/homeeye_log.txt")
_log_lines = []

def log(msg: str):
    print(msg)
    try:
        _log_lines.append(msg)
        LOG_FILE.write_text("\n".join(_log_lines[-50:]), encoding="utf-8")
    except Exception:
        pass

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  HomeEye AI Assistant — Raspberry Pi")
    print(f"  W4GGJ  |  {datetime.now().strftime('%B %d, %Y')}")
    print("=" * 55)
    print(f"  Model  : {MODEL}")
    print(f"  Wake   : {WAKE_WORDS}")
    print(f"  Mic    : {config.get('microphone_index', 'default')}")
    print("=" * 55 + "\n")

    speak("HomeEye assistant is online and ready.")

    always_on          = config.get("always_on", False)
    conv_timeout       = config.get("conversation_timeout", 10)
    in_conversation    = False
    last_response_time = 0

    while True:
        text = listen_once()

        if in_conversation and (time.time() - last_response_time) > conv_timeout:
            in_conversation = False

        if text is None:
            continue

        log(f"[Heard]: {text}")

        if is_exit(text):
            speak("Goodbye! Shutting down. 73 de W4GGJ.")
            break

        if not always_on and not in_conversation and not has_wake_word(text):
            continue

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

        # Route to handler
        reply = None

        # Time
        if any(k in query.lower() for k in TIME_KEYWORDS):
            reply = handle_time(query)

        # Weather
        elif any(k in query.lower() for k in WEATHER_KEYWORDS):
            speak("Checking weather...")
            reply = handle_weather(query)

        # Traffic
        elif any(k in query.lower() for k in TRAFFIC_KEYWORDS):
            speak("Checking traffic...")
            reply = handle_traffic()

        # Timer
        elif any(k in query.lower() for k in TIMER_KEYWORDS):
            reply = handle_timer(query)

        # Smart home
        elif any(k in query.lower() for k in SMART_KEYWORDS):
            result = handle_smart(query)
            reply  = result if result else None

        # Claude with camera
        elif needs_camera(query):
            speak("Let me take a look.")
            reply = ask_claude(query, include_camera=True, include_drive=False)

        # Claude with drive
        elif needs_drive(query):
            speak("Checking your files.")
            reply = ask_claude(query, include_camera=False, include_drive=True)

        # General Claude
        else:
            reply = ask_claude(query, include_camera=False, include_drive=False)

        if reply:
            speak(reply)
            in_conversation    = True
            last_response_time = time.time()

if __name__ == "__main__":
    main()
