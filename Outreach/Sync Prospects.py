import urllib.request
import urllib.error
import json
import os

NOTION_TOKEN = "ntn_U60582391564u7rDIIxeSyYXMD7aOqEaawu30A8D3wUag7"

SCREENING_DB_ID  = "28d16919-64b4-8065-b59e-c1f0b293f91f"
OUTREACH_DB_ID   = "28d16919-64b4-80a8-8260-e3871d01824c"

INITIATED_DB_ID  = "35d16919-64b4-8128-afd1-c38f35addd1e"
ENGAGED_DB_ID    = "35d16919-64b4-815b-8609-fc2360f1eba6"
PITCHED_DB_ID    = "35d16919-64b4-8148-ae2b-c3496c8893b0"
CLOSED_DB_ID     = "35d16919-64b4-8148-9a2e-d7a1c9c34011"

STAGE_PAGE_IDS = {
    "Pre-Initiated": "35d16919-64b4-8124-9528-e840cbba1b34",
    "Initiated":     "35e16919-64b4-8045-889d-f66b2c9bc3a0",
    "Engaged":       "35e16919-64b4-800b-bbda-d753173996f9",
    "Pitched":       "35e16919-64b4-8022-ba41-f3c893dff9ff",
    "Closed":        "35e16919-64b4-80ae-a80f-f069f3c8705f",
}

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

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
    prop = row.get("properties", {}).get(prop_name, {})
    date_obj = prop.get("date")
    if date_obj and date_obj.get("start"):
        return date_obj["start"]
    return None

def update_leads(page_id, count):
    notion_request("PATCH", f"/pages/{page_id}", {"properties": {"Leads": {"number": count}}})

def get_source(row):
    prop = row.get("properties", {}).get("Source", {})
    sel = prop.get("select")
    return sel.get("name") if sel else None

def get_row_title(row):
    prop = row.get("properties", {}).get("Source", {})
    parts = prop.get("title", [])
    return parts[0].get("plain_text", "") if parts else ""

def safe_pct(numerator, denominator):
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)

def upsert_funnel_row(db_id, existing_map, source_name, properties):
    if source_name in existing_map:
        notion_request("PATCH", f"/pages/{existing_map[source_name]}", {"properties": properties})
    else:
        notion_request("POST", "/pages", {
            "parent": {"database_id": db_id},
            "properties": {"Source": {"title": [{"text": {"content": source_name}}]}, **properties},
        })

def main():
    print("Fetching Screening database...")
    screening_rows = query_all_rows(SCREENING_DB_ID)
    pre_initiated_count = len(screening_rows)
    print(f"  Pre-Initiated: {pre_initiated_count}")

    print("Fetching Outreach database...")
    outreach_rows = query_all_rows(OUTREACH_DB_ID)
    print(f"  Total: {len(outreach_rows)}")

    initiated_count = engaged_count = pitched_count = closed_count = 0
    for row in outreach_rows:
        d_init = get_date(row, "Date Initiated")
        d_eng  = get_date(row, "Date Engaged")
        d_pit  = get_date(row, "Date Pitched")
        d_clo  = get_date(row, "Date Closed")
        if d_clo:
            closed_count += 1
        elif d_init and d_eng and d_pit and not d_clo:
            pitched_count += 1
        elif d_init and d_eng and not d_pit and not d_clo:
            engaged_count += 1
        elif d_init and not d_eng and not d_pit and not d_clo:
            initiated_count += 1

    update_leads(STAGE_PAGE_IDS["Pre-Initiated"], pre_initiated_count)
    update_leads(STAGE_PAGE_IDS["Initiated"],     initiated_count)
    update_leads(STAGE_PAGE_IDS["Engaged"],       engaged_count)
    update_leads(STAGE_PAGE_IDS["Pitched"],       pitched_count)
    update_leads(STAGE_PAGE_IDS["Closed"],        closed_count)
    print("\nDone! Prospects dashboard is up to date.")

if __name__ == "__main__":
    main()
