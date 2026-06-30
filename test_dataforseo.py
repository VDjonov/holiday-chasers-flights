"""
DataForSEO — coverage test for Cork (ORK) AND Dublin (DUB) flights.

IMPORTANT CORRECTION
---------------------
DataForSEO does NOT have a dedicated "flights" endpoint. Flight prices appear
as a "flights" FEATURE embedded inside a normal Google Organic search result
(the same flight widget you see if you type "flights from Cork to Barcelona"
into google.com). So we call the regular organic SERP endpoint with a
flight-search keyword, then look for the embedded flights widget in the
response and read the price/airline text out of it.

PURPOSE
-------
Before depositing any money, this checks the one thing that matters:
does DataForSEO surface flight prices — and Ryanair — for BOTH Cork and Dublin?

It runs on the small FREE trial credit DataForSEO gives new accounts, so you
risk nothing. A handful of searches costs a fraction of a cent.

CREDENTIALS
-----------
DataForSEO uses a login + password (your account email + API password),
sent as HTTP Basic Auth. Set them as GitHub Secrets:
  DATAFORSEO_LOGIN    = your account email
  DATAFORSEO_PASSWORD = your API password (from app.dataforseo.com/api-access)
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

# Full city/airport names for the search keyword (Google needs a real query,
# not just airport codes) — e.g. "flights from Cork to London Stansted"
ROUTES = {
    "ORK": [("STN", "London"), ("AGP", "Malaga"), ("FAO", "Faro"), ("BCN", "Barcelona")],
    "DUB": [("STN", "London"), ("AGP", "Malaga"), ("FAO", "Faro"), ("BCN", "Barcelona")],
}
ORIGIN_NAME = {"ORK": "Cork", "DUB": "Dublin"}

# Probe TWO time horizons to check how far forward the data holds
HORIZONS = {
    "near (~6 wks)":  42,
    "far  (~16 wks)": 112,
}

LOCATION_CODE = 2372   # Ireland (DataForSEO location_code for Google search)
LANGUAGE_CODE = "en"


def trip_date(days_ahead):
    return (dt.date.today() + dt.timedelta(days=days_ahead)).isoformat()


def auth_header():
    raw = f"{LOGIN}:{PASSWORD}".encode()
    return {"Authorization": "Basic " + base64.b64encode(raw).decode(),
            "Content-Type": "application/json"}


def search(keyword, debug=False):
    """Query Google (organic, advanced) for a flight-search keyword and look
    for the embedded 'flights' SERP feature in the results."""
    url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"
    payload = [{
        "keyword": keyword,
        "location_code": LOCATION_CODE,
        "language_code": LANGUAGE_CODE,
        "device": "desktop",
    }]
    try:
        r = requests.post(url, headers=auth_header(), json=payload, timeout=60)
    except Exception as e:
        return {"_error": f"network error: {e}"}
    if debug:
        print(f"    [debug] HTTP status: {r.status_code}")
        print(f"    [debug] raw body (first 2000 chars):\n{r.text[:2000]}")
    if r.status_code == 401:
        return {"_error": "401 Unauthorized — check login/password"}
    if r.status_code == 402:
        return {"_error": "402 — out of credit (top up or use trial credit)"}
    if r.status_code != 200:
        return {"_error": f"HTTP {r.status_code}: {r.text[:160]}"}
    data = r.json()
    if debug:
        try:
            task = data["tasks"][0]
            print(f"    [debug] task status_code: {task.get('status_code')} "
                  f"status_message: {task.get('status_message')}")
            items = task.get("result", [{}])[0].get("items", []) if task.get("result") else []
            types_seen = sorted(set(it.get("type", "?") for it in items))
            print(f"    [debug] item types in this SERP: {types_seen}")
        except Exception as e:
            print(f"    [debug] could not inspect task: {e}")
    return data


def find_flights_widget(resp):
    """Find the 'flights' feature item in the organic SERP results, if present."""
    try:
        items = resp["tasks"][0]["result"][0]["items"]
    except (KeyError, IndexError, TypeError):
        return None
    for it in items or []:
        if it.get("type") == "flights":
            return it
    return None


def parse_cheapest(flights_item):
    """Pull cheapest price + airline text out of the flights widget item."""
    if not flights_item:
        return None
    # The flights widget typically nests results under 'items' or 'flights'
    candidates = flights_item.get("items") or flights_item.get("flights") or []
    best = None
    for f in candidates:
        # Fields vary; try the common ones DataForSEO uses for this widget
        price = f.get("price")
        title = f.get("title") or f.get("airline_name") or f.get("description") or ""
        if isinstance(price, dict):
            price = price.get("value") or price.get("current")
        if isinstance(price, str):
            digits = "".join(c for c in price if c.isdigit())
            price = int(digits) if digits else None
        if price and (best is None or price < best["price"]):
            best = {"price": price, "title": title}
    if best:
        return best
    # Fallback: sometimes the widget itself just has a single price/title pair
    price = flights_item.get("price")
    if price:
        return {"price": price, "title": flights_item.get("title", "")}
    return None


def main():
    if "PASTE_" in LOGIN or "PASTE_" in PASSWORD:
        print("⚠  No credentials. Set GitHub Secrets DATAFORSEO_LOGIN and")
        print("   DATAFORSEO_PASSWORD (or paste into the file for a local run).")
        sys.exit(1)

    print("DataForSEO — coverage test for Cork + Dublin flights")
    print("(via the 'flights' widget embedded in Google Organic results)")
    print("Probing TWO horizons: ~6 weeks out and ~16 weeks out")
    print("=" * 64)

    horizon_found = {h: 0 for h in HORIZONS}
    horizon_total = {h: 0 for h in HORIZONS}
    ryanair_seen = {"ORK": False, "DUB": False}
    debug_done = False

    for hlabel, days_ahead in HORIZONS.items():
        dep = trip_date(days_ahead)
        print(f"\n######## HORIZON: {hlabel}  (around {dep}) ########")
        for origin, dests in ROUTES.items():
            print(f"\n=== {ORIGIN_NAME[origin]} ({origin}) ===")
            for code, name in dests:
                horizon_total[hlabel] += 1
                keyword = f"flights from {ORIGIN_NAME[origin]} to {name} {dep}"
                resp = search(keyword, debug=not debug_done)
                debug_done = True
                if isinstance(resp, dict) and resp.get("_error"):
                    print(f"  {name:<12} ⚠ {resp['_error']}")
                    continue
                widget = find_flights_widget(resp)
                best = parse_cheapest(widget)
                if not best:
                    print(f"  {name:<12} (no flights widget found)")
                    continue
                horizon_found[hlabel] += 1
                title = best["title"] or "?"
                if "ryanair" in title.lower():
                    ryanair_seen[origin] = True
                print(f"  {name:<12} €{best['price']:<6} {title}")

    # ── Verdict ──
    print("\n" + "=" * 64)
    print("VERDICT")
    for h in HORIZONS:
        print(f"  {h:<16}: {horizon_found[h]}/{horizon_total[h]} routes returned a flights widget")
    print(f"  Ryanair from Cork   : {'YES ✓' if ryanair_seen['ORK'] else 'no'}")
    print(f"  Ryanair from Dublin : {'YES ✓' if ryanair_seen['DUB'] else 'no'}")
    print()

    near_label = "near (~6 wks)"
    far_label = "far  (~16 wks)"
    near_ok = horizon_found.get(near_label, 0) >= horizon_total.get(near_label, 1) * 0.6
    far_ok = horizon_found.get(far_label, 0) >= horizon_total.get(far_label, 1) * 0.6
    ryan_ok = ryanair_seen["ORK"] and ryanair_seen["DUB"]

    if horizon_found[near_label] == 0 and horizon_found[far_label] == 0:
        print("  ✗ No flights widgets found at all. Either:")
        print("    - the flights feature isn't appearing in this market/location, or")
        print("    - the response shape still doesn't match what we're parsing.")
        print("    Check the [debug] item types list above — if 'flights' isn't in")
        print("    that list, Google simply isn't showing the widget for this query.")
        print("    Fall back to SerpApi if so.")
    elif near_ok and far_ok and ryan_ok:
        print("  ✓✓ EXCELLENT — good coverage at BOTH 6 and 16 weeks, Ryanair on both")
        print("     airports. The full 16+16 board is justified. Safe to deposit $50.")
    elif near_ok and not far_ok:
        print("  ~ Good NEAR-term coverage, but the ~16-week data is thin. Consider")
        print("    8+8 (≈2 months ahead) where coverage is solid instead.")
    elif near_ok:
        print("  ✓ Decent coverage. Ryanair flag uncertain — eyeball the prices above.")
    else:
        print("  ~ Coverage thinner than hoped. Compare with SerpApi before committing.")
    print()
    print("  Reminder: this ran on free trial credit — you've spent ~€0.")


if __name__ == "__main__":
    main()
