"""iCalendar (RFC 5545) export and Google Calendar links. No OAuth needed: users subscribe to a private feed URL
in Google/Outlook/Apple Calendar, and every interview, follow-up and tracker next-step shows up there."""
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

PRODID = "-//Job Search AI Agent//Calendar//EN"


def _esc(text: str) -> str:
    """RFC 5545 TEXT escaping: backslash, semicolon, comma and newlines."""
    text = (text or "").replace("\\", "\\\\")
    for ch in ";,":
        text = text.replace(ch, "\\" + ch)
    return text.replace("\r\n", "\\n").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Lines longer than 75 octets are folded with CRLF + space (RFC 5545 §3.1), without splitting a UTF-8 char."""
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode())
            cur = b""
        cur += b
    out.append(cur.decode())
    return "\r\n ".join(out)


def _utc(dt: datetime) -> str:
    if dt.tzinfo is None:  # SQLite returns naive datetimes; we store UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def vevent(uid: str, title: str, start: datetime | date, *, minutes: int = 60, location: str | None = None,
           description: str | None = None, alarms: tuple[int, ...] = (1440, 60),
           now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{_utc(now)}", f"SUMMARY:{_esc(title)}"]
    if isinstance(start, datetime):
        lines += [f"DTSTART:{_utc(start)}", f"DTEND:{_utc(start + timedelta(minutes=minutes))}"]
    else:  # all-day
        lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{start + timedelta(days=1):%Y%m%d}"]
    if location:
        lines.append(f"LOCATION:{_esc(location)}")
    if description:
        lines.append(f"DESCRIPTION:{_esc(description)}")
    for m in alarms:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(title)}", f"TRIGGER:-PT{m}M", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def calendar(events: list[list[str]], name: str = "Job search") -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{_esc(name)}"]
    for ev in events:
        lines += ev
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(ln) for ln in lines) + "\r\n"


def google_link(title: str, start: datetime, minutes: int = 60, location: str | None = None,
                details: str | None = None) -> str:
    """'Add to Google Calendar' link (no API key or OAuth: opens a pre-filled event for the user to save)."""
    q = {"action": "TEMPLATE", "text": title,
         "dates": f"{_utc(start)}/{_utc(start + timedelta(minutes=minutes))}"}
    if location:
        q["location"] = location
    if details:
        q["details"] = details
    return "https://calendar.google.com/calendar/render?" + urlencode(q)
