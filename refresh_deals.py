"""
Holiday Chasers Ireland — deal-board scanner (v3, FlightAPI edition)
====================================================================
ARCHITECTURE
  * Data source : FlightAPI.io /roundtrip — REAL bookable return fares.
                  Accuracy verified against Ryanair.com (within ~€2).
  * Pricing     : PER-PERSON (1 adult). The site multiplies by group size
                  at display time. No traveller math in the scanner —
                  the old ÷4 bug class is structurally impossible.
  * Boards      : 8 weekends (Fri→Sun) + 8 weeks (Sat→Sat, 7 nights),
                  starting the week AFTER the run date, rolling forward.
  * Airports    : Cork (ORK) + Dublin (DUB), separate boards each.
  * Fallback    : SerpApi (also 1 adult) only if FlightAPI errors mid-run.
  * Cadence     : every 5 days (workflow cron) — 9,984 credits/month,
                  fits the Basic plan (10,000).

SECRETS (GitHub → Settings → Secrets → Actions)
  FLIGHTAPI_KEY   — required (flightapi.io dashboard)
  SERPAPI_KEY..5  — optional fallback
"""

import datetime as dt
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import requests

# ── Config ───────────────────────────────────────────────────────────────────
FLIGHTAPI_KEY = os.environ.get("FLIGHTAPI_KEY", "").strip()

DELAY = 1.6          # seconds between FlightAPI calls (be kind to rate limits)
RETRIES = 1          # one retry on transient errors

NUM_WEEKENDS = 8
WEEKEND_NIGHTS = 2   # Fri → Sun
NUM_WEEKS = 10       # weeks booked further ahead than weekends → longer horizon
WEEK_NIGHTS = 7      # Sat → Sat

AIRPORTS = [
    {"code": "ORK", "name": "Cork"},
    {"code": "DUB", "name": "Dublin"},
]

# Single IATA code per destination (FlightAPI takes one airport per query).
# Multi-airport cities use the code most relevant to the Irish market.
# 4th field = airports that operate the route NON-STOP (route map: flightsfrom.com,
# July 2026). Cork-only-via-connection cities are skipped for ORK — keeps the
# "direct flights" promise honest and saves ~430 credits per scan.
DESTINATIONS = [
    ("ALC", "Alicante",   "Spain", ("ORK", "DUB")),
    ("BCN", "Barcelona",  "Spain", ("ORK", "DUB")),
    ("AGP", "Malaga",     "Spain", ("ORK", "DUB")),
    ("PMI", "Palma",      "Spain (Mallorca)", ("ORK", "DUB")),
    ("MAD", "Madrid",     "Spain", ("DUB",)),
    ("TFS", "Tenerife",   "Spain", ("ORK", "DUB")),
    ("ACE", "Lanzarote",  "Spain", ("ORK", "DUB")),
    ("FAO", "Faro",       "Portugal", ("ORK", "DUB")),
    ("LIS", "Lisbon",     "Portugal", ("DUB",)),
    ("OPO", "Porto",      "Portugal", ("DUB",)),
    ("FCO", "Rome",       "Italy", ("DUB",)),
    ("BGY", "Milan",      "Italy", ("ORK", "DUB")),
    ("CDG", "Paris",      "France", ("ORK", "DUB")),
    ("NCE", "Nice",       "France", ("ORK", "DUB")),
    ("AMS", "Amsterdam",  "Netherlands", ("ORK", "DUB")),
    ("BER", "Berlin",     "Germany", ("DUB",)),
    ("MUC", "Munich",     "Germany", ("ORK", "DUB")),
    ("BUD", "Budapest",   "Hungary", ("DUB",)),
    ("KRK", "Krakow",     "Poland", ("DUB",)),
    ("WAW", "Warsaw",     "Poland", ("DUB",)),
    ("PRG", "Prague",     "Czech Republic", ("ORK", "DUB")),
    ("EDI", "Edinburgh",  "Scotland", ("ORK", "DUB")),
    ("STN", "London",     "England", ("ORK", "DUB")),
    ("MAN", "Manchester", "England", ("ORK", "DUB")),
    ("GVA", "Geneva",     "Switzerland", ("ORK", "DUB")),
    ("MLA", "Malta",      "Malta", ("DUB",)),
    ("VIE", "Vienna",     "Austria", ("DUB",)),
    ("ATH", "Athens",     "Greece", ("DUB",)),
    ("VLC", "Valencia",   "Spain", ("ORK", "DUB")),
    ("CPH", "Copenhagen", "Denmark", ("DUB",)),
    ("SVQ", "Seville",    "Spain", ("ORK", "DUB")),
    ("VCE", "Venice",     "Italy", ("ORK", "DUB")),
    ("PSA", "Pisa",       "Italy", ("ORK", "DUB")),
    ("ZAD", "Zadar",      "Croatia", ("ORK", "DUB")),
    ("RHO", "Rhodes",     "Greece", ("ORK", "DUB")),
    ("FUE", "Fuerteventura", "Spain", ("ORK", "DUB")),
    ("LPA", "Las Palmas", "Spain", ("ORK", "DUB")),
    ("ZRH", "Zurich",     "Switzerland", ("ORK", "DUB")),
]

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(HERE, "deals_cache.json")
HISTORY_FILE = os.path.join(HERE, "price_history.json")
MAX_HISTORY = 12
MIN_HISTORY_POINTS = 2
CHEAPER_THRESHOLD = 0.85

