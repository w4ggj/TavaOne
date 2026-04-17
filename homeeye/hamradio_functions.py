"""
HomeEye Ham Radio & Utility Functions
DX Cluster, Band Conditions, Morning Routine, Ham Facts, Network Monitor
Author: Built for W4GGJ / Joe
"""

import urllib.request
import urllib.error
import json
import random
import subprocess
import socket
import time
from datetime import datetime

# ── Pushover Notifications ───────────────────────────────────────────────────
PUSHOVER_TOKEN = "akbhhsjk3g691dhce9fi778db81561"
PUSHOVER_USER  = "u2awjv54deq5hew939pir3tz3yjgeu"

def send_pushover(title: str, message: str, priority: int = 0) -> bool:
    """Send a push notification via Pushover."""
    try:
        import urllib.parse
        data = urllib.parse.urlencode({
            "token":    PUSHOVER_TOKEN,
            "user":     PUSHOVER_USER,
            "title":    title,
            "message":  message,
            "priority": priority,
        }).encode()
        req  = urllib.request.Request(
            "https://api.pushover.net/1/messages.json",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        urllib.request.urlopen(req, timeout=10)
        print("[Pushover] Notification sent!")
        return True
    except Exception as e:
        print(f"[Pushover Error]: {e}")
        return False

def push_morning_briefing(weather: str, traffic: str, calendar: str,
                           bands: str, going_to_work: bool):
    """Send morning briefing summary to phone."""
    now   = datetime.now()
    title = f"Good Morning Joe! {now.strftime('%A %b %d')}"

    lines = []
    if weather:
        lines.append(f"🌤 {weather}")
    if going_to_work and traffic:
        lines.append(f"🚗 {traffic}")
    if calendar:
        lines.append(f"📅 {calendar}")
    if bands:
        lines.append(f"📻 {bands}")

    message = "
".join(lines)
    send_pushover(title, message)

# ── Ham Radio Facts ───────────────────────────────────────────────────────────
HAM_FACTS = [
    "The first transatlantic radio transmission was made by Guglielmo Marconi in 1901.",
    "FT8 can decode signals 15 dB below the noise floor, making it incredible for weak signal work.",
    "The highest amateur radio frequency allocation is 250 GHz.",
    "There are over 3 million licensed amateur radio operators worldwide.",
    "The International Space Station has an amateur radio station with callsign NA1SS.",
    "Morse code was first used commercially in 1844 by Samuel Morse.",
    "The 40 meter band is often called the workhorse band because it works day and night.",
    "QRP means low power operation, typically 5 watts or less — just like your Xiegu X6200!",
    "The phonetic alphabet used in ham radio NATO standard was adopted in 1956.",
    "ARRL was founded in 1914 by Hiram Percy Maxim.",
    "The first ham satellite, OSCAR 1, was launched in 1961.",
    "DX means distance — working DX means contacting stations far away.",
    "The gray line is a narrow band around Earth where conditions are ideal for DX.",
    "Sunspot cycle 25 peaked in late 2024, making HF conditions excellent.",
    "Parks on the Air was founded in 2017 after the ARRL National Parks event ended.",
    "The 20 meter band is the most popular HF band for long distance contacts.",
    "A dipole antenna cut for 20 meters is about 33 feet long on each side.",
    "SSB stands for Single Sideband — it uses half the bandwidth of AM.",
    "The Q code was developed in 1909 for use by maritime radio operators.",
    "Lightning is the number one cause of damage to amateur radio equipment.",
    "The ionosphere has four layers: D, E, F1, and F2 — F2 reflects HF signals the furthest.",
    "WSPR stands for Weak Signal Propagation Reporter — hams use it to map band conditions.",
    "The 60 meter band has only 5 channels and requires specific modes and power limits.",
    "A general class license in the US grants HF privileges on most amateur bands.",
    "Radio silence during emergencies is called QRTN — the frequency is in use for emergency traffic.",
]

FACT_KEYWORDS = ["ham radio fact", "radio fact", "fact of the day", "did you know", "tell me something"]

def is_fact_command(text: str) -> bool:
    return any(kw in text.lower() for kw in FACT_KEYWORDS)

def handle_fact_command() -> str:
    return random.choice(HAM_FACTS)

# ── Band Conditions ───────────────────────────────────────────────────────────
BAND_KEYWORDS = ["band conditions", "propagation", "solar flux", "solar conditions",
                 "how are the bands", "hf conditions", "dx conditions", "k index", "a index"]

def is_band_command(text: str) -> bool:
    return any(kw in text.lower() for kw in BAND_KEYWORDS)

def handle_band_command() -> str:
    try:
        # Fetch from HamQSL solar data XML
        url = "https://www.hamqsl.com/solarxml.php"
        req = urllib.request.Request(url, headers={"User-Agent": "HomeEye/1.0 W4GGJ"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("utf-8")

        import xml.etree.ElementTree as ET
        root = ET.fromstring(data)
        solar = root.find(".//solardata")

        if solar is None:
            return "Couldn't parse solar data."

        sfi    = solar.findtext("solarflux", "unknown")
        aindex = solar.findtext("aindex",    "unknown")
        kindex = solar.findtext("kindex",    "unknown")
        xray   = solar.findtext("xray",      "unknown")
        sunspots = solar.findtext("sunspots", "unknown")

        # Band conditions
        bands = []
        for band in ["80m-40m","30m-20m","17m-15m","12m-10m"]:
            day   = solar.findtext(f"calculatedconditions/band[@name='{band}'][@time='day']",   "unknown")
            night = solar.findtext(f"calculatedconditions/band[@name='{band}'][@time='night']", "unknown")
            bands.append(f"{band} day {day}")

        band_str = ", ".join(bands)

        return (f"Solar flux is {sfi}, A-index {aindex}, K-index {kindex}, "
                f"sunspots {sunspots}. Band conditions: {band_str}. "
                f"X-ray flux: {xray}.")

    except Exception as e:
        return f"Couldn't fetch band conditions: {e}"

# ── DX Cluster ────────────────────────────────────────────────────────────────
DX_KEYWORDS = ["dx cluster", "dx spots", "any dx", "rare dx", "dx alert",
               "what dx", "check dx", "dx report"]

def is_dx_command(text: str) -> bool:
    return any(kw in text.lower() for kw in DX_KEYWORDS)

def handle_dx_command(config: dict) -> str:
    try:
        # Use DX Summit API for recent spots
        bands = config.get("dx_bands", ["20m", "17m", "15m", "40m"])
        url   = "https://www.dxsummit.fi/api/v1/spots?limit=20"
        req   = urllib.request.Request(url, headers={"User-Agent": "HomeEye/1.0 W4GGJ"})
        resp  = urllib.request.urlopen(req, timeout=10)
        spots = json.loads(resp.read())

        if not spots:
            return "No DX spots found right now."

        # Filter for interesting spots
        rare_entities = config.get("dx_rare_entities", [])
        interesting   = []

        for spot in spots[:20]:
            dx_call = spot.get("dx_call", "")
            freq    = spot.get("frequency", 0)
            comment = spot.get("comment", "")
            spotter = spot.get("spotter_call", "")

            # Convert freq to band
            freq_mhz = float(freq) / 1000 if freq else 0
            if 1.8 <= freq_mhz <= 2.0:   band = "160m"
            elif 3.5 <= freq_mhz <= 4.0: band = "80m"
            elif 7.0 <= freq_mhz <= 7.3: band = "40m"
            elif 10.1 <= freq_mhz <= 10.15: band = "30m"
            elif 14.0 <= freq_mhz <= 14.35: band = "20m"
            elif 18.068 <= freq_mhz <= 18.168: band = "17m"
            elif 21.0 <= freq_mhz <= 21.45: band = "15m"
            elif 24.89 <= freq_mhz <= 24.99: band = "12m"
            elif 28.0 <= freq_mhz <= 29.7: band = "10m"
            else: band = "other"

            if band in bands:
                interesting.append(f"{dx_call} on {band} at {freq_mhz:.1f} MHz")

        if not interesting:
            return f"No DX spots on your bands right now. Bands monitored: {', '.join(bands)}."

        result = f"Found {len(interesting)} DX spot{'s' if len(interesting) > 1 else ''}: "
        result += ". ".join(interesting[:5])
        return result

    except Exception as e:
        return f"Couldn't fetch DX cluster: {e}"

# ── Network Monitor ───────────────────────────────────────────────────────────
NETWORK_KEYWORDS = ["network status", "internet status", "is the internet",
                    "network check", "ping", "connection status", "am i connected"]

def is_network_command(text: str) -> bool:
    return any(kw in text.lower() for kw in NETWORK_KEYWORDS)

def handle_network_command() -> str:
    results = []

    # Check internet connectivity
    hosts = [
        ("Google",      "8.8.8.8"),
        ("Cloudflare",  "1.1.1.1"),
        ("ARRL",        "www.arrl.org"),
    ]

    online = 0
    for name, host in hosts:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 80 if "." in host and not host[0].isdigit() else 53))
            online += 1
        except Exception:
            results.append(f"{name} unreachable")

    if online == len(hosts):
        status = "Internet connection is good."
    elif online > 0:
        status = f"Partial connectivity — {', '.join(results)}."
    else:
        status = "No internet connection detected!"

    # Get local IP
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        status += f" Local IP is {local_ip}."
    except Exception:
        pass

    # Ping latency to Google
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "8.8.8.8"],
            capture_output=True, text=True, timeout=5
        )
        if "ms" in result.stdout:
            import re
            ms = re.search(r"Average = (\d+)ms", result.stdout)
            if ms:
                status += f" Latency is {ms.group(1)} milliseconds."
    except Exception:
        pass

    return status

