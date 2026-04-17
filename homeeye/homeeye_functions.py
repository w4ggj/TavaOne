"""
HomeEye Extended Functions
All the robust capabilities for HomeEye AI Assistant.
Author: Built for W4GGJ / Joe
"""

import os
import sys
import json
import time
import datetime
import subprocess
import threading
import urllib.request
import webbrowser
import platform
from pathlib import Path

# ── Weather ───────────────────────────────────────────────────────────────────
def get_weather(location: str = "Tampa Bay, FL", days: int = 1) -> str:
    """Fetch weather. days=1 for today, days=2 includes tomorrow, days=3 full forecast."""
    loc = location.replace(" ", "+")
    for attempt in range(3):
        try:
            if days == 1:
                # Current conditions only
                url = f"https://wttr.in/{loc}?format=3"
                req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
                resp = urllib.request.urlopen(req, timeout=15)
                return resp.read().decode("utf-8").strip()
            else:
                # Multi-day forecast as JSON
                url = f"https://wttr.in/{loc}?format=j1"
                req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
                resp = urllib.request.urlopen(req, timeout=15)
                import json as _json
                data = _json.loads(resp.read())
                weather = data["weather"]
                day_idx = days - 1  # 0=today, 1=tomorrow, 2=day after
                day_idx = min(day_idx, len(weather) - 1)
                day = weather[day_idx]
                avg_temp = day["avgtempF"]
                max_temp = day["maxtempF"]
                min_temp = day["mintempF"]
                desc     = day["hourly"][4]["weatherDesc"][0]["value"]
                chance   = day["hourly"][4].get("chanceofrain", "0")
                label    = ["Today", "Tomorrow", "Day after tomorrow"][day_idx]
                return f"{label} in {location}: {desc}, high of {max_temp}F, low of {min_temp}F, {chance}% chance of rain."
        except Exception as e:
            time.sleep(1)
    return "Weather service unavailable right now."

# ── Traffic ───────────────────────────────────────────────────────────────────
GOOGLE_MAPS_KEY = "AIzaSyAyc-EYqFnfPAoKz3dW7DlNGECLGOAwonQ"

# W4GGJ commute routes
# St Pete → I-275 → Selmon → I-75 → US-301 → CR-672 → Wimauma
TRAFFIC_ROUTES = [
    {
        "name":      "St Pete to Clearwater",
        "origin":    "4101 41st Ave N, St Petersburg, FL 33714",
        "dest":      "5040 140th Ave N, Clearwater, FL 33762",
        "waypoints": "",
    },
    {
        "name":      "Clearwater to Wimauma",
        "origin":    "5040 140th Ave N, Clearwater, FL 33762",
        "dest":      "14625 County Road 672, Wimauma, FL 33598",
        "waypoints": "",
    },
]

