#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timezone
from ics import Calendar, Event

# === CONFIG ===
NOTION_KEY = os.environ.get("NOTION_KEY", "")
DATABASE_ID  = "28d1691964b480a88260e3871d01824c"

if not NOTION_KEY:
    raise RuntimeError("NOTION_KEY environment variable not set.")

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

DATE_PROPERTIES = [
    "A1", "A2", "A3",
    "B1", "B2", "B3",
    "P1", "P2", "P3",
    "Date Initiated", "Date Engaged", "Date Pitched", "Date Closed",
]

def query_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    results = []
    payload = {}
    while True:
        resp = requests.post(url, headers=HEADERS, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Notion API error {resp.status_code}: {resp.text}")
        data = resp.json()
        results.extend(data["results"])
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results

def create_ics(entries):
    cal = Calendar()
    event_count = 0
    for entry in entries:
        try:
            name = entry["properties"]["Name"]["title"][0]["plain_text"]
        except (KeyError, IndexError, TypeError):
            continue
        try:
            contact_mode_list = entry["properties"]["Contact Mode"]["rich_text"]
            contact_mode = contact_mode_list[0]["plain_text"] if contact_mode_list else ""
        except (KeyError, IndexError, TypeError):
            contact_mode = ""
        description = f"Contact Mode: {contact_mode}" if contact_mode else ""
        for prop in DATE_PROPERTIES:
            try:
                date_val = entry["properties"][prop]["date"]
                if not date_val: continue
                start = date_val["start"]
                end = date_val.get("end") or start
            except (KeyError, TypeError): continue
            e = Event()
            e.name = f"{name} - {prop}"; e.begin = start; e.end = end; e.description = description
            cal.events.add(e)
            event_count += 1
    with open("Feeds/Outreach Feed/Outreach Feed.ics", "w") as f:
        f.writelines(cal)
    print(f"  Wrote Feeds/Outreach Feed/Outreach Feed.ics ({event_count} events)")

def main():
    print("Querying Outreach database...")
    entries = query_database(DATABASE_ID)
    print(f"  {len(entries)} entries found")
    create_ics(entries)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"Feed updated at {now}")

if __name__ == "__main__":
    main()
