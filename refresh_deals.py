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
EARLIEST_DATE = "2026-08-24"  # start from the last week of August. With NUM_WEEKENDS=4
                              # this gives: last weekend of Aug + first 3 weekends of Sept.
                              # Set to "" to always just use the next weekends.
WEEK_NIGHTS = 7
NUM_WEEKS = 4              # how many upcoming week-long trips to offer
                          # (Saturdays from EARLIEST_DATE: last week Aug + 3 weeks Sept)

# ── Price history (for the "cheaper than usual" badge) ───────────────────────
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_history.json")
MAX_HISTORY = 12          # keep up to 12 recent runs per destination (~3 months weekly)
MIN_HISTORY_POINTS = 3    # need at least this many past prices before judging "cheaper"
CHEAPER_THRESHOLD = 0.85  # a fare 15%+ below the typical price counts as "cheaper than usual"

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


# Keys discovered to be exhausted/invalid during this run. Once a key fails with
# a quota error, we stop trying it for every remaining search — this avoids
# wasting 2+ failed calls per search on already-dead keys.
EXHAUSTED_KEYS = set()


def load_keys():
    keys = []
    for name in ["SERPAPI_KEY", "SERPAPI_KEY2", "SERPAPI_KEY3",
                 "SERPAPI_KEY4", "SERPAPI_KEY5"]:
        v = os.environ.get(name, "").strip()
        if v:
            keys.append(v)
    return keys


# ── Price history helpers ────────────────────────────────────────────────────
def load_history():
    """Load past prices. Shape: {code: {"weekend": [p,...], "week": [p,...]}}"""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_history(hist):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  (could not write price history: {e})")


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    return s[mid] if n % 2 else (s[mid-1] + s[mid]) / 2


def annotate_with_history(boards, board_type, hist):
    """For each deal, compare its price to the destination's TYPICAL past price
    (median of prior runs) and flag is_cheaper / is_new / hist_typical."""
    for board in boards:
        for d in board["deals"]:
            prior = hist.get(d["code"], {}).get(board_type, [])
            typical = _median(prior) if len(prior) >= MIN_HISTORY_POINTS else None
            d["hist_typical"] = round(typical) if typical else None
            d["is_new"] = len(prior) == 0
            d["is_cheaper"] = bool(typical and d["price"] <= typical * CHEAPER_THRESHOLD)


def record_history(boards, board_type, hist):
    """Record this run's cheapest price per destination (for this board type)."""
    cheapest = {}
    for board in boards:
        for d in board["deals"]:
            c = cheapest.get(d["code"])
            if c is None or d["price"] < c:
                cheapest[d["code"]] = d["price"]
    for code, price in cheapest.items():
        hist.setdefault(code, {}).setdefault(board_type, [])
        hist[code][board_type].append(price)
        hist[code][board_type] = hist[code][board_type][-MAX_HISTORY:]


def cheapest_return(keys, dest_code, out_date, ret_date):
    base = {
        "engine": "google_flights", "departure_id": ORIGIN, "arrival_id": dest_code,
        "outbound_date": out_date, "return_date": ret_date, "type": "1",
        "adults": str(ADULTS), "children": "2", "children_ages": CHILDREN_AGES,
        "currency": "EUR", "hl": "en", "gl": "ie",
    }
    data = None
    live_keys = [(idx, k) for idx, k in enumerate(keys) if k not in EXHAUSTED_KEYS]
    if not live_keys:
        print("    all keys exhausted — skipping")
        return None
    for idx, key in live_keys:
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
        if _is_quota_error(err):
            # Mark this key dead for the rest of the run, then try the next live key
            EXHAUSTED_KEYS.add(key)
            print(f"    key {idx+1} exhausted — will skip it for the rest of this run")
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

    # ── Price history: compare to past, then record this run ──
    hist = load_history()
    annotate_with_history(weekend_boards, "weekend", hist)  # uses PRIOR prices
    annotate_with_history(week_boards, "week", hist)
    record_history(weekend_boards, "weekend", hist)          # then add this run
    record_history(week_boards, "week", hist)
    save_history(hist)

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

    live = len(keys) - len(EXHAUSTED_KEYS)
    print(f"\nKey health: {live} of {len(keys)} key(s) still had quota at the end of this run.")
    if EXHAUSTED_KEYS:
        print(f"  {len(EXHAUSTED_KEYS)} key(s) ran out during the run.")
        if live == 0:
            print("  ⚠ ALL keys are exhausted — some boards may be incomplete. Add more keys or reduce boards.")


if __name__ == "__main__":
    main()
