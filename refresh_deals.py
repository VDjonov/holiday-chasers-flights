#!/usr/bin/env python3
"""
refresh_deals.py — scan all destinations from Cork and save MULTIPLE deal boards:
  • Several upcoming WEEKENDS (2-night Fri->Sun trips)
  • One WEEK board (7 nights, ~3 weeks out)

Visitors pick which weekend from a dropdown — instant, zero quota per visitor.

Reads SerpApi keys from env vars SERPAPI_KEY, SERPAPI_KEY2, SERPAPI_KEY3 (rotation).

Local test:
    set SERPAPI_KEY=your_key
    python refresh_deals.py
"""

import datetime as dt
import json
import os
import sys
import time

import requests

ORIGIN = "ORK"
DELAY = 1.0

# ── Passengers: family of four (2 adults + 2 children aged 5 and 13) ──────────
ADULTS = 2
CHILDREN_AGES = "5,13"   # SerpApi 'children_ages' — comma separated
NUM_TRAVELLERS = 4       # for per-person division on the website

# ── How the boards are built ─────────────────────────────────────────────────
WEEKEND_NIGHTS = 2          # Fri -> Sun
NUM_WEEKENDS = 4            # how many upcoming weekends to offer
EARLIEST_DATE = "2026-08-01"  # don't show weekends before this date (skip July).
                              # Set to "" to always just use the next weekends.
WEEK_DEPART_IN_DAYS = 21
WEEK_NIGHTS = 7
NUM_WEEKS = 4              # how many upcoming week-long trips to offer

DESTINATIONS = [
    ("ALC", "Alicante",   "Spain"),
    ("BCN", "Barcelona",  "Spain"),
    ("AGP", "Malaga",     "Spain"),
    ("PMI", "Palma",      "Spain (Mallorca)"),
    ("MAD", "Madrid",     "Spain"),
    ("TFS,TFN", "Tenerife", "Spain"),
    ("ACE", "Lanzarote",  "Spain"),
    ("FAO", "Faro",       "Portugal"),
    ("LIS", "Lisbon",     "Portugal"),
    ("OPO", "Porto",      "Portugal"),
    ("FCO,CIA", "Rome",   "Italy"),
    ("MXP,LIN,BGY", "Milan", "Italy"),
    ("CDG,ORY,BVA", "Paris", "France"),
    ("NCE", "Nice",       "France"),
    ("AMS,EIN", "Amsterdam", "Netherlands"),
    ("BER", "Berlin",     "Germany"),
    ("MUC", "Munich",     "Germany"),
    ("BUD", "Budapest",   "Hungary"),
    ("KRK", "Krakow",     "Poland"),
    ("WAW,WMI", "Warsaw", "Poland"),
    ("PRG", "Prague",     "Czech Republic"),
    ("EDI", "Edinburgh",  "Scotland"),
    ("LHR,LGW,STN,LTN,LCY,SEN", "London", "England"),
    ("MAN", "Manchester", "England"),
    ("GVA", "Geneva",     "Switzerland"),
    ("MLA", "Malta",      "Malta"),
]

OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deals_cache.json")


def fmt_hm(total_min):
    if not total_min:
        return ""
    return f"{total_min // 60}h {total_min % 60}m"


def upcoming_weekdays(count, weekday, earliest=""):
    """Return the next `count` dates falling on `weekday` (0=Mon..6=Sun),
    not before `earliest` (YYYY-MM-DD) and at least ~7 days out so flights
    are bookable."""
    start = dt.date.today() + dt.timedelta(days=7)
    if earliest:
        try:
            e = dt.date.fromisoformat(earliest)
            if e > start:
                start = e
        except ValueError:
            pass
    d = start
    while d.weekday() != weekday:
        d += dt.timedelta(days=1)
    out = []
    for _ in range(count):
        out.append(d)
        d += dt.timedelta(days=7)
    return out


def upcoming_fridays(count, earliest=""):
    """Return the next `count` Fridays (kept for compatibility)."""
    return upcoming_weekdays(count, 4, earliest)  # 4 = Friday


def _is_quota_error(msg):
    msg = str(msg).lower()
    return any(s in msg for s in ["run out", "ran out", "exceeded", "limit",
                                  "plan", "quota", "401", "429", "unauthorized"])


def load_keys():
    keys = []
    for name in ["SERPAPI_KEY", "SERPAPI_KEY2", "SERPAPI_KEY3",
                 "SERPAPI_KEY4", "SERPAPI_KEY5"]:
        v = os.environ.get(name, "").strip()
        if v:
            keys.append(v)
    return keys