# ── Morning Routine ───────────────────────────────────────────────────────────
MORNING_KEYWORDS = ["good morning", "morning routine", "start my day",
                    "wake up routine", "morning briefing"]

def is_morning_command(text: str) -> bool:
    return any(kw in text.lower() for kw in MORNING_KEYWORDS)

def get_traffic(origin: str, destination: str) -> str:
    """Get basic traffic info via a simple web check."""
    try:
        # Use wttr for a basic commute weather check
        from homeeye_functions import get_weather
        weather = get_weather(origin, days=1)
        return f"Weather along your route: {weather} Allow extra time if conditions are poor."
    except Exception:
        return "Couldn't fetch traffic data right now."

def handle_morning_command(config: dict, speak_func, listen_func, calendar_func=None) -> str:
    now = datetime.now()

    # Step 1 — Greeting and question, NO wake word needed for response
    speak_func(f"Good morning Joe! Are you heading to work today or staying home?")

    # Step 2 — Listen for answer without requiring wake word
    answer = listen_func()

    if answer is None:
        # No response heard — do full briefing anyway
        speak_func("I didn't catch that — let me give you your full morning briefing.")
        _full_briefing(config, speak_func, calendar_func)
        return ""

    answer_lower = answer.lower()

    if any(x in answer_lower for x in ["work", "going", "office", "heading out", "leaving"]):
        # Work day routine
        speak_func("Heading to work! Let me get you ready.")
        time.sleep(0.3)

        # Weather for commute
        try:
            from homeeye_functions import get_weather
            location = config.get("weather_location", "Tampa Bay, FL")
            weather  = get_weather(location, days=1)
            speak_func(f"Commute weather: {weather}")
        except Exception:
            pass

        # Traffic
        try:
            from homeeye_functions import get_traffic
            traffic = get_traffic()
            speak_func(f"Live traffic: {traffic}")
        except Exception:
            speak_func("Check Google Maps for traffic before you head out.")

        # Today's calendar
        if calendar_func:
            try:
                cal = calendar_func(0)
                speak_func(f"Today on your calendar: {cal}")
            except Exception:
                pass

        # Band conditions quick
        try:
            bands = handle_band_command()
            speak_func(f"Quick band report: {bands}")
        except Exception:
            pass

        speak_func("Have a great day Joe! 73 de W4GGJ.")

        # Push briefing to phone
        try:
            w = weather if 'weather' in locals() else ""
            t = traffic if 'traffic' in locals() else ""
            c = cal     if 'cal'     in locals() else ""
            b = bands   if 'bands'   in locals() else ""
            push_morning_briefing(w, t, c, b, going_to_work=True)
        except Exception as e:
            print(f"[Push Error]: {e}")

    elif any(x in answer_lower for x in ["home", "staying", "here", "not going", "day off", "working from"]):
        # Stay home routine
        speak_func("Staying home — nice! Go make your coffee and come back for your full briefing.")

        # Wait for them to come back — listen for any response
        speak_func("Just say Hey Claude when you're ready.")

    else:
        # Unclear answer — do full briefing
        _full_briefing(config, speak_func, calendar_func)

    return ""

