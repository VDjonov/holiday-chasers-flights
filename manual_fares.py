#!/usr/bin/env python3
"""Turn the fare scout's CSV into the deals_cache.json shape.

The scheduled FlightAPI workflow does not call this. A person runs it, or sets
FARE_SOURCE=manual for one local run of refresh_deals.py. The default scanner
is unchanged.

Input columns (this order), in data/manual_fares.csv:

    origin, destination, out_date, ret_date, nights, trip_type, airline,
    out_flight, out_time, ret_flight, ret_time, out_fare_eur, ret_fare_eur,
    total_pp_eur, source_url, checked_at_utc, matched_shortlist, seats_note,
    screenshot_ref

Prices are the Basic Fare for 1 adult, taxes included, no bags. checked_at_utc
is stored as UTC and a Dublin stamp is added for display. screenshot_ref stays
in the CSV. It is the audit pointer, not a public site field.

Rows whose screenshot_ref starts with EXAMPLE, or whose seats_note contains
the word EXAMPLE, are fixtures. They convert only with --allow-example, and
even then they cannot be written to deals_cache.json.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE_CACHE = os.path.join(HERE, "deals_cache.json")
DEFAULT_CSV = os.path.join(HERE, "data", "manual_fares.csv")
DUBLIN = ZoneInfo("Europe/Dublin")

COLUMNS = [
    "origin",
    "destination",
    "out_date",
    "ret_date",
    "nights",
    "trip_type",
    "airline",
    "out_flight",
    "out_time",
    "ret_flight",
    "ret_time",
    "out_fare_eur",
    "ret_fare_eur",
    "total_pp_eur",
    "source_url",
    "checked_at_utc",
    "matched_shortlist",
    "seats_note",
    "screenshot_ref",
]

ORIGINS = {"ORK": "Cork", "DUB": "Dublin"}
# Named so a Kerry or Shannon row fails with the policy, not a generic code error.
REJECTED_ORIGINS = {"KIR": "Kerry", "SNN": "Shannon"}
REJECTED_DESTINATIONS = {"RAK": "Marrakesh"}

# city, country, airport label shown when the IATA is not the city's main code.
DESTINATIONS = {
    "ALC": ("Alicante", "Spain", ""),
    "BCN": ("Barcelona", "Spain", ""),
    "AGP": ("Malaga", "Spain", ""),
    "PMI": ("Palma Mallorca", "Spain", ""),
    "MAD": ("Madrid", "Spain", ""),
    "TFS": ("Tenerife", "Spain", ""),
    "ACE": ("Lanzarote", "Spain", ""),
    "FAO": ("Faro", "Portugal", ""),
    "LIS": ("Lisbon", "Portugal", ""),
    "OPO": ("Porto", "Portugal", ""),
    "FCO": ("Rome", "Italy", ""),
    "BGY": ("Milan", "Italy", ""),
    "CDG": ("Paris", "France", ""),
    "BVA": ("Paris", "France", "Beauvais"),
    "NCE": ("Nice", "France", ""),
    "AMS": ("Amsterdam", "Netherlands", ""),
    "BER": ("Berlin", "Germany", ""),
    "MUC": ("Munich", "Germany", ""),
    "BUD": ("Budapest", "Hungary", ""),
    "KRK": ("Krakow", "Poland", ""),
    "WMI": ("Warsaw", "Poland", ""),
    "PRG": ("Prague", "Czech Republic", ""),
    "EDI": ("Edinburgh", "Scotland", ""),
    "STN": ("London", "England", ""),
    "MAN": ("Manchester", "England", ""),
    "GVA": ("Geneva", "Switzerland", ""),
    "MLA": ("Malta", "Malta", ""),
    "VIE": ("Vienna", "Austria", ""),
    "ATH": ("Athens", "Greece", ""),
    "VLC": ("Valencia", "Spain", ""),
    "CPH": ("Copenhagen", "Denmark", ""),
    "SVQ": ("Seville", "Spain", ""),
    "VCE": ("Venice", "Italy", ""),
    "PSA": ("Pisa", "Italy", ""),
    "ZAD": ("Zadar", "Croatia", ""),
    "RHO": ("Rhodes", "Greece", ""),
    "FUE": ("Fuerteventura", "Spain", ""),
    "LPA": ("Las Palmas", "Spain", ""),
    "ZRH": ("Zurich", "Switzerland", ""),
    "BHX": ("Birmingham", "England", ""),
    "BRS": ("Bristol", "England", ""),
    "LPL": ("Liverpool", "England", ""),
    "GLA": ("Glasgow", "Scotland", ""),
    "CRL": ("Brussels", "Belgium", ""),
    "LYS": ("Lyon", "France", ""),
    "ADB": ("Izmir", "Turkey", ""),
}

AIRLINES = {
    "ryanair": ("Ryanair", ("ryanair.com", "www.ryanair.com")),
    "aer lingus": ("Aer Lingus", ("aerlingus.com", "www.aerlingus.com")),
}

STALE_HOURS = int(os.environ.get("MANUAL_FARE_STALE_HOURS", "48"))
HIDE_HOURS = int(os.environ.get("MANUAL_FARE_HIDE_HOURS", "168"))
SUM_TOLERANCE = Decimal("0.50")
MAX_PRICE = Decimal("5000")
FUTURE_SKEW = dt.timedelta(minutes=5)
MIN_KEEP_RATIO = float(os.environ.get("MIN_KEEP_RATIO", "0.5"))
MAX_HORIZON_DAYS = 400

FLIGHT_RE = re.compile(r"^[A-Z]{2,3}\d{1,4}$")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHOT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,179}$")
TRIP_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
BOOLS = {"true": True, "false": False, "yes": True, "no": False, "1": True, "0": False}


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


class SafetyError(Exception):
    pass


def utc_z(when):
    when = when.astimezone(dt.timezone.utc).replace(microsecond=0)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def dublin_stamp(when):
    local = when.astimezone(DUBLIN)
    return f"{local.day} {local.strftime('%b %Y')}, {local.strftime('%H:%M')}"


def money_number(amount):
    quantized = amount.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral_value():
        return int(quantized)
    return float(format(quantized, "f"))


def is_example(row):
    shot = (row.get("screenshot_ref") or "").strip()
    note = row.get("seats_note") or ""
    if shot.upper().startswith("EXAMPLE"):
        return True
    return re.search(r"\bEXAMPLE\b", note) is not None


def parse_money(text):
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    if amount.as_tuple().exponent < -2:
        return None
    return amount


def parse_checked(text):
    raw = text.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return "naive"
    return parsed.astimezone(dt.timezone.utc)


def norm_flight(text):
    return re.sub(r"\s+", "", text.strip().upper())


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = [(name or "").strip() for name in (reader.fieldnames or [])]
        if fields != COLUMNS:
            raise ValidationError([
                "CSV columns must be exactly: " + ", ".join(COLUMNS),
                "Got: " + ", ".join(fields),
            ])
        rows = []
        for line_no, raw in enumerate(reader, start=2):
            row = {key: (raw.get(key) or "").strip() for key in COLUMNS}
            if not any(row.values()):
                continue
            rows.append((line_no, row))
    return rows


def validate_row(line_no, row, now):
    """Return a list of human-readable errors. Empty means the row is usable."""
    errors = []

    def bad(message):
        errors.append(f"line {line_no}: {message}")

    origin = row["origin"].upper()
    if origin in REJECTED_ORIGINS:
        bad(f"{REJECTED_ORIGINS[origin]} ({origin}) is not a Holiday Chasers origin. "
            "Use Cork (ORK) or Dublin (DUB) only.")
    elif origin not in ORIGINS:
        bad("origin must be ORK or DUB")

    dest = row["destination"].upper()
    if dest in REJECTED_DESTINATIONS:
        bad(f"{REJECTED_DESTINATIONS[dest]} ({dest}) is excluded by policy and is not on the site")
    elif not re.fullmatch(r"[A-Z]{3}", dest) or dest not in DESTINATIONS:
        bad(f"destination {dest or '(blank)'} is not a Holiday Chasers airport")
    elif dest == origin:
        bad("destination must differ from origin")

    out_day = ret_day = None
    if not DATE_RE.fullmatch(row["out_date"]):
        bad("out_date must be YYYY-MM-DD")
    else:
        try:
            out_day = dt.date.fromisoformat(row["out_date"])
        except ValueError:
            bad("out_date is not a real date")
    if not DATE_RE.fullmatch(row["ret_date"]):
        bad("ret_date must be YYYY-MM-DD")
    else:
        try:
            ret_day = dt.date.fromisoformat(row["ret_date"])
        except ValueError:
            bad("ret_date is not a real date")

    today = now.astimezone(DUBLIN).date()
    if out_day and ret_day:
        if ret_day < out_day:
            bad("ret_date is before out_date")
        elif out_day < today:
            pass  # departed rows are dropped later, not rejected
        elif (out_day - today).days > MAX_HORIZON_DAYS:
            bad(f"out_date is more than {MAX_HORIZON_DAYS} days ahead")
        nights_span = (ret_day - out_day).days
        if not re.fullmatch(r"[1-9]\d*", row["nights"]):
            bad("nights must be a positive whole number")
        elif int(row["nights"]) != nights_span:
            bad(f"nights is {row['nights']} but the dates span {nights_span}")

    trip = re.sub(r"[\s-]+", "_", row["trip_type"].strip().lower())
    if not TRIP_RE.fullmatch(trip):
        bad("trip_type must be a short slug such as weekend, week or christmas")

    airline_key = row["airline"].strip().lower()
    if airline_key not in AIRLINES:
        bad("airline must be Ryanair or Aer Lingus")

    for field in ("out_flight", "ret_flight"):
        flight = norm_flight(row[field])
        if not FLIGHT_RE.fullmatch(flight):
            bad(f"{field} must look like FR1234 or EI123")
    for field in ("out_time", "ret_time"):
        if not TIME_RE.fullmatch(row[field]):
            bad(f"{field} must be HH:MM in 24-hour time")

    amounts = {}
    for field in ("out_fare_eur", "ret_fare_eur", "total_pp_eur"):
        amount = parse_money(row[field]) if row[field] else None
        if amount is None or amount <= 0 or amount > MAX_PRICE:
            bad(f"{field} must be a price in EUR greater than 0 (dot decimal, no € sign)")
        else:
            amounts[field] = amount
    if len(amounts) == 3:
        gap = abs((amounts["out_fare_eur"] + amounts["ret_fare_eur"]) - amounts["total_pp_eur"])
        if gap > SUM_TOLERANCE:
            bad(f"total_pp_eur differs from the two Basic Fares by €{gap} "
                f"(allowed €{SUM_TOLERANCE})")

    parsed_url = urlparse(row["source_url"])
    host = (parsed_url.hostname or "").lower()
    if parsed_url.scheme != "https" or parsed_url.username or parsed_url.password:
        bad("source_url must be an https URL with no username or password")
    elif airline_key in AIRLINES and host not in AIRLINES[airline_key][1]:
        allowed = " or ".join(AIRLINES[airline_key][1])
        bad(f"source_url host must be {allowed} for {AIRLINES[airline_key][0]}")

    checked = parse_checked(row["checked_at_utc"]) if row["checked_at_utc"] else None
    if checked is None:
        bad("checked_at_utc must be ISO 8601 with a timezone, for example 2026-11-13T18:05:00Z")
    elif checked == "naive":
        bad("checked_at_utc must include a timezone and must not be a future time")
    elif checked > now.astimezone(dt.timezone.utc) + FUTURE_SKEW:
        bad("checked_at_utc is in the future")

    matched = BOOLS.get(row["matched_shortlist"].strip().lower())
    if matched is None:
        bad("matched_shortlist must be true or false")

    if len(row["seats_note"]) > 160:
        bad("seats_note is longer than 160 characters")
    shot = row["screenshot_ref"]
    if not shot:
        bad("screenshot_ref is required so the check can be audited")
    elif ".." in shot or not SHOT_RE.fullmatch(shot):
        bad("screenshot_ref must be a relative id such as checks/2026-11-13/ork-fao.png")

    return errors


def _deal_from(row, now):
    origin = row["origin"].upper()
    dest = row["destination"].upper()
    city, country, airport_label = DESTINATIONS[dest]
    airline_name = AIRLINES[row["airline"].strip().lower()][0]
    checked = parse_checked(row["checked_at_utc"])
    age = now.astimezone(dt.timezone.utc) - checked
    out_day = dt.date.fromisoformat(row["out_date"])
    ret_day = dt.date.fromisoformat(row["ret_date"])
    trip = re.sub(r"[\s-]+", "_", row["trip_type"].strip().lower())
    deal = {
        "city": city,
        "country": country,
        "code": dest,
        "depart_date": out_day.isoformat(),
        "return_date": ret_day.isoformat(),
        "nights": int(row["nights"]),
        "price": money_number(parse_money(row["total_pp_eur"])),
        "stops": 0,
        "total_time": "—",
        "airlines": airline_name,
        "source": "manual",
        "fare_label": "from, no bags",
        "out_fare_eur": money_number(parse_money(row["out_fare_eur"])),
        "ret_fare_eur": money_number(parse_money(row["ret_fare_eur"])),
        "out_flight": norm_flight(row["out_flight"]),
        "out_time": row["out_time"],
        "ret_flight": norm_flight(row["ret_flight"]),
        "ret_time": row["ret_time"],
        "source_url": row["source_url"],
        "checked_at": utc_z(checked),
        "checked_at_dublin": dublin_stamp(checked),
        "matched_shortlist": BOOLS[row["matched_shortlist"].strip().lower()],
        "trip_type": trip,
        "stale": age > dt.timedelta(hours=STALE_HOURS),
        "origin_airport": origin,
    }
    if airport_label:
        deal["airport_label"] = airport_label
    if row["seats_note"] and not is_example(row):
        deal["seats_note"] = row["seats_note"]
    return deal, checked, age, out_day


def convert_rows(rows, now, allow_example=False):
    """rows is a list of (line_no, dict). Returns (payload, report)."""
    now = now.astimezone(dt.timezone.utc)
    errors = []
    examples = []
    for line_no, row in rows:
        errors.extend(validate_row(line_no, row, now))
        if is_example(row):
            examples.append(line_no)
    if examples and not allow_example:
        listed = ", ".join(str(n) for n in examples)
        errors.append(
            f"lines {listed}: EXAMPLE fixtures cannot be published. "
            "Use them only in tests (--allow-example) and never as live prices."
        )
    if errors:
        raise ValidationError(errors)
    if not rows:
        raise ValidationError(["no fare rows"])

    today = now.astimezone(DUBLIN).date()
    kept = {}
    report = {"stale": 0, "hidden_age": 0, "departed": 0, "duplicates": 0, "examples": len(examples)}
    for line_no, row in rows:
        deal, checked, age, out_day = _deal_from(row, now)
        if out_day < today:
            report["departed"] += 1
            continue
        if age > dt.timedelta(hours=HIDE_HOURS):
            report["hidden_age"] += 1
            continue
        if deal["stale"]:
            report["stale"] += 1
        key = (deal["origin_airport"], deal["code"], deal["depart_date"],
               deal["return_date"], deal["airlines"])
        previous = kept.get(key)
        if previous and previous[0] >= checked:
            report["duplicates"] += 1
            continue
        if previous:
            report["duplicates"] += 1
        kept[key] = (checked, deal)

    if not kept:
        raise ValidationError(["no fares left after dropping departed and expired rows"])

    boards = {}
    latest = None
    for checked, deal in kept.values():
        latest = checked if latest is None or checked > latest else latest
        origin = deal["origin_airport"]
        trip = deal["trip_type"]
        slot = "weekend_boards" if trip == "weekend" else "week_boards" if trip == "week" else "special_boards"
        board_key = (origin, slot, deal["depart_date"], deal["return_date"], deal["nights"], trip)
        bucket = boards.setdefault(board_key, [])
        bucket.append(deal)

    airports = {
        "ORK": {"name": "Cork", "weekend_boards": [], "week_boards": [], "special_boards": []},
        "DUB": {"name": "Dublin", "weekend_boards": [], "week_boards": [], "special_boards": []},
    }
    for (origin, slot, depart, ret, nights, trip), deals in sorted(boards.items()):
        deals.sort(key=lambda item: (item["price"], item["code"]))
        out_day = dt.date.fromisoformat(depart)
        ret_day = dt.date.fromisoformat(ret)
        board = {
            "depart_date": depart,
            "return_date": ret,
            "nights": nights,
            "label": f"{out_day.strftime('%a %d %b')} – {ret_day.strftime('%a %d %b')}",
            "deals": deals,
        }
        if slot == "special_boards":
            board["trip_type"] = trip
        airports[origin][slot].append(board)

    for code, airport in airports.items():
        stamps = [
            deal["checked_at"]
            for slot in ("weekend_boards", "week_boards", "special_boards")
            for board in airport[slot]
            for deal in board["deals"]
        ]
        if stamps:
            airport["scanned_utc"] = max(stamps)

    ork = airports["ORK"]
    payload = {
        "updated_utc": utc_z(latest),
        "travellers": 1,
        "passenger_label": "per person (1 adult, return, from, no bags)",
        "fare_source": "manual",
        "fare_label": "from, no bags",
        "checked_timezone": "Europe/Dublin",
        "airports": airports,
        "weekend_boards": ork["weekend_boards"],
        "week_boards": ork["week_boards"],
        "week_board": (ork["week_boards"] or [None])[0],
    }
    report["published"] = count_deals(payload)
    return payload, report


def convert_file(path, now=None, allow_example=False):
    now = now or dt.datetime.now(dt.timezone.utc)
    return convert_rows(read_csv(path), now, allow_example=allow_example)


def count_deals(payload):
    total = 0
    for airport in (payload.get("airports") or {}).values():
        for slot in ("weekend_boards", "week_boards", "special_boards"):
            for board in airport.get(slot) or []:
                total += len(board.get("deals") or [])
    return total


def _existing_deal_count(path):
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return 0
    return count_deals(payload)


def write_payload(payload, out_path, force=False):
    out_abs = os.path.abspath(out_path)
    if out_abs == os.path.abspath(LIVE_CACHE) and os.path.exists(LIVE_CACHE) and not force:
        previous = _existing_deal_count(LIVE_CACHE)
        new_count = count_deals(payload)
        if previous and new_count < previous * MIN_KEEP_RATIO:
            raise SafetyError(
                f"refusing to replace deals_cache.json: {new_count} manual fares "
                f"vs {previous} already published (minimum {int(previous * MIN_KEEP_RATIO)}). "
                "Pass --force, or FORCE_CACHE_WRITE=1, when the smaller board is intentional."
            )
    os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
    with open(out_abs, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return out_abs


def _reject_live_examples(path, out_path, allow_example):
    if not allow_example:
        return
    if os.path.abspath(out_path) != os.path.abspath(LIVE_CACHE):
        return
    for _line, row in read_csv(path):
        if is_example(row):
            raise ValidationError([
                "EXAMPLE rows cannot be written to deals_cache.json. "
                "They are fixtures, not fares for the site."
            ])


def publish_from_env():
    """Used by refresh_deals.py when FARE_SOURCE=manual. Never calls FlightAPI."""
    csv_path = os.environ.get("MANUAL_FARES_CSV", DEFAULT_CSV)
    out_path = os.environ.get("MANUAL_FARES_OUT", LIVE_CACHE)
    force = os.environ.get("FORCE_CACHE_WRITE") == "1"
    try:
        _reject_live_examples(csv_path, out_path, allow_example=False)
        payload, report = convert_file(csv_path, allow_example=False)
        written = write_payload(payload, out_path, force=force)
    except (ValidationError, SafetyError, OSError) as exc:
        print(exc)
        return 1
    print(f"Wrote {written}")
    print(
        f"published={report['published']} stale={report['stale']} "
        f"hidden_age={report['hidden_age']} departed={report['departed']} "
        f"duplicates={report['duplicates']}"
    )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert the scout CSV into deals_cache.json shape.")
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--out", default=LIVE_CACHE)
    parser.add_argument("--publish", action="store_true",
                        help="Required when --out is the live deals_cache.json.")
    parser.add_argument("--force", action="store_true",
                        help="Replace the live cache even if the manual file is much smaller.")
    parser.add_argument("--allow-example", action="store_true",
                        help="Convert EXAMPLE fixture rows. Still refused for deals_cache.json.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the summary. Do not write.")
    args = parser.parse_args(argv)
    live = os.path.abspath(args.out) == os.path.abspath(LIVE_CACHE)
    if live and not args.publish and not args.dry_run:
        print("Refusing to write deals_cache.json without --publish.")
        return 2
    try:
        _reject_live_examples(args.csv, args.out, args.allow_example)
        payload, report = convert_file(args.csv, allow_example=args.allow_example)
    except (ValidationError, OSError) as exc:
        print(exc)
        return 1
    print(
        f"published={report['published']} stale={report['stale']} "
        f"hidden_age={report['hidden_age']} departed={report['departed']} "
        f"duplicates={report['duplicates']} examples={report['examples']}"
    )
    if args.dry_run:
        print("Dry run: no file written.")
        return 0
    try:
        written = write_payload(payload, args.out, force=args.force)
    except SafetyError as exc:
        print(exc)
        return 1
    print(f"Wrote {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
