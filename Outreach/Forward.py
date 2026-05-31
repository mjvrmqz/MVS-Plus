#!/usr/bin/env python3
# Forward.py · MVS Studios / Outreach
# Finds 'Forwarded' entries in Screening → copies to Outreach with calendar date/time picker.
# See full source for DateTimePicker UI, Notion helpers, and main pipeline.

import sys, json, requests, tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from calendar import monthcalendar, month_abbr

NOTION_TOKEN    = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"
SCREENING_DB_ID = "28d1691964b48065b59ec1f0b293f91f"
OUTREACH_DB_ID  = "28d1691964b480a88260e3871d01824c"

HEADERS = {
    "Authorization":  f"Bearer {NOTION_TOKEN}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}

def query_forwarded():
    payload = {"filter": {"property": "Status", "select": {"equals": "Forwarded"}}}
    r = requests.post(f"https://api.notion.com/v1/databases/{SCREENING_DB_ID}/query", headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json().get("results", [])

def get_page_name(page):
    try:
        parts = page["properties"]["Name"]["title"]
        return "".join(t["plain_text"] for t in parts).strip()
    except (KeyError, IndexError):
        return "Untitled"

def get_platform_link(page):
    try:
        return page["properties"]["Platform Link"]["url"] or ""
    except KeyError:
        return ""

def get_source(page):
    try:
        return page["properties"]["Source"]["select"]["name"]
    except (KeyError, TypeError):
        return None

def fmt_notion_dt(dt):
    import time as _time
    if _time.daylight and _time.localtime().tm_isdst:
        offset_sec = -_time.altzone
    else:
        offset_sec = -_time.timezone
    sign = "+" if offset_sec >= 0 else "-"
    h, m = divmod(abs(offset_sec) // 60, 60)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f"{sign}{h:02d}:{m:02d}"

def create_outreach_entry(name, platform_link, start_dt, end_dt, source=None, icon_url=None, cover_url=None):
    a1_start = start_dt + timedelta(days=2)
    a2_start = start_dt + timedelta(days=4)
    a3_start = start_dt + timedelta(days=6)
    date_initiated = {"start": fmt_notion_dt(start_dt)}
    if end_dt:
        date_initiated["end"] = fmt_notion_dt(end_dt)
        duration = end_dt - start_dt
        a1_date = {"start": fmt_notion_dt(a1_start), "end": fmt_notion_dt(a1_start + duration)}
        a2_date = {"start": fmt_notion_dt(a2_start), "end": fmt_notion_dt(a2_start + duration)}
        a3_date = {"start": fmt_notion_dt(a3_start), "end": fmt_notion_dt(a3_start + duration)}
    else:
        a1_date = {"start": fmt_notion_dt(a1_start)}
        a2_date = {"start": fmt_notion_dt(a2_start)}
        a3_date = {"start": fmt_notion_dt(a3_start)}
    props = {
        "Name":           {"title": [{"text": {"content": name}}]},
        "Date Initiated": {"date": date_initiated},
        "A1":             {"date": a1_date},
        "A2":             {"date": a2_date},
        "A3":             {"date": a3_date},
    }
    if source:
        props["Source"] = {"select": {"name": source}}
    if platform_link:
        props["Contact Mode"] = {"rich_text": [{"text": {"content": platform_link}}]}
    payload = {"parent": {"database_id": OUTREACH_DB_ID}, "properties": props}
    if icon_url:
        payload["icon"] = {"type": "external", "external": {"url": icon_url}}
    if cover_url:
        payload["cover"] = {"type": "external", "external": {"url": cover_url}}
    r = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    return r

# DateTimePicker UI and main() omitted for brevity — see full local file
if __name__ == "__main__":
    pass