def _full_briefing(config: dict, speak_func, calendar_func=None):
    """Full morning briefing — weather, calendar, bands, fact."""
    now = datetime.now()
    speak_func(f"It's {now.strftime('%A, %B %d')} and the time is {now.strftime('%I:%M %p')}.")

    try:
        from homeeye_functions import get_weather
        location = config.get("weather_location", "Tampa Bay, FL")
        weather  = get_weather(location, days=1)
        speak_func(f"Weather: {weather}")
    except Exception:
        pass

    if calendar_func:
        try:
            cal = calendar_func(0)
            speak_func(cal)
        except Exception:
            pass

    try:
        bands = handle_band_command()
        speak_func(f"Ham radio: {bands}")
    except Exception:
        pass

    fact = handle_fact_command()
    speak_func(f"Ham fact of the day: {fact}")

# ── Goodnight Routine ─────────────────────────────────────────────────────────
GOODNIGHT_KEYWORDS = ["good night", "goodnight routine", "end my day",
                      "going to bed", "night routine"]

def is_goodnight_command(text: str) -> bool:
    return any(kw in text.lower() for kw in GOODNIGHT_KEYWORDS)

def handle_goodnight_command(config: dict, speak_func, smartthings_func=None, calendar_func=None) -> str:
    speak_func("Goodnight Joe! Let me wrap things up for you.")

    # Tomorrow's calendar
    if calendar_func:
        try:
            cal = calendar_func(1)
            speak_func(f"Tomorrow: {cal}")
        except Exception:
            pass

    # Turn off all lights
    if smartthings_func:
        try:
            smartthings_func("turn off all lights")
            speak_func("All lights are off.")
        except Exception:
            pass

    speak_func("Have a great night. 73 de W4GGJ.")
    return ""
