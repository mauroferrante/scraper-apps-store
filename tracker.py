"""
App Store Ranking Tracker — Multi-app competitor tracking.

Uses the iTunes Search API to find keyword search rankings across
multiple countries for Simply Wall St and key competitors.
Appends results to rankings_history.csv.
"""

import csv
import os
import time
from datetime import datetime, timezone

import requests

# ── Apps to track ───────────────────────────────────────────────────────────
APPS = [
    {"name": "Simply Wall St", "id": 1075614972, "bundle": "com.simplywallst.app"},
    {"name": "Sharesight", "id": 6695726060, "bundle": "com.sharesight.portfolio"},
    {"name": "Snowball Analytics", "id": 6463484375, "bundle": "com.snowball-analytics.app"},
    {"name": "Seeking Alpha", "id": 552799694, "bundle": "com.seekingalpha.webwrapper"},
    {"name": "Yahoo Finance", "id": 328412701, "bundle": "com.yahoo.finance"},
    {"name": "MarketWatch", "id": 336693422, "bundle": "com.dowjones.MarketWatch"},
]

COUNTRIES = ["US", "AU", "CA", "DE", "GB"]
KEYWORDS = [
    "stock analysis",
    "stock research",
    "stock screener",
    "portfolio tracker",
    "dividend tracker",
]

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rankings_history.csv")
CSV_HEADERS = ["date", "app_name", "country", "keyword", "keyword_rank", "category_rank"]

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
ITUNES_RSS_URL = "https://itunes.apple.com/{country}/rss/topfreeapplications/genre=6015/limit=200/json"


# ── Category ranking (Finance top-free chart) ───────────────────────────────
def get_category_ranks(country: str) -> dict[int, int]:
    """Return {app_id: position} for all tracked apps in the Finance chart."""
    url = ITUNES_RSS_URL.format(country=country.lower())
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        entries = resp.json().get("feed", {}).get("entry", [])
    except (requests.RequestException, ValueError, KeyError) as exc:
        print(f"  [ERROR] Category rank for {country}: {exc}")
        return {}

    tracked_ids = {str(app["id"]) for app in APPS}
    tracked_bundles = {app["bundle"]: app["id"] for app in APPS}
    ranks: dict[int, int] = {}

    for position, entry in enumerate(entries, start=1):
        entry_id = entry.get("id", {}).get("attributes", {}).get("im:id", "")
        entry_bundle = entry.get("id", {}).get("attributes", {}).get("im:bundleId", "")

        if entry_id in tracked_ids:
            ranks[int(entry_id)] = position
        elif entry_bundle in tracked_bundles:
            ranks[tracked_bundles[entry_bundle]] = position

    return ranks


# ── Keyword ranking ─────────────────────────────────────────────────────────
def get_keyword_ranks(keyword: str, country: str) -> dict[int, int]:
    """Search iTunes and return {app_id: position} for all tracked apps found."""
    params = {
        "term": keyword,
        "country": country,
        "media": "software",
        "limit": 200,
    }
    try:
        resp = requests.get(ITUNES_SEARCH_URL, params=params, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", [])
    except (requests.RequestException, ValueError) as exc:
        print(f"  [ERROR] Failed to fetch '{keyword}' for {country}: {exc}")
        return {}

    tracked_ids = {app["id"] for app in APPS}
    tracked_bundles = {app["bundle"]: app["id"] for app in APPS}
    ranks: dict[int, int] = {}

    for position, result in enumerate(results, start=1):
        track_id = result.get("trackId")
        bundle_id = result.get("bundleId", "")

        if track_id in tracked_ids:
            ranks[track_id] = position
        elif bundle_id in tracked_bundles:
            ranks[tracked_bundles[bundle_id]] = position

    return ranks


# ── CSV helpers ─────────────────────────────────────────────────────────────
def ensure_csv_exists() -> None:
    """Create the CSV with headers if it doesn't exist."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def append_rows(rows: list[list]) -> None:
    """Append rows to the CSV file."""
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


# ── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    ensure_csv_exists()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows: list[list] = []

    app_names = [a["name"] for a in APPS]
    print(f"Tracking rankings on {today}")
    print(f"Apps: {', '.join(app_names)}")
    print(f"Countries: {', '.join(COUNTRIES)}")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print("=" * 60)

    for country in COUNTRIES:
        print(f"\n  [{country}]")

        # 1. Fetch Finance category ranks (one call per country for all apps)
        cat_ranks = get_category_ranks(country)
        for app_info in APPS:
            cat_pos = cat_ranks.get(app_info["id"])
            if cat_pos:
                print(f"    {app_info['name']:25s} Finance category -> #{cat_pos}")
        time.sleep(1)

        # 2. Fetch keyword ranks (one call per keyword, finds all apps at once)
        for keyword in KEYWORDS:
            kw_ranks = get_keyword_ranks(keyword, country)

            for app_info in APPS:
                app_id = app_info["id"]
                kw_rank = kw_ranks.get(app_id)
                cat_rank = cat_ranks.get(app_id)

                rank_display = f"#{kw_rank}" if kw_rank else "—"
                print(f"    {app_info['name']:25s} '{keyword}' -> {rank_display}")

                rows.append([today, app_info["name"], country, keyword, kw_rank, cat_rank])

            # Be polite to Apple's API
            time.sleep(1)

    append_rows(rows)
    print(f"\n{'=' * 60}")
    print(f"Done. {len(rows)} rows appended to {CSV_FILE}")


if __name__ == "__main__":
    main()
