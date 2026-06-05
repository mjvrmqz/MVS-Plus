#!/usr/bin/env python3
"""
agents_feed_to_ics.py

Generates a calendar feed (Agents Feed.ics) from the scheduled GitHub Actions
workflows in the MVS-Studios repo. No Notion involved — reads directly from
the workflow definitions hardcoded below.

Each scheduled workflow becomes a recurring calendar event. Manual-only
workflows (workflow_dispatch only) are skipped since they have no fixed time.

Vague schedules (e.g. "every 4 hours") become all-day recurring events.
Schedules with a specific time become timed recurring events.

Run locally or via GitHub Actions to regenerate the .ics file.
"""

from datetime import datetime, timezone, timedelta
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

OUTPUT_PATH = "Feeds/Agents/Agents Feed.ics"

# ─── AGENT DEFINITIONS ────────────────────────────────────────────────────────
# all_day=True  → no specific time, shows as an all-day recurring event (FREQ=DAILY)
# all_day=False → specific time, shows as a timed event with duration

AGENTS = [
    {
        "name":        "Update Outreach Feed",
        "description": "Pulls outreach data from Notion and regenerates Outreach Feed.ics.",
        "schedule":    "Every 4 hours",
        "all_day":     True,
        "anchor":      "20260605",           # DATE only (no time)
        "rrule":       "FREQ=DAILY",
    },
    {
        "name":        "Update Projects Feed",
        "description": "Pulls project data from Notion and regenerates Projects Feed.ics.",
        "schedule":    "Every 4 hours",
        "all_day":     True,
        "anchor":      "20260605",
        "rrule":       "FREQ=DAILY",
    },
    {
        "name":        "YouTube Outreach Agent",
        "description": "Runs the YouTube Scraper (5 min cap) then the YouTube Screener. Scrapes leads and scores channels for outreach compatibility.",
        "schedule":    "Every Saturday at 9:00 AM PDT",
        "all_day":     False,
        "anchor":      "20260606T160000Z",   # 9:00 AM PDT = 16:00 UTC; 20260606 = Saturday
        "rrule":       "FREQ=WEEKLY;BYDAY=SA",
        "duration_min": 180,
    },
]

# ─── BUILD CALENDAR ───────────────────────────────────────────────────────────

def build_calendar():
    cal = Calendar()

    for agent in AGENTS:
        description = f"{agent['description']}\n\nSchedule: {agent['schedule']}"

        if agent["all_day"]:
            vevent = (
                "BEGIN:VEVENT\r\n"
                f"DTSTART;VALUE=DATE:{agent['anchor']}\r\n"
                f"RRULE:{agent['rrule']}\r\n"
                f"SUMMARY:{agent['name']}\r\n"
                f"DESCRIPTION:{description}\r\n"
                "END:VEVENT\r\n"
            )
            cal._unused.append(vevent)
        else:
            e = Event()
            e.name        = agent['name']
            e.description = description
            e.begin       = agent["anchor"]
            e.duration    = timedelta(minutes=agent["duration_min"])
            e.extra.append(ContentLine(f"RRULE:{agent['rrule']}"))
            cal.events.add(e)

        print(f"  Added: {agent['name']} ({'all-day' if agent['all_day'] else agent['schedule']})")

    return cal

def main():
    print("Generating Agents Feed...")

    lines = [
        "BEGIN:VCALENDAR\r\n",
        "VERSION:2.0\r\n",
        "PRODID:-//MVS Studios//Agents Feed//EN\r\n",
        "CALSCALE:GREGORIAN\r\n",
        "METHOD:PUBLISH\r\n",
        "X-WR-CALNAME:MVS Studios — Agents\r\n",
        "X-WR-TIMEZONE:UTC\r\n",
    ]

    for agent in AGENTS:
        description = f"{agent['description']}\\n\\nSchedule: {agent['schedule']}"
        if agent["all_day"]:
            lines += [
                "BEGIN:VEVENT\r\n",
                f"DTSTART;VALUE=DATE:{agent['anchor']}\r\n",
                f"RRULE:{agent['rrule']}\r\n",
                f"SUMMARY:{agent['name']}\r\n",
                f"DESCRIPTION:{description}\r\n",
                "END:VEVENT\r\n",
            ]
        else:
            end_dt = datetime.strptime(agent["anchor"], "%Y%m%dT%H%M%SZ") + timedelta(minutes=agent["duration_min"])
            end_str = end_dt.strftime("%Y%m%dT%H%M%SZ")
            lines += [
                "BEGIN:VEVENT\r\n",
                f"DTSTART:{agent['anchor']}\r\n",
                f"DTEND:{end_str}\r\n",
                f"RRULE:{agent['rrule']}\r\n",
                f"SUMMARY:{agent['name']}\r\n",
                f"DESCRIPTION:{description}\r\n",
                "END:VEVENT\r\n",
            ]
        print(f"  Added: {agent['name']} ({'all-day' if agent['all_day'] else agent['schedule']})")

    lines.append("END:VCALENDAR\r\n")

    with open(OUTPUT_PATH, "w") as f:
        f.writelines(lines)

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"  Wrote {OUTPUT_PATH} ({len(AGENTS)} agents) at {now}")

if __name__ == "__main__":
    main()
