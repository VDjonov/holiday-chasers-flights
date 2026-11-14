#!/usr/bin/env python3
"""Merge a fare-scout CSV and rebuild the site from it.

This is the daily update. It does not call FlightAPI and it does not read
FLIGHTAPI_KEY. A row that fails a price, date, or origin check rejects the
incoming file and nothing is written. An airport with no page is kept in
data/manual_fares.csv, named in the summary, and left off the site.

Usage:
    python scripts/update_manual_fares.py path/to/scout.csv [more.csv ...]

The merge key is origin, destination, out_date, ret_date, and airline.
The row with the newest checked_at_utc is kept. An equal timestamp keeps
the row from the file you just passed.
"""

import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import generate_pages
import manual_fares

CSV_PATH = manual_fares.DEFAULT_CSV
CACHE_PATH = manual_fares.LIVE_CACHE


def _soft_destination(message):
    return (
        "is not a Holiday Chasers airport" in message
        or "has no Holiday Chasers page" in message
        or "excluded until a destination page is approved" in message
    )


def classify_row(line_no, row, now):
    """Return (hard_errors, soft_notes). Soft notes are airports with no page."""
    if manual_fares.is_example(row):
        return [f"line {line_no}: EXAMPLE fixtures cannot be merged as live prices"], []
    hard = []
    soft = []
    for message in manual_fares.validate_row(line_no, row, now):
        if _soft_destination(message):
            soft.append(message)
        else:
            hard.append(message)
    return hard, soft


def _read_rows(path):
    numbered = manual_fares.read_csv(path)
    return [row for _line, row in numbered]


def _check_file(path, now):
    hard = []
    soft = []
    rows = []
    for line_no, row in manual_fares.read_csv(path):
        row_hard, row_soft = classify_row(line_no, row, now)
        hard.extend(row_hard)
        soft.extend(row_soft)
        rows.append(row)
    return rows, hard, soft


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=manual_fares.COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in manual_fares.COLUMNS})


def rows_same(left, right):
    def norm(rows):
        return [
            tuple((row.get(key) or "") for key in manual_fares.COLUMNS)
            for row in sorted(rows, key=manual_fares.fare_key)
        ]
    return norm(left) == norm(right)


def html_has_fare(path):
    if not os.path.exists(path):
        return False
    text = open(path, encoding="utf-8").read()
    return "<tbody>\n<tr" in text


def coverage(cache):
    """Counts a visitor can check against the rebuilt pages."""
    cards = 0
    cities = set()
    boards = boards_with = 0
    for airport in (cache.get("airports") or {}).values():
        for slot in ("weekend_boards", "week_boards"):
            for board in airport.get(slot) or []:
                boards += 1
                deals = board.get("deals") or []
                if deals:
                    boards_with += 1
                cards += len(deals)
                cities.update(deal.get("code") for deal in deals if deal.get("code"))
    dest_with = []
    dest_empty = []
    for code, (slug, _city, _country, _blurb) in generate_pages.CITIES.items():
        path = os.path.join(ROOT, "destinations", f"{slug}.html")
        if html_has_fare(path):
            dest_with.append(slug)
        else:
            dest_empty.append(slug)
    route_with = []
    route_empty = []
    for route in generate_pages.ROUTES:
        path = os.path.join(ROOT, "routes", f"{route['slug']}.html")
        if html_has_fare(path):
            route_with.append(route["slug"])
        else:
            route_empty.append(route["slug"])
    popular_empty = []
    for href, name, label, _note in generate_pages.POPULAR_ROUTES:
        rel = href.lstrip("/")
        if not html_has_fare(os.path.join(ROOT, rel)):
            popular_empty.append(f"{name} ({label})")
    return {
        "homepage_deal_cards": cards,
        "homepage_cities": len(cities),
        "homepage_boards_with_a_fare": boards_with,
        "homepage_boards": boards,
        "destinations_with_a_fare": len(dest_with),
        "destinations": len(generate_pages.CITIES),
        "destinations_empty": dest_empty,
        "route_pages_with_a_fare": len(route_with),
        "route_pages": len(generate_pages.ROUTES),
        "route_pages_empty": route_empty,
        "popular_empty": popular_empty,
    }


