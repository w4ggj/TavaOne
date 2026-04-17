"""
HomeEye Ambient Face Watcher
Continuously monitors webcam in background.
When a known face is detected, triggers a greeting and morning/evening routine.

Author: Built for W4GGJ / Joe
"""

import cv2
import time
import threading
import numpy as np
from datetime import datetime
from pathlib import Path
from face_recognition_homeeye import recognize_face, face_cascade

# ── State ─────────────────────────────────────────────────────────────────────
_watcher_thread   = None
_stop_event       = threading.Event()
_last_seen        = {}          # name -> timestamp last greeted
_greet_cooldown   = 1800        # seconds between greetings (30 min)
_presence_timeout = 10          # seconds face must be absent before re-greeting

def get_greeting(name: str) -> str:
    """Return time-appropriate greeting."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return f"Good morning {name}!"
    elif 12 <= hour < 17:
        return f"Good afternoon {name}!"
    elif 17 <= hour < 21:
        return f"Good evening {name}!"
    else:
        return f"Hey {name}, burning the midnight oil?"

def should_greet(name: str) -> bool:
    """Check if enough time has passed to greet again."""
    last = _last_seen.get(name, 0)
    return (time.time() - last) > _greet_cooldown

def mark_greeted(name: str):
    _last_seen[name] = time.time()

# ── Camera loop ───────────────────────────────────────────────────────────────
def _watch_loop(cam_index: int, speak_func, listen_func,
                config: dict, calendar_func=None, sound_func=None):
    """Background thread — watches camera, triggers greetings."""

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(cam_index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[FaceWatcher] Camera watcher started.")
    last_face_time = 0
    check_interval = 2.0  # Check every 2 seconds

    while not _stop_event.is_set():
        time.sleep(check_interval)

        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(1)
            continue

        # Quick face detect first (cheap)
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        if len(faces) == 0:
            continue

        # Face detected — try to recognize
        name = recognize_face(frame)
        if not name:
            continue

        # Known face — should we greet?
        if not should_greet(name):
            continue

        mark_greeted(name)
        print(f"[FaceWatcher] Recognized: {name}")

        # Play recognition sound
        if sound_func:
            try:
                sound_func()
            except Exception:
                pass

        # Greeting
        greeting = get_greeting(name)
        speak_func(greeting)
        time.sleep(0.5)

        # Morning routine prompt
        hour = datetime.now().hour
        if 5 <= hour < 12:
            speak_func("Are you heading to work today or staying home?")
            answer = listen_func()
            if answer:
                answer_lower = answer.lower()
                if any(x in answer_lower for x in ["work", "going", "office", "heading", "leaving"]):
                    speak_func("Let me get you ready!")
                    # Weather
                    try:
                        from homeeye_functions import get_weather
                        location = config.get("weather_location", "Tampa Bay, FL")
                        weather  = get_weather(location, days=1)
                        speak_func(f"Weather: {weather}")
                    except Exception:
                        pass
                    # Traffic
                    try:
                        from homeeye_functions import get_traffic
                        traffic = get_traffic()
                        speak_func(f"Traffic: {traffic}")
                    except Exception:
                        pass
                    # Calendar
                    if calendar_func:
                        try:
                            cal = calendar_func(0)
                            speak_func(cal)
                        except Exception:
                            pass
                    speak_func("Have a great day! 73 de W4GGJ.")

                elif any(x in answer_lower for x in ["home", "staying", "here", "off", "not"]):
                    speak_func("Nice! Go grab your coffee and come back. Just say Hey Claude when you're ready.")

        elif 17 <= hour < 21:
            # Evening — welcome home
            speak_func("Welcome home! How was your day?")
            answer = listen_func()
            if answer:
                # Send to Claude for natural response
                pass  # Let the main loop handle it

        cap.release()
        # Reopen camera after greeting to reset
        time.sleep(2)
        cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(cam_index)

    cap.release()
    print("[FaceWatcher] Camera watcher stopped.")

# ── Public API ────────────────────────────────────────────────────────────────
def start_face_watcher(cam_index: int, speak_func, listen_func,
                        config: dict, calendar_func=None, sound_func=None):
    """Start the background face watcher thread."""
    global _watcher_thread
    _stop_event.clear()
    _watcher_thread = threading.Thread(
        target=_watch_loop,
        args=(cam_index, speak_func, listen_func, config, calendar_func, sound_func),
        daemon=True
    )
    _watcher_thread.start()
    print("[FaceWatcher] Started.")

def stop_face_watcher():
    """Stop the background face watcher."""
    _stop_event.set()
    if _watcher_thread:
        _watcher_thread.join(timeout=3)
    print("[FaceWatcher] Stopped.")

def set_greet_cooldown(seconds: int):
    """Set how long between greetings for the same person."""
    global _greet_cooldown
    _greet_cooldown = seconds
