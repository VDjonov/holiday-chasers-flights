"""
Merge per-airport scan parts into deals_cache.json + price_history.json.

Usage: python merge_parts.py <dir with part_*.json>

Each part comes from `SCAN_AIRPORTS=<code> PART_OUT=part_<code>.json python refresh_deals.py`.
Resilient by design: an airport whose part is missing (job failed / timed out) or looks
broken (far fewer deals than the live cache) KEEPS its previous data, so one bad scan
never wipes the site or throws away the other airport's fresh fares.
Exit 1 only when nothing at all could be updated.
"""
import glob, json, os, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "deals_cache.json")
HISTORY = os.path.join(HERE, "price_history.json")
MIN_KEEP_RATIO = float(os.environ.get("MIN_KEEP_RATIO", "0.5"))


def n_deals(ap):
    return sum(len(b.get("deals") or []) for b in (ap.get("weekend_boards") or []) + (ap.get("week_boards") or []))


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def main(parts_dir):
    cache = load(CACHE, {})
    hist = load(HISTORY, {})
    airports = dict(cache.get("airports") or {})
    updated, kept = [], []

    for path in sorted(glob.glob(os.path.join(parts_dir, "**", "part_*.json"), recursive=True)):
        part = load(path, None)
        if not part:
            print("unreadable part:", path); continue
        for code, ap in part["airports"].items():
            new, old = n_deals(ap), n_deals(airports.get(code, {}))
            if old and new < old * MIN_KEEP_RATIO:
                print(f"✋ {code}: scan found {new} deals vs {old} live; keeping previous {code} data")
                kept.append(code); continue
            airports[code] = ap
            ap["scanned_utc"] = part["scanned_utc"]
            for city, keys in part["history"].items():
                hist.setdefault(city, {}).update({k: v for k, v in keys.items() if k.startswith(code + "_")})
            updated.append(code)
            print(f"✓ {code}: {new} deals (was {old})")

    if not updated:
        print("Nothing updated — leaving deals_cache.json unchanged.")
        sys.exit(1)

    ork = airports.get("ORK", {})
    payload = {
        "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "travellers": 1,
        "passenger_label": "per person (1 adult, return)",
        "airports": airports,
        "weekend_boards": ork.get("weekend_boards", []),
        "week_boards": ork.get("week_boards", []),
        "week_board": (ork.get("week_boards") or [None])[0],
    }
    json.dump(payload, open(CACHE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(hist, open(HISTORY, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"Merged: updated={updated} kept_old={kept}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