# Set True the moment FlightAPI says the quota is gone — stops wasting calls.
FLIGHTAPI_DOWN = False


# ── Dates: boards start the week AFTER the run date ─────────────────────────
def next_monday(today=None):
    today = today or dt.date.today()
    days = (7 - today.weekday()) % 7 or 7
    return today + dt.timedelta(days=days)


def first_weekday_on_or_after(start, weekday):
    d = start
    while d.weekday() != weekday:
        d += dt.timedelta(days=1)
    return d


def weekend_starts(count):
    first_fri = first_weekday_on_or_after(next_monday(), 4)   # Friday
    return [first_fri + dt.timedelta(weeks=i) for i in range(count)]


def week_starts(count):
    first_sat = first_weekday_on_or_after(next_monday(), 5)   # Saturday
    return [first_sat + dt.timedelta(weeks=i) for i in range(count)]


# ── FlightAPI.io — primary source ────────────────────────────────────────────
def flightapi_cheapest(origin, dest_code, out_date, ret_date):
    """Cheapest REAL return fare, per person (1 adult), EUR.
    Returns deal dict or None. Sets FLIGHTAPI_DOWN on quota exhaustion."""
    global FLIGHTAPI_DOWN
    if FLIGHTAPI_DOWN or not FLIGHTAPI_KEY:
        return None
    url = (f"https://api.flightapi.io/roundtrip/{FLIGHTAPI_KEY}/{origin}/"
           f"{dest_code}/{out_date}/{ret_date}/1/0/0/Economy/EUR")
    for attempt in range(RETRIES + 1):
        try:
            r = requests.get(url, timeout=90)
        except Exception as e:
            if attempt < RETRIES:
                time.sleep(3); continue
            print(f"    (network error: {e})")
            return None
        if r.status_code == 200:
            break
        if r.status_code == 403:
            print("    ⚠ FlightAPI quota exhausted — switching to fallback for the rest of this run")
            FLIGHTAPI_DOWN = True
            return None
        if r.status_code == 404:
            return None                      # no fares for this route/date
        if r.status_code == 429 and attempt < RETRIES:
            time.sleep(8); continue          # rate limited — brief pause, retry
        if attempt < RETRIES and r.status_code >= 500:
            time.sleep(3); continue
        print(f"    (HTTP {r.status_code})")
        return None
    try:
        data = r.json()
    except Exception:
        return None

    itineraries = data.get("itineraries") or []
    legs = {l.get("id"): l for l in (data.get("legs") or [])}
    carriers = {}
    for c in (data.get("carriers") or []):
        carriers[c.get("id", c.get("code"))] = c.get("name", "")

    best = None
    for it in itineraries:
        # price: pricing_options[0].price.amount | cheapest_price | price
        amt = None
        po = it.get("pricing_options") or []
        if po:
            amt = (po[0].get("price") or {}).get("amount")
        if amt is None:
            cp = it.get("cheapest_price")
            if isinstance(cp, dict):
                amt = cp.get("amount")
            elif isinstance(cp, (int, float)):
                amt = cp
        if amt is None:
            continue
        amt = float(amt)
        if best is not None and amt >= best["price"]:
            continue
        airline, stops, dur = "", None, None
        lids = it.get("leg_ids") or []
        if lids and lids[0] in legs:
            leg = legs[lids[0]]
            mc = leg.get("marketing_carrier_ids") or []
            if mc:
                airline = carriers.get(mc[0], "")
            stops = leg.get("stop_count")
            dur = leg.get("duration")
        best = {
            "price": round(amt),             # PER PERSON, return, EUR
            "stops": stops if stops is not None else 0,
            "total_time": f"{dur//60}h {dur%60:02d}m" if dur else "—",
            "airlines": airline or "—",
            "source": "flightapi",
        }
    return best


