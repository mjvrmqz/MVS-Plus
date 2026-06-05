#!/usr/bin/env python3
"""
agents_feed_to_ics.py

Generates a calendar feed (Agents Feed.ics) from the scheduled GitHub Actions
workflows in the MVS-Studios repo. No Notion involved — reads directly from
the workflow definitions hardcoded below.

Each scheduled workflow becomes a recurring calendar event. Manual-only
workflows (workflow_dispatch only) are skipped since they have no fixed time.

Run locally or via GitHub Actions to regenerate the .ics file.
"""

from datetime import datetime, timezone, timedelta
from ics import Calendar, Event
from ics.grammar.parse import ContentLine

OUTPUT_PATH = "Feeds/Agents/Agents Feed.ics"

# ─── AGENT DEFINITIONS ────────────────────────────────────────────────────────
# Each entry represents one scheduled workflow.
# "schedule" is a plain-English description of the cron.
# "rrule" is the iCal recurrence rule string.
# "next_run" is the next upcoming UTC occurrence used as the event start.
# Duration is 0 (instant marker event) — adjust if you want a window shown.

AGENTS = [
    {
        "name":        "Update Outreach Feed",
        "description": "Pulls outreach data from Notion and regenerates Outreach Feed.ics.",
        "schedule":    "Every 4 hours",
        "rrule":       "FREQ=HOURLY;INTERVAL=4",
        # Runs at :00 of every 4th hour — next anchor: 00:00 UTC
        "anchor":      "2026-06-05T00:00:00Z",
        "duration_min": 2,
    },
    {
        "name":        "Update Projects Feed",
        "description": "Pulls project data from Notion and regenerates Projects Feed.ics.",
        "schedule":    "Every 4 hours",
        "rrule":       "FREQ=HOURLY;INTERVAL=4",
        "anchor":      "2026-06-05T00:00:00Z",
        "duration_min": 2,
    },
    {
        "name":        "YouTube Outreach Agent",
        "description": "Runs the YouTube Scraper (5 min cap) then the YouTube Screener. Scrapes leads and scores channels for outreach compatibility.",
        "schedule":    "Every Saturday at 9:00 AM UTC",
        "rrule":       "FREQ=WEEKLY;BYDAY=SA",
        # Next Saturday at 09:00 UTC
        "anchor":      "2026-06-07T09:00:00Z",
        "duration_min": 180,
    },
]

# ─── BUILD CALENDAR ───────────────────────────────────────────────────────────

def build_calendar():
    cal = Calendar()

    for agent in AGENTS:
        e = Event()
        e.name        = f"⚙️ {agent['name']}"
        e.description = f"{agent['description']}\n\nSchedule: {agent['schedule']}"
        e.begin       = agent["anchor"]
        e.duration    = timedelta(minutes=agent["duration_min"])

        # Attach the RRULE so it repeats in calendar apps
        e.extra.append(ContentLine(f"RRULE:{agent['rrule']}"))

        cal.events.add(e)
        print(f"  Added: {agent['name']} ({agent['schedule']})")

    return cal

def main():
    print("Generating Agents Feed...")
    cal = build_calendar()

    with open(OUTPUT_PATH, "w") as f:
        f.writelines(cal)

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"  Wrote {OUTPUT_PATH} ({len(AGENTS)} agents) at {now}")

if __name__ == "__main__":
    main()
