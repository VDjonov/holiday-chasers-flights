"""
FlightAPI.io — coverage & accuracy test for Cork (ORK) AND Dublin (DUB).

PURPOSE
-------
Before paying for any plan, this checks the two things that matter:
  1. COVERAGE  — does FlightAPI return results for Cork and Dublin routes,
                 including Ryanair, at both near (~6wk) and far (~16wk) horizons?
  2. ACCURACY  — are the prices real bookable RETURN fares (per person)?
                 Compare a couple of results by hand against Ryanair.com.

It runs on the FREE plan (100 requests / 30 days) — this test uses 16 requests.

API FORMAT (from official docs, docs.flightapi.io)
---------------------------------------------------
GET https://api.flightapi.io/roundtrip/<key>/<from>/<to>/<dep>/<ret>/<adults>/<children>/<infants>/<cabin>/<currency>
Cost: 2 credits per request. Free plan returns 429 if rate exceeded.

We test with 1 ADULT — matching the per-person storage architecture the
production scanner will use (store per-person, multiply by group at display).

CREDENTIALS
-----------
Set a GitHub Secret:  FLIGHTAPI_KEY  = your API key from flightapi.io dashboard
"""

import os
import sys
import json
import time
import datetime as dt

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

try:
    import requests
except ImportError:
    print("Installing requests…")
    os.system("pip install requests")
    import requests

API_KEY = os.environ.get("FLIGHTAPI_KEY", "PASTE_KEY_HERE")

ROUTES = {
    "ORK": [("STN", "London Stansted"), ("AGP", "Malaga"),
            ("FAO", "Faro"), ("BCN", "Barcelona")],
    "DUB": [("STN", "London Stansted"), ("AGP", "Malaga"),
            ("FAO", "Faro"), ("BCN", "Barcelona")],
}
ORIGIN_NAME = {"ORK": "Cork", "DUB": "Dublin"}

# Two horizons: typical browsing window vs far edge of an 8-week board
HORIZONS = {
    "near (~6 wks)":  (42, 44),    # Fri-ish out, 2 nights
    "far (~16 wks)":  (112, 114),
}

DELAY_BETWEEN_CALLS = 3  # be gentle with free-plan rate limits


def trip_dates(dep_days, ret_days):
    dep = (dt.date.today() + dt.timedelta(days=dep_days)).isoformat()
    ret = (dt.date.today() + dt.timedelta(days=ret_days)).isoformat()
    return dep, ret


def search(origin, dest, dep, ret, debug=False):
    """One round-trip search, 1 adult, EUR. Returns parsed JSON or {_error}."""
    url = (f"https://api.flightapi.io/roundtrip/{API_KEY}/{origin}/{dest}/"
           f"{dep}/{ret}/1/0/0/Economy/EUR")
    try:
        r = requests.get(url, timeout=90)
    except Exception as e:
        return {"_error": f"network error: {e}"}
    if debug:
        print(f"    [debug] HTTP {r.status_code}")
    if r.status_code == 429:
        return {"_error": "429 rate/limit — free plan exhausted or too fast"}
    if r.status_code == 401:
        return {"_error": "401 — bad API key"}
    if r.status_code == 404:
        return {"_error": "404 — no data for this route/date"}
    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}: {r.text[:140]}"}
    try:
        data = r.json()
    except Exception:
        return {"_error": f"non-JSON response: {r.text[:140]}"}
    if debug:
        print(f"    [debug] top-level keys: {sorted(data.keys())}")
        its = data.get("itineraries") or []
        if its:
            print(f"    [debug] {len(its)} itineraries; first itinerary keys: "
                  f"{sorted(its[0].keys())}")
            print(f"    [debug] first itinerary (1200 chars):\n"
                  f"{json.dumps(its[0], indent=2)[:1200]}")
        legs = data.get("legs") or []
        if legs:
            print(f"    [debug] first leg keys: {sorted(legs[0].keys())}")
    return data


def parse_cheapest(data):
    """Cheapest itinerary: price + airline name + whether a deeplink exists.
    FlightAPI uses a Skyscanner-style referenced schema; field names can vary
    slightly, so we try the known shapes and fall back defensively."""
    if not data or "_error" in data:
        return None
    its = data.get("itineraries") or []
    legs = {l.get("id"): l for l in (data.get("legs") or [])}
    carriers = {}
    for c in (data.get("carriers") or []):
        cid = c.get("id", c.get("code"))
        carriers[cid] = c.get("name", "")

    def itin_price(it):
        # Known shapes: pricing_options[0].price.amount  |  price.amount | price
        po = it.get("pricing_options") or it.get("pricingOptions") or []
        if po:
            p = po[0].get("price", {})
            amt = p.get("amount")
            if amt is not None:
                return float(amt), po[0]
        p = it.get("price")
        if isinstance(p, dict) and p.get("amount") is not None:
            return float(p["amount"]), {}
        if isinstance(p, (int, float)):
            return float(p), {}
        return None, {}

    best = None
    for it in its:
        amt, po = itin_price(it)
        if amt is None:
            continue
        if best is None or amt < best["price"]:
            # Resolve airline from the outbound leg's marketing carrier
            leg_ids = it.get("leg_ids") or it.get("legIds") or []
            airline = ""
            stops = None
            if leg_ids and leg_ids[0] in legs:
                leg = legs[leg_ids[0]]
                mc = (leg.get("marketing_carrier_ids")
                      or leg.get("marketingCarrierIds") or [])
                if mc:
                    airline = carriers.get(mc[0], "")
                stops = leg.get("stop_count", leg.get("stopCount"))
            has_link = bool(po.get("url") or it.get("deepLink") or it.get("deeplink"))
            best = {"price": amt, "airline": airline,
                    "stops": stops, "deeplink": has_link}
    return best