# ── SerpApi — emergency fallback (also per-person: 1 adult) ─────────────────
SERP_KEYS = [v for v in (os.environ.get(k, "").strip() for k in
             ["SERPAPI_KEY", "SERPAPI_KEY2", "SERPAPI_KEY3",
              "SERPAPI_KEY4", "SERPAPI_KEY5"]) if v]
EXHAUSTED = set()


def serpapi_cheapest(origin, dest_code, out_date, ret_date):
    for key in SERP_KEYS:
        if key in EXHAUSTED:
            continue
        params = {"engine": "google_flights", "departure_id": origin,
                  "arrival_id": dest_code, "outbound_date": out_date,
                  "return_date": ret_date, "type": "1", "adults": "1",
                  "currency": "EUR", "hl": "en", "gl": "ie", "api_key": key}
        try:
            r = requests.get("https://serpapi.com/search.json",
                             params=params, timeout=40)
        except Exception:
            continue
        if r.status_code != 200:
            try:
                err = r.json().get("error", "")
            except Exception:
                err = ""
            if "run out" in err.lower() or "limit" in err.lower():
                EXHAUSTED.add(key)
                continue
            return None
        data = r.json()
        its = (data.get("best_flights") or []) + (data.get("other_flights") or [])
        best = None
        for it in its:
            p = it.get("price")
            if not p:
                continue
            if best is None or p < best["price"]:
                fl = it.get("flights", [{}])
                best = {
                    "price": round(p),
                    "stops": max(len(fl) - 1, 0),
                    "total_time": "—",
                    "airlines": fl[0].get("airline", "—") if fl else "—",
                    "source": "serpapi",
                }
        return best
    return None


def cheapest_return(origin, dest_code, out_date, ret_date):
    res = flightapi_cheapest(origin, dest_code, out_date, ret_date)
    if res:
        return res
    if FLIGHTAPI_DOWN and SERP_KEYS:
        return serpapi_cheapest(origin, dest_code, out_date, ret_date)
    return None


# ── Price history (per airport + board type) ─────────────────────────────────
def load_history():
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
    s = sorted(vals); n = len(s)
    if n == 0:
        return None
    m = n // 2
    return s[m] if n % 2 else (s[m-1] + s[m]) / 2


def annotate_with_history(boards, hkey, hist):
    for board in boards:
        for d in board["deals"]:
            prior = hist.get(d["code"], {}).get(hkey, [])
            typical = _median(prior) if len(prior) >= MIN_HISTORY_POINTS else None
            d["hist_typical"] = round(typical) if typical else None
            d["is_new"] = len(prior) == 0
            d["is_cheaper"] = bool(typical and d["price"] <= typical * CHEAPER_THRESHOLD)


def record_history(boards, hkey, hist):
    cheapest = {}
    for board in boards:
        for d in board["deals"]:
            c = cheapest.get(d["code"])
            if c is None or d["price"] < c:
                cheapest[d["code"]] = d["price"]
    for code, price in cheapest.items():
        hist.setdefault(code, {}).setdefault(hkey, [])
        hist[code][hkey].append(price)
        hist[code][hkey] = hist[code][hkey][-MAX_HISTORY:]


