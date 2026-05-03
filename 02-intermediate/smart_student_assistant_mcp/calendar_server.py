import json
import sys
from datetime import datetime, time, timedelta

from mcp.server.fastmcp import FastMCP


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)


mcp = FastMCP(
    "student_calendar_server",
    host="127.0.0.1",
    port=8101,
    streamable_http_path="/mcp",
)

def _event(title: str, day_offset: int, start_time: time, duration_minutes: int, location: str) -> dict:
    event_date = datetime.now().date() + timedelta(days=day_offset)
    start = datetime.combine(event_date, start_time)
    end = start + timedelta(minutes=duration_minutes)
    return {
        "title": title,
        "start": start.isoformat(timespec="minutes"),
        "end": end.isoformat(timespec="minutes"),
        "location": location,
    }


@mcp.tool()
def get_upcoming_events(days_ahead: int = 2) -> str:
    """Return upcoming student calendar events for the next few days."""
    today = datetime.now().date()
    events = [
        _event("AI Midterm Exam", 1, time(10, 0), 120, "Room C-204"),
        _event("Machine Learning Study Group", 0, time(18, 0), 60, "Library Discussion Hall"),
        _event("Data Structures Assignment Due", 2, time(23, 59), 1, "Online LMS"),
    ]

    cutoff = today + timedelta(days=max(days_ahead, 0))
    filtered = [
        event
        for event in events
        if today <= datetime.fromisoformat(event["start"]).date() <= cutoff
    ]

    return json.dumps(
        {
            "source": "student_calendar_server",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "days_ahead": days_ahead,
            "events": filtered,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
