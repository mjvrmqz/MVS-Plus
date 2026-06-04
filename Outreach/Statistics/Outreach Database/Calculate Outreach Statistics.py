import urllib.request
import urllib.error
import json
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
NOTION_KEY = os.environ.get("NOTION_KEY", "")

SCREENING_DB_ID  = os.environ.get("SCREENING_DB_ID", "")
OUTREACH_DB_ID   = os.environ.get("OUTREACH_DB_ID", "")

# Funnel breakdown databases (Initiated → Engaged → Pitched → Closed)
INITIATED_DB_ID  = "35d16919-64b4-8128-afd1-c38f35addd1e"
ENGAGED_DB_ID    = "35d16919-64b4-815b-8609-fc2360f1eba6"
PITCHED_DB_ID    = "35d16919-64b4-8148-ae2b-c3496c8893b0"
CLOSED_DB_ID     = "35d16919-64b4-8148-9a2e-d7a1c9c34011"

# Prospects stage row page IDs
STAGE_PAGE_IDS = {
    "Pre-Initiated": "35d16919-64b4-8124-9528-e840cbba1b34",
    "Initiated":     "35e16919-64b4-8045-889d-f66b2c9bc3a0",
    "Engaged":       "35e16919-64b4-800b-bbda-d753173996f9",
    "Pitched":       "35e16919-64b4-8022-ba41-f3c893dff9ff",
    "Closed":        "35e16919-64b4-80ae-a80f-f069f3c8705f",
}

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def notion_request(method, path, body=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}: {e.read().decode()}")
        raise

def query_all_rows(database_id):
    """Fetches all rows from a Notion database, handling pagination."""
    rows = []
    body = {"page_size": 100}
    while True:
        result = notion_request("POST", f"/databases/{database_id}/query", body)
        rows.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        body["start_cursor"] = result["next_cursor"]
    return rows

def get_date(row, prop_name):
    """Returns the date string for a date property, or None if empty."""
    prop = row.get("properties", {}).get(prop_name, {})
    date_obj = prop.get("date")
    if date_obj and date_obj.get("start"):
        return date_obj["start"]
    return None

def update_leads(page_id, count):
    """Writes a number to the Leads property of a Prospects stage row."""
    notion_request("PATCH", f"/pages/{page_id}", {
        "properties": {
            "Leads": {"number": count}
        }
    })

def get_source(row):
    """Returns the Source select value for an Outreach row, or None."""
    prop = row.get("properties", {}).get("Source", {})
    sel = prop.get("select")
    return sel.get("name") if sel else None

def get_row_title(row):
    """Returns the title (Source) of a funnel DB row."""
    prop = row.get("properties", {}).get("Source", {})
    parts = prop.get("title", [])
    return parts[0].get("plain_text", "") if parts else ""

def safe_pct(numerator, denominator):
    """Returns percentage rounded to 2 dp, or 0.0 if denominator is zero."""
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)

def upsert_funnel_row(db_id, existing_map, source_name, properties):
    """Updates the row for source_name if it exists, otherwise creates it."""
    if source_name in existing_map:
        notion_request("PATCH", f"/pages/{existing_map[source_name]}",
                       {"properties": properties})
    else:
        notion_request("POST", "/pages", {
            "parent": {"database_id": db_id},
            "properties": {
                "Source": {"title": [{"text": {"content": source_name}}]},
                **properties,
            },
        })

