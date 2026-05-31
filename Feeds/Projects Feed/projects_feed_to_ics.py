#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timezone
from ics import Calendar, Event

# === CONFIG ===
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
DATABASE_ID  = "27d1691964b480639559d787b664900a"

if not NOTION_TOKEN:
    raise RuntimeError("NOTION_TOKEN environment variable not set.")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

DATE_PROPERTIES = ["Due Date"]

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
        desc_parts = []
        try:
            stage = entry["properties"]["Workflow Stage"]["select"]
            if stage: desc_parts.append(f"Stage: {stage['name']}")
        except (KeyError, TypeError): pass
        try:
            proj_type = entry["properties"]["Type"]["select"]
            if proj_type: desc_parts.append(f"Type: {proj_type['name']}")
        except (KeyError, TypeError): pass
        try:
            client = entry["properties"]["Client"]["select"]
            if client: desc_parts.append(f"Client: {client['name']}")
        except (KeyError, TypeError): pass
        try:
            notes_list = entry["properties"]["Client Notes"]["rich_text"]
            if notes_list: desc_parts.append(f"Notes: {notes_list[0]['plain_text']}")
        except (KeyError, IndexError, TypeError): pass
        description = " | ".join(desc_parts)
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
    with open("Feeds/Projects Feed/Projects Feed.ics", "w") as f:
        f.writelines(cal)
    print(f"  Wrote Feeds/Projects Feed/Projects Feed.ics ({event_count} events)")

def main():
    print("Querying Projects database...")
    entries = query_database(DATABASE_ID)
    print(f"  {len(entries)} entries found")
    create_ics(entries)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"Feed updated at {now}")

if __name__ == "__main__":
    main()
