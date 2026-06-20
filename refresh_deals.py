#!/usr/bin/env python3
"""
refresh_deals.py — scan all destinations from Cork and save TWO deal boards:
  • Weekend board  (depart next suitable Friday, 2 nights)
  • Week board      (depart ~3 weeks out, 7 nights)

Meant to run on a SCHEDULE (GitHub Actions), NOT per visitor. Writes
deals_cache.json, which the dashboard reads and shows to everyone instantly —
so visitor traffic costs ZERO SerpApi quota.

Reads the SerpApi key from the SERPAPI_KEY environment variable.

Local test:
    set SERPAPI_KEY=your_key        (Windows)
    export SERPAPI_KEY=your_key     (Mac/Linux)
    python refresh_deals.py
"""

import datetime as dt
import json
import os
import sys
import time

import requests

ORIGIN = "ORK"
DELAY = 1.0  # seconds between requests

# Boards to build: (label, depart-offset-days, nights). Weekend uses next Friday.
WEEKEND_NIGHTS = 2
WEEK_DEPART_IN_DAYS = 21
WEEK_NIGHTS = 7

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


def next_friday(min_days_out=10):
    """Next Friday that is at least `min_days_out` days from today."""
    d = dt.date.today() + dt.timedelta(days=min_days_out)
    while d.weekday() != 4:  # 4 = Friday
        d += dt.timedelta(days=1)
    return d


def _is_quota_error(msg):
    msg = str(msg).lower()
    return any(s in msg for s in ["run out", "ran out", "exceeded", "limit",
                                  "plan", "quota", "401", "429", "unauthorized"])


def load_keys():
    """All SerpApi keys from env vars SERPAPI_KEY, SERPAPI_KEY2 … (rotation)."""
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
    print(f"\n=== {label} board · out {out_date} · back {ret_date} ({nights} nights) ===")
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
        print("ERROR: no SERPAPI_KEY (or SERPAPI_KEY2/3) environment variables set.")
        sys.exit(1)
    print(f"Loaded {len(keys)} key(s) for rotation.")

    today = dt.date.today()

    # Weekend board: next Friday, 2 nights (Fri -> Sun)
    we_out = next_friday(min_days_out=10)
    we_ret = we_out + dt.timedelta(days=WEEKEND_NIGHTS)

    # Week board: ~3 weeks out, 7 nights
    wk_out = today + dt.timedelta(days=WEEK_DEPART_IN_DAYS)
    wk_ret = wk_out + dt.timedelta(days=WEEK_NIGHTS)

    boards = {
        "weekend": build_board(keys, "Weekend", we_out.isoformat(),
                               we_ret.isoformat(), WEEKEND_NIGHTS),
        "week": build_board(keys, "Week", wk_out.isoformat(),
                            wk_ret.isoformat(), WEEK_NIGHTS),
    }

    payload = {
        "updated_utc": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "boards": boards,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Wrote 2 boards to {os.path.basename(OUT_FILE)}")
    for key, b in boards.items():
        if b["deals"]:
            print(f"  {key}: cheapest €{b['deals'][0]['price']} to {b['deals'][0]['city']}")


if __name__ == "__main__":
    main()
