"""
HomeEye Google Calendar Integration
Allows voice control of Google Calendar.
Author: Built for W4GGJ / Joe
"""

from pathlib import Path
from datetime import datetime, timedelta
import re

CREDS_FILE = Path("C:/HomeEye/calendar_credentials.json")
TOKEN_FILE = Path("C:/HomeEye/calendar_token.json")
SCOPES     = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Authenticate and return Google Calendar service."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if not CREDS_FILE.exists():
            return None, "calendar_credentials.json not found in C:\\HomeEye\\"
        flow  = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service, None

def get_events(day_offset: int = 0, max_results: int = 5) -> str:
    """Get calendar events for a specific day."""
    service, err = get_calendar_service()
    if err:
        return f"Calendar error: {err}"

    import pytz
    tz     = pytz.timezone("America/New_York")
    target = datetime.now(tz) + timedelta(days=day_offset)
    start  = target.replace(hour=0,  minute=0,  second=0,  microsecond=0)
    end    = target.replace(hour=23, minute=59, second=59, microsecond=0)

    start_str = start.isoformat()
    end_str   = end.isoformat()

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_str,
            timeMax=end_str,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if not events:
            day_name = "today" if day_offset == 0 else "tomorrow" if day_offset == 1 else target.strftime("%A")
            return f"You have no events scheduled {day_name}."

        day_name = "today" if day_offset == 0 else "tomorrow" if day_offset == 1 else target.strftime("%A")
        result   = f"You have {len(events)} event{'s' if len(events) > 1 else ''} {day_name}: "
        parts    = []

        for event in events:
            summary = event.get("summary", "Unnamed event")
            start_e = event["start"].get("dateTime", event["start"].get("date", ""))
            if "T" in start_e:
                dt = datetime.fromisoformat(start_e.replace("Z",""))
                time_str = dt.strftime("%I:%M %p").lstrip("0")
                parts.append(f"{summary} at {time_str}")
            else:
                parts.append(f"{summary} (all day)")

        result += ", ".join(parts) + "."
        return result

    except Exception as e:
        return f"Couldn't fetch calendar: {e}"

def add_event(summary: str, day_offset: int = 0, hour: int = 12, minute: int = 0, duration_hours: int = 1) -> str:
    """Add an event to Google Calendar."""
    service, err = get_calendar_service()
    if err:
        return f"Calendar error: {err}"

    target = datetime.now() + timedelta(days=day_offset)
    start  = target.replace(hour=hour, minute=minute, second=0, microsecond=0)
    end    = start + timedelta(hours=duration_hours)

    event = {
        "summary": summary,
        "start":   {"dateTime": start.isoformat(), "timeZone": "America/New_York"},
        "end":     {"dateTime": end.isoformat(),   "timeZone": "America/New_York"},
    }

    try:
        service.events().insert(calendarId="primary", body=event).execute()
        day_name = "today" if day_offset == 0 else "tomorrow" if day_offset == 1 else target.strftime("%A")
        return f"Added {summary} to your calendar {day_name} at {start.strftime('%I:%M %p').lstrip('0')}."
    except Exception as e:
        return f"Couldn't add event: {e}"

def get_next_event() -> str:
    """Get the next upcoming event."""
    service, err = get_calendar_service()
    if err:
        return f"Calendar error: {err}"

    now = datetime.utcnow().isoformat() + "Z"
    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=1,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "You have no upcoming events."

        event    = events[0]
        summary  = event.get("summary", "Unnamed event")
        start_e  = event["start"].get("dateTime", event["start"].get("date", ""))
        if "T" in start_e:
            dt       = datetime.fromisoformat(start_e.replace("Z",""))
            time_str = dt.strftime("%A %B %d at %I:%M %p")
        else:
            dt       = datetime.fromisoformat(start_e)
            time_str = dt.strftime("%A %B %d")

        return f"Your next event is {summary} on {time_str}."
    except Exception as e:
        return f"Couldn't fetch next event: {e}"

# ── Voice command parsing ──────────────────────────────────────────────────────
CALENDAR_KEYWORDS = [
    "calendar", "schedule", "appointment", "event", "meeting",
    "what do i have", "what's on", "add to calendar", "add event",
    "next appointment", "next event", "next meeting"
]

def is_calendar_command(text: str) -> bool:
    return any(kw in text.lower() for kw in CALENDAR_KEYWORDS)

def parse_time(text: str) -> tuple:
    """Parse hour and minute from text. Returns (hour24, minute)."""
    t = text.lower()
    hour, minute = 12, 0

    m = re.search(r'(\d+)(?::(\d+))?\s*(am|pm)', t)
    if m:
        hour   = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        if m.group(3) == "pm" and hour != 12:
            hour += 12
        elif m.group(3) == "am" and hour == 12:
            hour = 0
    return hour, minute

def parse_day_offset(text: str) -> int:
    t = text.lower()
    # Check tomorrow FIRST before any day-of-week checks
    if "tomorrow" in t:
        return 1
    # Check today explicitly
    if "today" in t:
        return 0
    # Day of week
    days = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,
            "friday":4,"saturday":5,"sunday":6}
    today_num = datetime.now().weekday()
    for day_name, day_num in days.items():
        if day_name in t:
            diff = (day_num - today_num) % 7
            return diff if diff > 0 else 7
    return 0

def handle_calendar_command(text: str) -> str:
    t = text.lower()

    # Add event — must have add/create AND event/calendar keywords
    if any(x in t for x in ["add event", "create event", "add to calendar",
                              "put on my calendar", "schedule a", "add a"]):
        # Extract event name — everything after add/create up to time words
        name = t
        for kw in ["add to calendar", "add event", "create event", "schedule", "add", "create", "put on my calendar"]:
            name = name.replace(kw, "").strip()
        # Remove time and day references
        name = re.sub(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|today)\b', '', name)
        name = re.sub(r'\d+(?::\d+)?\s*(?:am|pm)', '', name)
        name = re.sub(r'\bat\b', '', name).strip()
        name = name.strip(" ,.")
        if not name:
            name = "New Event"

        day_offset = parse_day_offset(t)
        hour, minute = parse_time(t)
        return add_event(name.title(), day_offset, hour, minute)

    # Next event
    elif any(x in t for x in ["next appointment", "next event", "next meeting"]):
        return get_next_event()

    # Today/tomorrow/day events
    else:
        day_offset = parse_day_offset(t)
        return get_events(day_offset)