def get_traffic() -> str:
    """Get live traffic conditions via Google Maps Directions API."""
    results = []
    now_ts  = int(time.time())

    for route in TRAFFIC_ROUTES:
        try:
            import urllib.parse
            params = {
                "origin":       route["origin"],
                "destination":  route["dest"],
                "departure_time": "now",
                "traffic_model": "best_guess",
                "key":          GOOGLE_MAPS_KEY,
            }
            if route["waypoints"]:
                params["waypoints"] = route["waypoints"]

            url = "https://maps.googleapis.com/maps/api/directions/json?" + urllib.parse.urlencode(params)
            req  = urllib.request.Request(url, headers={"User-Agent": "HomeEye/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            if data["status"] != "OK":
                results.append(f"{route['name']}: {data['status']}")
                continue

            leg         = data["routes"][0]["legs"][0]
            normal_sec  = leg["duration"]["value"]
            traffic_sec = leg.get("duration_in_traffic", {}).get("value", normal_sec)
            normal_min  = normal_sec  // 60
            traffic_min = traffic_sec // 60
            delay_min   = max(0, traffic_min - normal_min)
            distance    = leg["distance"]["text"]

            if delay_min >= 15:
                status = f"heavy traffic, {delay_min} min delay"
            elif delay_min >= 8:
                status = f"moderate traffic, {delay_min} min delay"
            elif delay_min >= 3:
                status = f"light delays of {delay_min} minutes"
            else:
                status = "traffic is clear"

            results.append(f"{route['name']}: {traffic_min} minutes, {distance}, {status}")

        except Exception as e:
            results.append(f"{route['name']}: unavailable")

    return ". ".join(results)

TRAFFIC_KEYWORDS = ["traffic", "commute", "how long to", "drive time",
                    "road conditions", "how is traffic"]

def is_traffic_command(text: str) -> bool:
    return any(kw in text.lower() for kw in TRAFFIC_KEYWORDS)

def handle_traffic_command() -> str:
    traffic = get_traffic()
    return f"Live traffic update: {traffic}"

WEATHER_KEYWORDS = ["weather", "temperature", "forecast", "rain", "hot outside",
                    "cold outside", "humidity", "wind"]

def is_weather_command(text: str) -> bool:
    return any(kw in text.lower() for kw in WEATHER_KEYWORDS)

def handle_weather_command(text: str, config: dict) -> str:
    location = config.get("weather_location", "Tampa Bay, FL")
    t = text.lower()
    if "tomorrow" in t:
        return get_weather(location, days=2)
    elif "day after" in t or "two days" in t:
        return get_weather(location, days=3)
    elif "forecast" in t or "week" in t:
        today    = get_weather(location, days=1)
        tomorrow = get_weather(location, days=2)
        return f"{today} {tomorrow}"
    else:
        weather = get_weather(location, days=1)
        return f"Current conditions: {weather}"

# ── Time and Date ─────────────────────────────────────────────────────────────
TIME_KEYWORDS = ["what time", "what's the time", "current time", "what day",
                 "what date", "today's date", "what year"]

def is_time_command(text: str) -> bool:
    return any(kw in text.lower() for kw in TIME_KEYWORDS)

def handle_time_command(text: str) -> str:
    now  = datetime.datetime.now()
    t    = text.lower()
    if "date" in t or "day" in t:
        return f"Today is {now.strftime('%A, %B %d, %Y')}."
    elif "year" in t:
        return f"It's {now.year}."
    else:
        return f"The time is {now.strftime('%I:%M %p')}."

# ── Timers ────────────────────────────────────────────────────────────────────
_active_timers = {}

TIMER_KEYWORDS = ["set a timer", "timer for", "remind me in", "set timer",
                  "countdown", "alarm for"]

def is_timer_command(text: str) -> bool:
    return any(kw in text.lower() for kw in TIMER_KEYWORDS)

def handle_timer_command(text: str, speak_func) -> str:
    import re
    t = text.lower()

    minutes = 0
    seconds = 0

    m = re.search(r'(\d+)\s*minute', t)
    s = re.search(r'(\d+)\s*second', t)
    h = re.search(r'(\d+)\s*hour', t)

    if m:
        minutes += int(m.group(1))
    if s:
        seconds += int(s.group(1))
    if h:
        minutes += int(h.group(1)) * 60

    total_secs = minutes * 60 + seconds

    if total_secs <= 0:
        return "I didn't catch the timer duration. Try saying something like set a timer for 5 minutes."

    def timer_done():
        time.sleep(total_secs)
        speak_func("Timer complete!")

    t_thread = threading.Thread(target=timer_done, daemon=True)
    t_thread.start()

    if minutes > 0 and seconds > 0:
        return f"Timer set for {minutes} minutes and {seconds} seconds."
    elif minutes > 0:
        return f"Timer set for {minutes} minute{'s' if minutes != 1 else ''}."
    else:
        return f"Timer set for {seconds} seconds."

# ── Volume Control ────────────────────────────────────────────────────────────
VOLUME_KEYWORDS = ["volume up", "volume down", "turn up", "turn down",
                   "louder", "quieter", "mute", "unmute", "set volume"]

def is_volume_command(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in VOLUME_KEYWORDS) and \
           not any(x in t for x in ["light", "lamp", "fan", "plug"])

def handle_volume_command(text: str) -> str:
    import re
    t = text.lower()

    try:
        if "mute" in t and "unmute" not in t:
            subprocess.run(["powershell", "-c",
                "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"],
                capture_output=True)
            return "Volume muted."

        elif "unmute" in t:
            subprocess.run(["powershell", "-c",
                "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"],
                capture_output=True)
            return "Volume unmuted."

        # Check for specific percentage
        pct = re.search(r'(\d+)\s*(%|percent)', t)
        if pct:
            level = int(pct.group(1))
            subprocess.run(["powershell", "-c",
                f"$wshShell = New-Object -ComObject wscript.shell; "
                f"[audio]::Volume = {level/100}"],
                capture_output=True)
            return f"Volume set to {level} percent."

        elif any(x in t for x in ["up", "louder", "increase", "raise"]):
            for _ in range(5):
                subprocess.run(["powershell", "-c",
                    "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]175)"],
                    capture_output=True)
            return "Volume increased."

        elif any(x in t for x in ["down", "quieter", "decrease", "lower"]):
            for _ in range(5):
                subprocess.run(["powershell", "-c",
                    "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]174)"],
                    capture_output=True)
            return "Volume decreased."

        return "Volume adjusted."
    except Exception as e:
        return f"Couldn't adjust volume: {e}"

# ── Open Applications ─────────────────────────────────────────────────────────
APP_KEYWORDS = ["open ", "launch ", "start ", "run "]

KNOWN_APPS = {
    "notepad":      "notepad.exe",
    "calculator":   "calc.exe",
    "file explorer": "explorer.exe",
    "explorer":     "explorer.exe",
    "task manager": "taskmgr.exe",
    "paint":        "mspaint.exe",
    "wordpad":      "wordpad.exe",
    "vlc":          "vlc",
    "chrome":       "chrome",
    "firefox":      "firefox",
    "spotify":      "spotify",
    "discord":      "discord",
    "wsjt":         "wsjtx",
    "wsjtx":        "wsjtx",
    "fldigi":       "fldigi",
    "hamclock":     "hamclock",
    "log4om":       "log4om",
}

def is_app_command(text: str) -> bool:
    t = text.lower()
    return (any(kw in t for kw in APP_KEYWORDS) and
            not any(x in t for x in [".com", ".net", ".org", "website", "site"]) and
            not any(x in t for x in ["light", "lamp", "plug", "fan"]))

def handle_app_command(text: str) -> str:
    t = text.lower()
    for kw in sorted(APP_KEYWORDS, key=len, reverse=True):
        t = t.replace(kw, "").strip()

    for name, exe in KNOWN_APPS.items():
        if name in t:
            try:
                subprocess.Popen(exe, shell=True)
                return f"Opening {name}."
            except Exception as e:
                return f"Couldn't open {name}: {e}"

    # Try opening whatever was said as a program name
    try:
        subprocess.Popen(t, shell=True)
        return f"Attempting to open {t}."
    except Exception:
        return f"I couldn't find an app called {t}."

# ── System Info ───────────────────────────────────────────────────────────────
SYSINFO_KEYWORDS = ["ip address", "my ip", "cpu", "memory", "ram",
                    "disk space", "system info", "computer name",
                    "what's my ip", "uptime"]

def is_sysinfo_command(text: str) -> bool:
    return any(kw in text.lower() for kw in SYSINFO_KEYWORDS)

def handle_sysinfo_command(text: str) -> str:
    t = text.lower()
    try:
        if "ip" in t:
            result = subprocess.run(["powershell", "-c",
                "(Test-Connection -ComputerName (hostname) -Count 1).IPV4Address.IPAddressToString"],
                capture_output=True, text=True, timeout=5)
            ip = result.stdout.strip()
            if not ip:
                import socket
                ip = socket.gethostbyname(socket.gethostname())
            return f"Your IP address is {ip}."

        elif "cpu" in t:
            result = subprocess.run(["powershell", "-c",
                "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty LoadPercentage"],
                capture_output=True, text=True, timeout=5)
            cpu = result.stdout.strip()
            return f"CPU usage is {cpu} percent."

        elif "ram" in t or "memory" in t:
            result = subprocess.run(["powershell", "-c",
                "$os = Get-WmiObject Win32_OperatingSystem; "
                "[math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100)"],
                capture_output=True, text=True, timeout=5)
            ram = result.stdout.strip()
            return f"Memory usage is {ram} percent."

        elif "disk" in t:
            result = subprocess.run(["powershell", "-c",
                "$d = Get-PSDrive C; [math]::Round($d.Used/($d.Used+$d.Free)*100)"],
                capture_output=True, text=True, timeout=5)
            disk = result.stdout.strip()
            return f"C drive is {disk} percent full."

        elif "computer name" in t or "hostname" in t:
            import socket
            return f"This computer's name is {socket.gethostname()}."

        elif "uptime" in t:
            result = subprocess.run(["powershell", "-c",
                "(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime | Select-Object -ExpandProperty TotalHours"],
                capture_output=True, text=True, timeout=5)
            hours = float(result.stdout.strip())
            return f"System has been running for {int(hours)} hours."

        return "What system information do you need? Try asking for IP address, CPU, memory, or disk space."

    except Exception as e:
        return f"Couldn't get system info: {e}"

# ── Screenshot ────────────────────────────────────────────────────────────────
SCREENSHOT_KEYWORDS = ["take a screenshot", "screenshot", "capture screen",
                       "grab screen", "screen capture"]

def is_screenshot_command(text: str) -> bool:
    return any(kw in text.lower() for kw in SCREENSHOT_KEYWORDS)

def handle_screenshot_command(text: str) -> str:
    try:
        ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(Path.home() / "Pictures" / f"HomeEye_{ts}.png")
        subprocess.run(["powershell", "-c",
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.Screen]::AllScreens | ForEach-Object {{ "
            f"$bmp = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height); "
            f"$g = [System.Drawing.Graphics]::FromImage($bmp); "
            f"$g.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size); "
            f"$bmp.Save('{path}') }}"],
            capture_output=True, timeout=10)
        return f"Screenshot saved to Pictures folder."
    except Exception as e:
        return f"Couldn't take screenshot: {e}"

# ── Music / Media Control ─────────────────────────────────────────────────────
MEDIA_KEYWORDS = ["play music", "pause music", "stop music", "next song",
                  "previous song", "skip song", "play", "pause", "next track",
                  "previous track"]

def is_media_command(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in MEDIA_KEYWORDS) and \
           not any(x in t for x in ["pota", "radio", "ft8", "cq"])

def handle_media_command(text: str) -> str:
    t = text.lower()
    try:
        if "next" in t or "skip" in t:
            subprocess.run(["powershell", "-c",
                "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]176)"],
                capture_output=True)
            return "Skipping to next track."

        elif "previous" in t or "back" in t:
            subprocess.run(["powershell", "-c",
                "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]177)"],
                capture_output=True)
            return "Going to previous track."

        elif "pause" in t or "stop" in t:
            subprocess.run(["powershell", "-c",
                "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]179)"],
                capture_output=True)
            return "Pausing music."

        elif "play" in t:
            subprocess.run(["powershell", "-c",
                "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]179)"],
                capture_output=True)
            return "Playing music."

        return "Media command received."
    except Exception as e:
        return f"Couldn't control media: {e}"

# ── Dictation / Type ──────────────────────────────────────────────────────────
DICTATION_KEYWORDS = ["type ", "dictate ", "write ", "type this"]

def is_dictation_command(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in DICTATION_KEYWORDS) and len(text) > 10

def handle_dictation_command(text: str) -> str:
    t = text.lower()
    for kw in sorted(DICTATION_KEYWORDS, key=len, reverse=True):
        t = t.replace(kw, "").strip()

    if not t:
        return "What would you like me to type?"

    try:
        # Small delay to let user focus desired window
        time.sleep(1.5)
        subprocess.run(["powershell", "-c",
            f"$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys('{t}')"],
            capture_output=True)
        return f"Typed: {t}"
    except Exception as e:
        return f"Couldn't type that: {e}"

# ── Web Browser ───────────────────────────────────────────────────────────────
WEB_KEYWORDS = ["open ", "go to ", "browse to ", "navigate to ",
                "pull up ", "show me "]

def is_web_command(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in WEB_KEYWORDS) and any(
        x in t for x in [".com", ".net", ".org", ".gov", ".io",
                          ".tv", "website", "site"]
    )

def handle_web_command(text: str) -> str:
    t = text.lower()
    for kw in sorted(WEB_KEYWORDS, key=len, reverse=True):
        t = t.replace(kw, "").strip()

    t = t.replace(" dot com", ".com").replace(" dot net", ".net") \
         .replace(" dot org", ".org").replace(" dot gov", ".gov") \
         .replace(" dot io", ".io").replace(" dot tv", ".tv") \
         .replace(" dot ", ".").strip().rstrip(".,!?")

    url = "https://" + t if not t.startswith("http") else t

    try:
        webbrowser.get("chrome").open(url)
        return f"Opening {t} in Chrome."
    except Exception:
        webbrowser.open(url)
        return f"Opening {t} in your browser."
