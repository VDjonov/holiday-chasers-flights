#!/usr/bin/env python3
"""
Holiday Chasers Cork — FastAPI backend.

Runs on YOUR PC. Handles live flight searches via SerpApi, serves cached deals,
and connects to the public website via Cloudflare Tunnel.

─── SETUP ───
    pip install fastapi uvicorn requests

─── RUN ───
    python backend.py

─── THEN (in a separate terminal) ───
    cloudflared tunnel --url http://localhost:8000
"""

import datetime as dt
import json
import os
import time
import hashlib

import requests as http_req
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
ORIGIN = "ORK"
HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "serpapi_key.txt")
DEALS_FILE = os.path.join(HERE, "deals_cache.json")

# ── Live-search file cache ────────────────────────────────────────────────────
# Stores recent SerpApi results keyed by route+date. Survives backend restarts.
# Cuts SerpApi costs by 30-65% as traffic grows (repeat popular routes are free).
LIVE_CACHE_FILE = os.path.join(HERE, "live_search_cache.json")
LIVE_CACHE_TTL_HOURS = 6   # results older than this trigger a fresh SerpApi call


def _cache_key(origin, dest, outbound_date, return_date):
    """Stable string key for a unique flight query."""
    raw = f"{origin}|{dest}|{outbound_date}|{return_date or ''}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load_live_cache():
    try:
        with open(LIVE_CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_live_cache(cache):
    try:
        with open(LIVE_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _cache_get(key):
    """Return cached result if it exists and is fresher than TTL, else None."""
    cache = _load_live_cache()
    entry = cache.get(key)
    if not entry:
        return None
    age_hours = (time.time() - entry["ts"]) / 3600
    if age_hours > LIVE_CACHE_TTL_HOURS:
        return None          # stale — will be refreshed and overwritten
    return entry["result"]


def _cache_set(key, result):
    """Store a result in the cache with a timestamp."""
    cache = _load_live_cache()
    cache[key] = {"ts": time.time(), "result": result}
    # Evict entries older than 48h to keep the file from growing indefinitely
    cutoff = time.time() - 48 * 3600
    cache = {k: v for k, v in cache.items() if v["ts"] > cutoff}
    _save_live_cache(cache)

app = FastAPI(title="Holiday Chasers Cork API")

# Allow the website (any origin) to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add ngrok browser warning skip header to all responses
@app.middleware("http")
async def add_ngrok_header(request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Key management — multi-key rotation
# ──────────────────────────────────────────────────────────────────────────────
def load_keys():
    keys = []
    # 1) Environment variables
    for name in ["SERPAPI_KEY", "SERPAPI_KEY2", "SERPAPI_KEY3",
                 "SERPAPI_KEY4", "SERPAPI_KEY5"]:
        v = os.environ.get(name, "").strip()
        if v and v not in keys:
            keys.append(v)
    # 2) Local file (one key per line) — MERGED with env vars, not just a fallback.
    #    This means you can keep all your keys in serpapi_key.txt and they'll be
    #    used even if some env vars are also set.
    try:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "r") as f:
                for line in f:
                    k = line.strip()
                    if k and not k.startswith("#") and k not in keys:
                        keys.append(k)
    except Exception:
        pass
    return keys


# ──────────────────────────────────────────────────────────────────────────────
# SerpApi helpers (same logic as the dashboard)
# ──────────────────────────────────────────────────────────────────────────────
def _is_quota_err(msg):
    m = str(msg).lower()
    return any(s in m for s in ["run out", "exceeded", "limit", "quota", "401", "429"])


# Keys found exhausted during this backend session — skipped on later searches
# so live search doesn't keep re-failing dead keys.
_EXHAUSTED = set()


def serpapi_get(params):
    keys = load_keys()
    if not keys:
        raise HTTPException(500, "No SerpApi keys configured on backend")
    live = [k for k in keys if k not in _EXHAUSTED]
    if not live:
        # All known-dead — try them all again in case quota reset
        live = keys
        _EXHAUSTED.clear()
    for idx, key in enumerate(live):
        p = {**params, "api_key": key}
        try:
            r = http_req.get("https://serpapi.com/search.json", params=p, timeout=40)
        except Exception as e:
            continue
        if r.status_code == 200:
            return r.json()
        try:
            err = r.json().get("error", f"HTTP {r.status_code}")
        except Exception:
            err = f"HTTP {r.status_code}"
        if _is_quota_err(err):
            _EXHAUSTED.add(key)
            if idx < len(live) - 1:
                continue
        else:
            raise HTTPException(502, f"SerpApi error: {err}")
    raise HTTPException(502, "All SerpApi keys exhausted")


def fmt_hm(m):
    return f"{m // 60}h {m % 60}m" if m else ""


def parse_itinerary(it):
    legs = it.get("flights", [])
    layovers = it.get("layovers", []) or []
    first = legs[0] if legs else {}
    last = legs[-1] if legs else {}
    airlines = []
    for leg in legs:
        a = leg.get("airline")
        if a and a not in airlines:
            airlines.append(a)
    dep = (first.get("departure_airport", {}) or {}).get("time", "")
    arr = (last.get("arrival_airport", {}) or {}).get("time", "")
    arr_id = (last.get("arrival_airport", {}) or {}).get("id", "")
    via = " → ".join(f"{lo.get('id','?')} ({fmt_hm(lo.get('duration',0))})"
                     for lo in layovers) or "Direct"
    return {
        "price": round(it.get("price", 0)),
        "stops": len(layovers),
        "total_min": it.get("total_duration", 0),
        "total_time": fmt_hm(it.get("total_duration", 0)),
        "airlines": ", ".join(airlines) if airlines else "—",
        "arrival_airport": arr_id,
        "via": via,
        "departure": dep[11:16] if len(dep) >= 16 else dep,
        "arrival": arr[11:16] if len(arr) >= 16 else arr,
    }


# ──────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    cache = _load_live_cache()
    fresh = sum(1 for v in cache.values()
                if (time.time() - v["ts"]) / 3600 < LIVE_CACHE_TTL_HOURS)
    return {"status": "online", "keys": len(load_keys()),
            "cache_entries": len(cache), "cache_fresh": fresh,
            "cache_ttl_hours": LIVE_CACHE_TTL_HOURS,
            "time": dt.datetime.utcnow().isoformat() + "Z"}


@app.get("/api/deals")
def get_deals():
    """Return cached deal boards (always available, no quota cost)."""
    if not os.path.exists(DEALS_FILE):
        return {"boards": {}, "updated_utc": None}
    with open(DEALS_FILE, "r") as f:
        return json.load(f)


class SearchReq(BaseModel):
    dest_code: str
    outbound_date: str
    return_date: str | None = None
    nonstop: bool = False
    departure_override: str | None = None  # if set, use as origin instead of ORK


@app.post("/api/search/direct")
def search_direct(req: SearchReq):
    """Cheapest nonstop flight for one date. Results cached for 6h to cut SerpApi costs."""
    origin = req.departure_override or ORIGIN
    dest   = ORIGIN if req.departure_override else req.dest_code

    # Check cache first — same query within 6h returns instantly, costs nothing
    ck = _cache_key(origin, dest, req.outbound_date, req.return_date)
    cached = _cache_get(ck)
    if cached is not None:
        return cached   # free hit — no SerpApi call

    params = {
        "engine": "google_flights", "departure_id": origin,
        "arrival_id": dest, "outbound_date": req.outbound_date,
        "stops": "1", "currency": "EUR", "hl": "en", "gl": "ie",
    }
    if req.return_date:
        params["type"] = "1"
        params["return_date"] = req.return_date
    else:
        params["type"] = "2"
    data = serpapi_get(params)
    its = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    best = None
    for it in its:
        if not it.get("price"):
            continue
        row = parse_itinerary(it)
        if row["stops"] != 0:
            continue
        if best is None or row["price"] < best["price"]:
            best = row

    # Store result (even if None — no flights on that date is also a valid cached fact)
    _cache_set(ck, best)
    return best


@app.post("/api/search/all")
def search_all(req: SearchReq):
    """All options (direct + connecting) for one date."""
    params = {
        "engine": "google_flights", "departure_id": ORIGIN,
        "arrival_id": req.dest_code, "outbound_date": req.outbound_date,
        "currency": "EUR", "hl": "en", "gl": "ie",
    }
    if req.return_date:
        params["type"] = "1"
        params["return_date"] = req.return_date
    else:
        params["type"] = "2"
    data = serpapi_get(params)
    its = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    rows = [parse_itinerary(it) for it in its if it.get("price")]
    rows.sort(key=lambda r: r["price"])
    return rows[:10]


class ScanReq(BaseModel):
    outbound_date: str
    return_date: str
    destinations: list[dict]  # [{"code":"ALC","city":"Alicante","country":"Spain"}, ...]


@app.post("/api/scan")
def scan_all_destinations(req: ScanReq):
    """Scan multiple destinations — one search each. Returns ranked deals."""
    results = []
    for d in req.destinations:
        params = {
            "engine": "google_flights", "departure_id": ORIGIN,
            "arrival_id": d["code"], "outbound_date": req.outbound_date,
            "return_date": req.return_date, "type": "1",
            "currency": "EUR", "hl": "en", "gl": "ie",
        }
        try:
            data = serpapi_get(params)
        except HTTPException:
            continue
        its = (data.get("best_flights") or []) + (data.get("other_flights") or [])
        best = None
        for it in its:
            if not it.get("price"):
                continue
            row = parse_itinerary(it)
            if best is None or row["price"] < best["price"]:
                best = row
        if best:
            results.append({**d, **best})
        time.sleep(0.3)
    results.sort(key=lambda r: r["price"])
    return results


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"\n  🛫 Holiday Chasers Cork backend starting...")
    print(f"  Keys loaded: {len(load_keys())}")
    print(f"  Deals cache: {'found' if os.path.exists(DEALS_FILE) else 'not found'}")
    print(f"\n  Open http://localhost:8000/api/health to test\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