def print_coverage(summary):
    print(
        "coverage "
        f"destinations={summary['destinations_with_a_fare']}/{summary['destinations']} "
        f"routes={summary['route_pages_with_a_fare']}/{summary['route_pages']} "
        f"homepage_deal_cards={summary['homepage_deal_cards']} "
        f"homepage_cities={summary['homepage_cities']} "
        f"homepage_boards={summary['homepage_boards_with_a_fare']}/{summary['homepage_boards']}"
    )
    if summary["destinations_empty"]:
        print("destinations without a fare: " + ", ".join(summary["destinations_empty"]))
    if summary["route_pages_empty"]:
        print("route pages without a fare: " + ", ".join(summary["route_pages_empty"]))
    if summary["popular_empty"]:
        print("popular pages without a fare: " + "; ".join(summary["popular_empty"]))


def regenerate():
    """FARE_SOURCE=manual. FlightAPI and SerpApi keys are removed from the child."""
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("FLIGHTAPI", "SERPAPI", "DATAFORSEO")):
            env.pop(key, None)
    env["FARE_SOURCE"] = "manual"
    env["FORCE_CACHE_WRITE"] = "1"
    steps = [
        [sys.executable, os.path.join(ROOT, "refresh_deals.py")],
        [sys.executable, os.path.join(ROOT, "generate_pages.py")],
    ]
    for command in steps:
        completed = subprocess.run(command, cwd=ROOT, env=env)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 2 if not argv else 0
    now = dt.datetime.now(dt.timezone.utc)
    incoming = []
    soft_notes = []
    hard = []
    for path in argv:
        rows, file_hard, file_soft = _check_file(path, now)
        if file_hard:
            hard.append(path)
            for message in file_hard:
                print(f"{path}: {message}")
        else:
            incoming.extend(rows)
            soft_notes.extend(f"{path}: {message}" for message in file_soft)
    if hard:
        print("Refusing to merge. The CSV on disk was not changed.")
        return 1
    if not os.path.exists(CSV_PATH):
        print(f"Missing {CSV_PATH}")
        return 1
    existing, existing_hard, existing_soft = _check_file(CSV_PATH, now)
    if existing_hard:
        print("The committed CSV has a row that cannot be published:")
        for message in existing_hard:
            print(message)
        return 1
    soft_notes.extend(existing_soft)
    merged, stats = manual_fares.merge_fare_rows(existing, incoming)
    if rows_same(existing, merged):
        print(
            f"manual_fares.csv unchanged "
            f"(added={stats['added']} replaced={stats['replaced']} "
            f"kept_older={stats['kept_existing']} total={stats['total']})"
        )
    else:
        write_csv(CSV_PATH, merged)
        print(
            f"Wrote {CSV_PATH} "
            f"(added={stats['added']} replaced={stats['replaced']} "
            f"kept_older={stats['kept_existing']} total={stats['total']})"
        )
    unpublished = set()
    for note in soft_notes:
        match = re.search(
            r"destination ([A-Z]{3}) is not a Holiday Chasers airport"
            r"|([A-Z]{3}) has no Holiday Chasers page",
            note,
        )
        if match:
            unpublished.add(match.group(1) or match.group(2))
    for code in sorted(unpublished):
        print(f"not published, no page: {code}")
    code = regenerate()
    if code != 0:
        return code
    cache = json.load(open(CACHE_PATH, encoding="utf-8"))
    if cache.get("fare_source") != "manual":
        print("deals_cache.json was not written from the manual file.")
        return 1
    print_coverage(coverage(cache))
    return 0


if __name__ == "__main__":
    sys.exit(main())