def main():
    if "PASTE_" in API_KEY:
        print("⚠  No API key. Set GitHub Secret FLIGHTAPI_KEY "
              "(from your flightapi.io dashboard).")
        sys.exit(1)

    print("FlightAPI.io — coverage & accuracy test, Cork + Dublin")
    print("1 adult · return trips · EUR  (per-person architecture)")
    print("Uses 16 of your 100 free requests.")
    print("=" * 64)

    horizon_found = {h: 0 for h in HORIZONS}
    horizon_total = {h: 0 for h in HORIZONS}
    ryanair_seen = {"ORK": False, "DUB": False}
    deeplinks_seen = 0
    debug_done = False

    for hlabel, (dd, rr) in HORIZONS.items():
        dep, ret = trip_dates(dd, rr)
        print(f"\n######## HORIZON: {hlabel}  ({dep} → {ret}) ########")
        for origin, dests in ROUTES.items():
            print(f"\n=== {ORIGIN_NAME[origin]} ({origin}) ===")
            for code, name in dests:
                horizon_total[hlabel] += 1
                is_first = not debug_done
                data = search(origin, code, dep, ret, debug=is_first)
                debug_done = True
                if isinstance(data, dict) and data.get("_error"):
                    print(f"  {name:<16} ⚠ {data['_error']}")
                    time.sleep(DELAY_BETWEEN_CALLS)
                    continue
                best = parse_cheapest(data)
                if not best:
                    print(f"  {name:<16} (no priced itineraries returned)")
                    time.sleep(DELAY_BETWEEN_CALLS)
                    continue
                horizon_found[hlabel] += 1
                if "ryanair" in (best["airline"] or "").lower():
                    ryanair_seen[origin] = True
                if best["deeplink"]:
                    deeplinks_seen += 1
                stops_s = ("direct" if best["stops"] == 0
                           else f"{best['stops']} stop(s)" if best["stops"] is not None
                           else "?")
                print(f"  {name:<16} €{best['price']:<8.0f} "
                      f"{best['airline'] or '?':<14} {stops_s}")
                time.sleep(DELAY_BETWEEN_CALLS)

    # ── Verdict ──
    print("\n" + "=" * 64)
    print("VERDICT")
    for h in HORIZONS:
        print(f"  {h:<15}: {horizon_found[h]}/{horizon_total[h]} routes returned priced fares")
    print(f"  Ryanair from Cork   : {'YES ✓' if ryanair_seen['ORK'] else 'no'}")
    print(f"  Ryanair from Dublin : {'YES ✓' if ryanair_seen['DUB'] else 'no'}")
    print(f"  Booking deeplinks   : {deeplinks_seen} results had one")
    print()

    near = "near (~6 wks)"; far = "far (~16 wks)"
    near_ok = horizon_found[near] >= horizon_total[near] * 0.6
    far_ok = horizon_found[far] >= horizon_total[far] * 0.6
    ryan_ok = ryanair_seen["ORK"] and ryanair_seen["DUB"]

    if horizon_found[near] == 0 and horizon_found[far] == 0:
        print("  ✗ Nothing returned. Check the API key, or the [debug] output")
        print("    above for the real response shape — the parser may need a tweak.")
    elif near_ok and far_ok and ryan_ok:
        print("  ✓✓ EXCELLENT — coverage at both horizons and Ryanair on both")
        print("     airports. ACCURACY CHECK: pick 2 prices above and compare them")
        print("     on Ryanair.com for the same dates, 1 adult, return. If they're")
        print("     within a few euro, FlightAPI is your accurate source at $49/mo.")
    elif near_ok:
        print("  ✓ Good near-term coverage; far horizon thinner. Compare 2 prices")
        print("    against Ryanair.com — if accurate, still viable (8-week boards fit).")
    else:
        print("  ~ Coverage thinner than hoped. Compare with SerpApi before paying.")

    print()
    print(f"  Requests used this run: ~16 of your free 100.")


if __name__ == "__main__":
    main()
