"""
App Store Ranking Tracker for Simply Wall St (ID: 1075614972).

Uses the iTunes Search API to find keyword search rankings across
multiple countries. Appends results to rankings_history.csv.
"""

import csv
import os
import time
from datetime import datetime, timezone

import requests

APP_ID = 1075614972
APP_BUNDLE_ID = "com.simplywallst.app"

COUNTRIES = ["US", "AU", "CA", "DE", "IN"]
KEYWORDS = ["stock analysis", "investing", "dividend tracker"]

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rankings_history.csv")
CSV_HEADERS = ["date", "country", "keyword", "keyword_rank", "category_rank"]

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def get_keyword_rank(keyword: str, country: str) -> int | None:
    """Search iTunes for a keyword and return the app's position (1-indexed), or None if not found."""
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
        return None

    for position, app in enumerate(results, start=1):
        if app.get("trackId") == APP_ID or app.get("bundleId") == APP_BUNDLE_ID:
            return position

    return None


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


def main() -> None:
    ensure_csv_exists()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = []

    print(f"Tracking rankings for Simply Wall St on {today}")
    print(f"Countries: {', '.join(COUNTRIES)}")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print("-" * 50)

    for country in COUNTRIES:
        for keyword in KEYWORDS:
            rank = get_keyword_rank(keyword, country)
            rank_display = rank if rank is not None else "Not in top 200"
            print(f"  {country} | '{keyword}' -> {rank_display}")

            rows.append([today, country, keyword, rank, "N/A"])

            # Be polite to Apple's API
            time.sleep(1)

    append_rows(rows)
    print(f"\nDone. {len(rows)} rows appended to {CSV_FILE}")


if __name__ == "__main__":
    main()