# ── FUNNEL DATABASES ─────────────────────────────────────────────────────────
def sync_funnel_databases(outreach_rows):
    """
    Reads all Outreach rows and writes per-source breakdowns into the
    Initiated, Engaged, Pitched, and Closed funnel databases.

    Each stage counts a lead if its corresponding date field is filled in,
    regardless of other stages (cumulative, not exclusive):
      Initiated  → Date Initiated set
      Engaged    → Date Engaged set
      Pitched    → Date Pitched set
      Closed     → Date Closed set

    Conversion rates:
      Initiated  : Close Rate %  = Closed / Initiated
      Engaged    : A > B Conv. % = Engaged / Initiated
      Pitched    : B > C Conv. % = Pitched / Engaged
      Closed     : C > D Conv. % = Closed  / Pitched
    """
    from collections import defaultdict

    # ── 1. Tally counts per source for every stage ────────────────────────────
    initiated = defaultdict(int)
    engaged   = defaultdict(int)
    pitched   = defaultdict(int)
    closed    = defaultdict(int)

    for row in outreach_rows:
        source = get_source(row) or "Other"
        if get_date(row, "Date Initiated"):
            initiated[source] += 1
        if get_date(row, "Date Engaged"):
            engaged[source] += 1
        if get_date(row, "Date Pitched"):
            pitched[source] += 1
        if get_date(row, "Date Closed"):
            closed[source] += 1

    # All sources that appear in any stage
    all_sources = sorted(
        set(initiated) | set(engaged) | set(pitched) | set(closed)
    )

    # Grand totals
    total_init    = sum(initiated.values())
    total_engaged = sum(engaged.values())
    total_pitched = sum(pitched.values())
    total_closed  = sum(closed.values())

    # ── 2. Initiated DB ───────────────────────────────────────────────────────
    print("\nSyncing Initiated database...")
    existing = {get_row_title(r): r["id"] for r in query_all_rows(INITIATED_DB_ID)}

    for source in all_sources:
        i = initiated.get(source, 0)
        c = closed.get(source, 0)
        upsert_funnel_row(INITIATED_DB_ID, existing, source, {
            "Initiated Leads": {"number": i},
            "Close Rate %":    {"number": safe_pct(c, i)},
        })
        print(f"  {source}: {i} leads, {safe_pct(c, i)}% close rate")

    upsert_funnel_row(INITIATED_DB_ID, existing, "TOTAL", {
        "Initiated Leads": {"number": total_init},
        "Close Rate %":    {"number": safe_pct(total_closed, total_init)},
    })
    print(f"  TOTAL: {total_init} leads, {safe_pct(total_closed, total_init)}% close rate")

    # ── 3. Engaged DB ─────────────────────────────────────────────────────────
    print("\nSyncing Engaged database...")
    existing = {get_row_title(r): r["id"] for r in query_all_rows(ENGAGED_DB_ID)}

    for source in all_sources:
        i = initiated.get(source, 0)
        e = engaged.get(source, 0)
        upsert_funnel_row(ENGAGED_DB_ID, existing, source, {
            "Engaged Leads":  {"number": e},
            "A > B Conv. %": {"number": safe_pct(e, i)},
        })
        print(f"  {source}: {e} leads, {safe_pct(e, i)}% A>B")

    upsert_funnel_row(ENGAGED_DB_ID, existing, "TOTAL", {
        "Engaged Leads":  {"number": total_engaged},
        "A > B Conv. %": {"number": safe_pct(total_engaged, total_init)},
    })
    print(f"  TOTAL: {total_engaged} leads, {safe_pct(total_engaged, total_init)}% A>B")

    # ── 4. Pitched DB ─────────────────────────────────────────────────────────
    print("\nSyncing Pitched database...")
    existing = {get_row_title(r): r["id"] for r in query_all_rows(PITCHED_DB_ID)}

    for source in all_sources:
        e = engaged.get(source, 0)
        p = pitched.get(source, 0)
        # Note: property is named "Engaged Leads" in this DB but holds pitched count
        upsert_funnel_row(PITCHED_DB_ID, existing, source, {
            "Engaged Leads":  {"number": p},
            "B > C Conv. %": {"number": safe_pct(p, e)},
        })
        print(f"  {source}: {p} leads, {safe_pct(p, e)}% B>C")

    upsert_funnel_row(PITCHED_DB_ID, existing, "TOTAL", {
        "Engaged Leads":  {"number": total_pitched},
        "B > C Conv. %": {"number": safe_pct(total_pitched, total_engaged)},
    })
    print(f"  TOTAL: {total_pitched} leads, {safe_pct(total_pitched, total_engaged)}% B>C")

    # ── 5. Closed DB ──────────────────────────────────────────────────────────
    print("\nSyncing Closed database...")
    existing = {get_row_title(r): r["id"] for r in query_all_rows(CLOSED_DB_ID)}

    for source in all_sources:
        p = pitched.get(source, 0)
        c = closed.get(source, 0)
        # Note: property is named "Engaged Leads" in this DB but holds closed count
        upsert_funnel_row(CLOSED_DB_ID, existing, source, {
            "Engaged Leads":  {"number": c},
            "C > D Conv. %": {"number": safe_pct(c, p)},
        })
        print(f"  {source}: {c} leads, {safe_pct(c, p)}% C>D")

    upsert_funnel_row(CLOSED_DB_ID, existing, "TOTAL", {
        "Engaged Leads":  {"number": total_closed},
        "C > D Conv. %": {"number": safe_pct(total_closed, total_pitched)},
    })
    print(f"  TOTAL: {total_closed} leads, {safe_pct(total_closed, total_pitched)}% C>D")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("Fetching Screening database...")
    screening_rows = query_all_rows(SCREENING_DB_ID)
    pre_initiated_count = len(screening_rows)
    print(f"  Pre-Initiated (Screening rows): {pre_initiated_count}")

    print("Fetching Outreach database...")
    outreach_rows = query_all_rows(OUTREACH_DB_ID)
    print(f"  Total Outreach rows fetched: {len(outreach_rows)}")

    initiated_count = 0
    engaged_count   = 0
    pitched_count   = 0
    closed_count    = 0

    for row in outreach_rows:
        date_initiated = get_date(row, "Date Initiated")
        date_engaged   = get_date(row, "Date Engaged")
        date_pitched   = get_date(row, "Date Pitched")
        date_closed    = get_date(row, "Date Closed")

        # Closed: Date Closed is filled
        if date_closed:
            closed_count += 1

        # Pitched: Date Initiated + Engaged + Pitched filled, Date Closed empty
        elif date_initiated and date_engaged and date_pitched and not date_closed:
            pitched_count += 1

        # Engaged: Date Initiated + Engaged filled, Pitched + Closed empty
        elif date_initiated and date_engaged and not date_pitched and not date_closed:
            engaged_count += 1

        # Initiated: only Date Initiated filled, rest empty
        elif date_initiated and not date_engaged and not date_pitched and not date_closed:
            initiated_count += 1

    print(f"  Initiated: {initiated_count}")
    print(f"  Engaged:   {engaged_count}")
    print(f"  Pitched:   {pitched_count}")
    print(f"  Closed:    {closed_count}")

    print("\nWriting counts back to Notion Prospects database...")
    update_leads(STAGE_PAGE_IDS["Pre-Initiated"], pre_initiated_count)
    print(f"  ✓ Pre-Initiated → {pre_initiated_count}")
    update_leads(STAGE_PAGE_IDS["Initiated"], initiated_count)
    print(f"  ✓ Initiated     → {initiated_count}")
    update_leads(STAGE_PAGE_IDS["Engaged"], engaged_count)
    print(f"  ✓ Engaged       → {engaged_count}")
    update_leads(STAGE_PAGE_IDS["Pitched"], pitched_count)
    print(f"  ✓ Pitched       → {pitched_count}")
    update_leads(STAGE_PAGE_IDS["Closed"], closed_count)
    print(f"  ✓ Closed        → {closed_count}")

    print("\nDone! Prospects dashboard is up to date.")

    sync_funnel_databases(outreach_rows)
    print("\nAll funnel databases are up to date.")

if __name__ == "__main__":
    main()