def cheapest_return(keys, dest_code, out_date, ret_date):
    base = {
        "engine": "google_flights", "departure_id": ORIGIN, "arrival_id": dest_code,
        "outbound_date": out_date, "return_date": ret_date, "type": "1",
        "adults": str(ADULTS), "children": "2", "children_ages": CHILDREN_AGES,
        "currency": "EUR", "hl": "en", "gl": "ie",
    }
    data = None
    for idx, key in enumerate(keys):
        params = dict(base); params["api_key"] = key
        try:
            r = requests.get("https://serpapi.com/search.json", params=params, timeout=40)
        except Exception as e:
            print(f"    network error: {e}")
            continue
        if r.status_code == 200:
            data = r.json()
            break
        try:
            err = r.json().get("error", f"HTTP {r.status_code}")
        except Exception:
            err = f"HTTP {r.status_code}"
        if _is_quota_error(err) and idx < len(keys) - 1:
            print(f"    key {idx+1} exhausted, trying next…")
            continue
        else:
            print(f"    API error: {err}")
            return None
    if data is None:
        return None

    itineraries = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    best = None
    for it in itineraries:
        price = it.get("price")
        if not price:
            continue
        legs = it.get("flights", [])
        layovers = it.get("layovers", []) or []
        airlines = []
        for leg in legs:
            a = leg.get("airline")
            if a and a not in airlines:
                airlines.append(a)
        via = " → ".join(f"{lo.get('id','?')} ({fmt_hm(lo.get('duration',0))})"
                         for lo in layovers) or "Direct"
        if best is None or price < best["price"]:
            best = {
                "price": round(price),
                "stops": len(layovers),
                "total_time": fmt_hm(it.get("total_duration", 0)),
                "airlines": ", ".join(airlines) if airlines else "—",
                "via": via,
            }
    return best


def build_board(keys, label, out_date, ret_date, nights):
    print(f"\n=== {label} · out {out_date} · back {ret_date} ({nights} nights) ===")
    deals = []
    for i, (code, city, country) in enumerate(DESTINATIONS, 1):
        print(f"  [{i:>2}/{len(DESTINATIONS)}] {city}, {country} …")
        res = cheapest_return(keys, code, out_date, ret_date)
        if res:
            deals.append({"city": city, "country": country, "code": code.split(",")[0], **res})
            print(f"      €{res['price']} ({res['stops']} stop(s)) {res['airlines']}")
        time.sleep(DELAY)
    deals.sort(key=lambda d: d["price"])
    return {"depart_date": out_date, "return_date": ret_date, "nights": nights, "deals": deals}


def main():
    keys = load_keys()
    if not keys:
        print("ERROR: no SERPAPI_KEY env vars set.")
        sys.exit(1)
    print(f"Loaded {len(keys)} key(s) for rotation.")

    today = dt.date.today()

    # ── Weekend boards: next N Fridays (skipping before EARLIEST_DATE) ──
    weekend_boards = []
    for friday in upcoming_fridays(NUM_WEEKENDS, EARLIEST_DATE):
        sun = friday + dt.timedelta(days=WEEKEND_NIGHTS)
        label = f"Weekend {friday.strftime('%d %b')}"
        board = build_board(keys, label, friday.isoformat(), sun.isoformat(), WEEKEND_NIGHTS)
        board["label"] = f"{friday.strftime('%a %d %b')} – {sun.strftime('%a %d %b')}"
        weekend_boards.append(board)

    # ── Week boards: next N week-long trips starting on a Saturday ──
    week_boards = []
    for sat in upcoming_weekdays(NUM_WEEKS, 5, EARLIEST_DATE):  # 5 = Saturday
        wk_ret = sat + dt.timedelta(days=WEEK_NIGHTS)
        label = f"Week {sat.strftime('%d %b')}"
        board = build_board(keys, label, sat.isoformat(), wk_ret.isoformat(), WEEK_NIGHTS)
        board["label"] = f"{sat.strftime('%a %d %b')} – {wk_ret.strftime('%a %d %b')}"
        week_boards.append(board)

    payload = {
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "travellers": NUM_TRAVELLERS,
        "passenger_label": "2 adults + 2 children (5 & 13)",
        "weekend_boards": weekend_boards,   # list, visitor picks which
        "week_boards": week_boards,         # list, visitor picks which
        "week_board": week_boards[0] if week_boards else None,  # legacy single (back-compat)
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Wrote {len(weekend_boards)} weekend board(s) + {len(week_boards)} week board(s).")
    for b in weekend_boards + week_boards:
        if b["deals"]:
            print(f"  {b['label']}: cheapest €{b['deals'][0]['price']} to {b['deals'][0]['city']}")


if __name__ == "__main__":
    main()
