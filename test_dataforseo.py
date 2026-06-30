"""
DataForSEO Google Flights — coverage test for Cork (ORK) AND Dublin (DUB).

PURPOSE
-------
Before depositing any money, this checks the one thing that matters:
does DataForSEO return flight prices — and Ryanair — for BOTH Cork and Dublin?

It runs on the small FREE trial credit DataForSEO gives new accounts, so you
risk nothing. A handful of searches costs a fraction of a cent.

HOW IT WORKS
------------
DataForSEO's SERP API returns the "Google Flights" feature for a route as
structured JSON. We send a few routes from ORK and DUB and read back the
cheapest fare + airline shown.

CREDENTIALS
-----------
DataForSEO uses a login + password (your account email + API password),
sent as HTTP Basic Auth. Set them as GitHub Secrets:
  DATAFORSEO_LOGIN    = your account email
  DATAFORSEO_PASSWORD = your API password (from the dashboard)
"""

import os
import sys
import json
import base64
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

LOGIN = os.environ.get("DATAFORSEO_LOGIN", "PASTE_LOGIN_HERE")
PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "PASTE_PASSWORD_HERE")

# Routes to test from BOTH airports — cheap Ryanair direct + a couple of others
ROUTES = {
    "ORK": [("STN", "London"), ("AGP", "Malaga"), ("FAO", "Faro"), ("BCN", "Barcelona")],
    "DUB": [("STN", "London"), ("AGP", "Malaga"), ("FAO", "Faro"), ("BCN", "Barcelona")],
}
AIRPORT_NAME = {"ORK": "Cork", "DUB": "Dublin"}

# Probe TWO time horizons to check how far forward the data holds:
#   - "near"  ~6 weeks out (typical browsing window)
#   - "far"   ~16 weeks out (the edge of a 16-week board — what you'd pay extra for)
HORIZONS = {
    "near (~6 wks)":  (42, 45),
    "far  (~16 wks)": (112, 115),
}


def trip_dates(dep_days, ret_days):
    dep = (dt.date.today() + dt.timedelta(days=dep_days)).isoformat()
    ret = (dt.date.today() + dt.timedelta(days=ret_days)).isoformat()
    return dep, ret


def auth_header():
    raw = f"{LOGIN}:{PASSWORD}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode(),
            "Content-Type": "application/json"}


def search(origin, dest, dep, ret):
    """Query Google Flights via DataForSEO SERP API (live mode)."""
    url = "https://api.dataforseo.com/v3/serp/google/flights/live/advanced"
    payload = [{
        "departure_airport_code": origin,
        "arrival_airport_code": dest,
        "departure_date": dep,
        "return_date": ret,
        "adults": 2, "children": 2,
        "currency": "EUR",
        "language_code": "en",
    }]
    try:
        r = requests.post(url, headers=auth_header(), json=payload, timeout=60)
    except Exception as e:
        return {"_error": f"network error: {e}"}
    if r.status_code == 401:
        return {"_error": "401 Unauthorized — check login/password"}
    if r.status_code == 402:
        return {"_error": "402 — out of credit (top up or use trial credit)"}
    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}: {r.text[:160]}"}
    return r.json()


def parse_cheapest(resp):
    """Pull the cheapest fare + airline from a DataForSEO flights response."""
    try:
        items = resp["tasks"][0]["result"][0]["items"]
    except (KeyError, IndexError, TypeError):
        return None
    best = None
    for it in items or []:
        # google_flights items carry price + airline info
        price = it.get("price", {})
        amt = price.get("value") if isinstance(price, dict) else None
        airline = it.get("airline") or it.get("title") or ""
        if amt and (best is None or amt < best["price"]):
            best = {"price": amt, "airline": airline,
                    "type": it.get("type", "")}
    return best


def main():
    if "PASTE_" in LOGIN or "PASTE_" in PASSWORD:
        print("⚠  No credentials. Set GitHub Secrets DATAFORSEO_LOGIN and")
        print("   DATAFORSEO_PASSWORD (or paste into the file for a local run).")
        sys.exit(1)

    print("DataForSEO Google Flights — coverage test for Cork + Dublin")
    print("Probing TWO horizons: ~6 weeks out and ~16 weeks out")
    print("2 adults + 2 children · EUR")
    print("=" * 64)

    # Track results per horizon
    horizon_found = {h: 0 for h in HORIZONS}
    horizon_total = {h: 0 for h in HORIZONS}
    ryanair_seen = {"ORK": False, "DUB": False}

    for hlabel, (dd, rd) in HORIZONS.items():
        dep, ret = trip_dates(dd, rd)
        print(f"\n######## HORIZON: {hlabel}  ({dep} -> {ret}) ########")
        for origin, dests in ROUTES.items():
            print(f"\n=== {AIRPORT_NAME[origin]} ({origin}) ===")
            for code, name in dests:
                horizon_total[hlabel] += 1
                resp = search(origin, code, dep, ret)
                if isinstance(resp, dict) and resp.get("_error"):
                    print(f"  {name:<12} ⚠ {resp['_error']}")
                    continue
                best = parse_cheapest(resp)
                if not best:
                    print(f"  {name:<12} (no flights returned)")
                    continue
                horizon_found[hlabel] += 1
                air = best["airline"] or "?"
                if "ryanair" in air.lower():
                    ryanair_seen[origin] = True
                print(f"  {name:<12} €{best['price']:<6} {air}")

    # ── Verdict ──
    print("\n" + "=" * 64)
    print("VERDICT")
    for h in HORIZONS:
        print(f"  {h:<16}: {horizon_found[h]}/{horizon_total[h]} routes returned flights")
    print(f"  Ryanair from Cork   : {'YES ✓' if ryanair_seen['ORK'] else 'no'}")
    print(f"  Ryanair from Dublin : {'YES ✓' if ryanair_seen['DUB'] else 'no'}")
    print()

    near_label = "near (~6 wks)"
    far_label = "far  (~16 wks)"
    near_ok = horizon_found.get(near_label, 0) >= horizon_total.get(near_label, 1) * 0.6
    far_ok = horizon_found.get(far_label, 0) >= horizon_total.get(far_label, 1) * 0.6
    ryan_ok = ryanair_seen["ORK"] and ryanair_seen["DUB"]

    if horizon_found[near_label] == 0 and horizon_found[far_label] == 0:
        print("  ✗ No flights at all. Check credentials/credit, or fall back to SerpApi.")
    elif near_ok and far_ok and ryan_ok:
        print("  ✓✓ EXCELLENT — good coverage at BOTH 6 and 16 weeks, Ryanair on both")
        print("     airports. The full 16+16 board is justified. Safe to deposit $50.")
    elif near_ok and not far_ok:
        print("  ~ Good NEAR-term coverage, but the ~16-week data is thin. Honest")
        print("    takeaway: a 16-week board would have gaps far out. Consider 8+8")
        print("    (≈2 months ahead) where coverage is solid — cheaper AND fuller.")
    elif near_ok:
        print("  ✓ Decent coverage. Ryanair flag uncertain — eyeball the prices above")
        print("    vs Google Flights, then decide.")
    else:
        print("  ~ Coverage thinner than hoped. Compare with SerpApi before committing.")
    print()
    print("  Reminder: this ran on free trial credit — you've spent ~€0.")


if __name__ == "__main__":
    main()
