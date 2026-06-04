#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
#  Method_ReplyRate.py  ·  MVS Studios / Outreach
#  Reads the Outreach database, groups by Method, counts how
#  many prospects were Initiated vs Engaged (replied), then
#  writes the results into the Method / Reply Rate % database
#  — one row per method. Notion's Reply Rate % formula column
#  then auto-calculates Engaged / Initiated * 100.
# ─────────────────────────────────────────────────────────────

import sys, requests
import os

# ── Config ────────────────────────────────────────────────────
NOTION_KEY     = os.environ.get("NOTION_KEY", "")
OUTREACH_DB_ID   = "28d1691964b480a88260e3871d01824c"
REPLY_RATE_DB_ID = "3601691964b480d0851cd9868b606e1f"

HEADERS = {
    "Authorization":  f"Bearer {NOTION_KEY}",
    "Content-Type":   "application/json",
    "Notion-Version": "2022-06-28",
}

METHODS = ["HVR", "Loom Alchemy", "Omni Application", "Hybrid"]

# ── Helpers ───────────────────────────────────────────────────
def has_date(page, prop_name):
    try:
        return bool(page["properties"][prop_name]["date"])
    except (KeyError, TypeError):
        return False

def get_select(page, prop_name):
    try:
        sel = page["properties"][prop_name]["select"]
        return sel["name"] if sel else None
    except (KeyError, TypeError):
        return None

def get_title(page, prop_name):
    try:
        parts = page["properties"][prop_name]["title"]
        return parts[0]["plain_text"] if parts else None
    except (KeyError, TypeError, IndexError):
        return None

# ── Fetch all Outreach rows (handles pagination) ──────────────
def fetch_all_outreach():
    pages, payload = [], {"page_size": 100}
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{OUTREACH_DB_ID}/query",
            headers=HEADERS, json=payload,
        )
        r.raise_for_status()
        data = r.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return pages

# ── Crunch numbers ────────────────────────────────────────────
def calculate_stats(pages):
    stats = {m: {"initiated": 0, "engaged": 0} for m in METHODS}

    for page in pages:
        method = get_select(page, "Method")
        if method not in stats:
            continue  # skip rows with no method or unknown method

        if has_date(page, "Date Initiated"):
            stats[method]["initiated"] += 1
        if has_date(page, "Date Engaged"):
            stats[method]["engaged"] += 1

    return stats

# ── Fetch existing rows from Reply Rate DB ────────────────────
def fetch_existing_rows():
    """Returns {method_name: page_id} for existing rows."""
    r = requests.post(
        f"https://api.notion.com/v1/databases/{REPLY_RATE_DB_ID}/query",
        headers=HEADERS, json={"page_size": 100},
    )
    r.raise_for_status()
    rows = {}
    for page in r.json().get("results", []):
        method = get_title(page, "Method")
        if method:
            rows[method] = page["id"]
    return rows

# ── Build Notion properties payload ──────────────────────────
def build_props(method, s):
    return {
        "Method":    {"title": [{"text": {"content": method}}]},
        "Initiated": {"number": s["initiated"]},
        "Engaged":   {"number": s["engaged"]},
    }

# ── Upsert rows ───────────────────────────────────────────────
def upsert_rows(stats, existing):
    for method, s in stats.items():
        props = build_props(method, s)

        if method in existing:
            r = requests.patch(
                f"https://api.notion.com/v1/pages/{existing[method]}",
                headers=HEADERS, json={"properties": props},
            )
            action = "Updated"
        else:
            r = requests.post(
                "https://api.notion.com/v1/pages",
                headers=HEADERS,
                json={
                    "parent":     {"database_id": REPLY_RATE_DB_ID},
                    "properties": props,
                },
            )
            action = "Created"

        reply_rate = round(s["engaged"] / s["initiated"] * 100) if s["initiated"] else 0
        if r.status_code == 200:
            print(f"  {action}: {method:20s} | "
                  f"Initiated: {s['initiated']:3d}  "
                  f"Engaged: {s['engaged']:3d}  "
                  f"Reply Rate: {reply_rate:3d}%")
        else:
            print(f"  ERROR ({method}): {r.status_code} — {r.text[:200]}")

# ── Main ──────────────────────────────────────────────────────
def main():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║   MVS Studios · Method / Reply Rate %    ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    print("  Fetching Outreach entries...", end="", flush=True)
    pages = fetch_all_outreach()
    print(f" {len(pages)} found.")

    print("  Calculating reply rate per method...")
    stats = calculate_stats(pages)

    print("  Fetching existing Reply Rate rows...")
    existing = fetch_existing_rows()

    print("  Writing to Notion...\n")
    upsert_rows(stats, existing)

    print(f"\n  Done. Run this script anytime to refresh the numbers.\n")

if __name__ == "__main__":
    main()