# ── Board building ───────────────────────────────────────────────────────────
def build_board(origin, label, out_date, ret_date, nights):
    print(f"\n=== [{origin}] {label} · out {out_date} · back {ret_date} ({nights}n) ===")
    deals = []
    for i, (code, city, country, airports) in enumerate(DESTINATIONS, 1):
        if origin not in airports:
            print(f"  [{i:>2}/{len(DESTINATIONS)}] {city:<12} (no direct route from {origin} — skipped)")
            continue
        res = cheapest_return(origin, code, out_date, ret_date)
        if res:
            deals.append({"city": city, "country": country, "code": code, **res})
            src = "" if res["source"] == "flightapi" else f" [{res['source']}]"
            print(f"  [{i:>2}/{len(DESTINATIONS)}] {city:<12} €{res['price']:<5} "
                  f"{res['airlines']:<16}{src}")
        else:
            print(f"  [{i:>2}/{len(DESTINATIONS)}] {city:<12} —")
        time.sleep(DELAY)
    deals.sort(key=lambda d: d["price"])
    return {"depart_date": out_date, "return_date": ret_date,
            "nights": nights, "deals": deals}


def main():
    if not FLIGHTAPI_KEY:
        print("ERROR: FLIGHTAPI_KEY secret not set.")
        sys.exit(1)
    print("Holiday Chasers scanner — FlightAPI edition")
    print(f"Prices: PER PERSON (1 adult), real return fares, EUR")
    print(f"Boards: {NUM_WEEKENDS} weekends + {NUM_WEEKS} weeks, "
          f"starting week of {next_monday()}")
    print(f"Fallback SerpApi keys available: {len(SERP_KEYS)}")

    hist = load_history()
    airport_data = {}

    for ap in AIRPORTS:
        origin, name = ap["code"], ap["name"]
        print(f"\n{'='*60}\nSCANNING {name} ({origin})\n{'='*60}")

        weekend_boards = []
        for fri in weekend_starts(NUM_WEEKENDS):
            sun = fri + dt.timedelta(days=WEEKEND_NIGHTS)
            b = build_board(origin, f"Weekend {fri.strftime('%d %b')}",
                            fri.isoformat(), sun.isoformat(), WEEKEND_NIGHTS)
            b["label"] = f"{fri.strftime('%a %d %b')} – {sun.strftime('%a %d %b')}"
            weekend_boards.append(b)

        week_boards = []
        for sat in week_starts(NUM_WEEKS):
            ret = sat + dt.timedelta(days=WEEK_NIGHTS)
            b = build_board(origin, f"Week {sat.strftime('%d %b')}",
                            sat.isoformat(), ret.isoformat(), WEEK_NIGHTS)
            b["label"] = f"{sat.strftime('%a %d %b')} – {ret.strftime('%a %d %b')}"
            week_boards.append(b)

        annotate_with_history(weekend_boards, f"{origin}_weekend", hist)
        annotate_with_history(week_boards, f"{origin}_week", hist)
        record_history(weekend_boards, f"{origin}_weekend", hist)
        record_history(week_boards, f"{origin}_week", hist)

        airport_data[origin] = {"name": name,
                                "weekend_boards": weekend_boards,
                                "week_boards": week_boards}

    save_history(hist)

    ork = airport_data.get("ORK", {})
    payload = {
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "travellers": 1,                      # per-person storage
        "passenger_label": "per person (1 adult, return)",
        "airports": airport_data,
        # Legacy keys so any old client keeps working
        "weekend_boards": ork.get("weekend_boards", []),
        "week_boards": ork.get("week_boards", []),
        "week_board": (ork.get("week_boards") or [None])[0],
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    total = sum(len(a["weekend_boards"]) + len(a["week_boards"])
                for a in airport_data.values())
    all_deals = [d for a in airport_data.values()
                 for b in a["weekend_boards"] + a["week_boards"]
                 for d in b["deals"]]
    n_fa = sum(1 for d in all_deals if d["source"] == "flightapi")
    n_sp = len(all_deals) - n_fa
    print(f"\nDone. {total} boards, {len(all_deals)} deals "
          f"({n_fa} FlightAPI, {n_sp} SerpApi fallback).")
    for code, a in airport_data.items():
        b = (a["weekend_boards"] or [{}])[0]
        if b.get("deals"):
            d = b["deals"][0]
            print(f"  [{code}] first weekend cheapest: €{d['price']}/pp "
                  f"{d['city']} ({d['airlines']})")
    if FLIGHTAPI_DOWN:
        print("\n⚠ FlightAPI quota ran out during this run — check plan credits.")


if __name__ == "__main__":
    main()
