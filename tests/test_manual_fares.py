"""Converter tests for the fare-scout CSV. No network. No live prices.

The EXAMPLE fixture is the only price file, and these tests refuse to leave it
in deals_cache.json.
"""

import csv
import datetime as dt
import json
import os
import pathlib
import re
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("requests", types.ModuleType("requests"))

import generate_pages
import manual_fares
import refresh_deals

NOW = dt.datetime(2026, 11, 14, 12, 0, tzinfo=dt.timezone.utc)
EXAMPLE = ROOT / "data" / "manual_fares.example.csv"
LIVE = pathlib.Path(manual_fares.LIVE_CACHE)

BASE = {
    "origin": "ORK",
    "destination": "FAO",
    "out_date": "2026-12-04",
    "ret_date": "2026-12-06",
    "nights": "2",
    "trip_type": "weekend",
    "airline": "Ryanair",
    "out_flight": "FR9991",
    "out_time": "06:40",
    "ret_flight": "FR9992",
    "ret_time": "21:15",
    "out_fare_eur": "100.01",
    "ret_fare_eur": "11.10",
    "total_pp_eur": "111.11",
    "source_url": "https://www.ryanair.com/ie/en/trip/flights/select?fixture=1",
    "checked_at_utc": "2026-11-13T18:05:00Z",
    "matched_shortlist": "true",
    "seats_note": "",
    "screenshot_ref": "checks/2026-11-13/ork-fao.png",
}


def write_csv(rows, directory):
    path = pathlib.Path(directory) / "fares.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=manual_fares.COLUMNS)
        writer.writeheader()
        for row in rows:
            full = dict(BASE)
            full.update(row)
            writer.writerow(full)
    return path


class ManualFareTests(unittest.TestCase):
    def setUp(self):
        self.cache_before = LIVE.read_bytes()

    def tearDown(self):
        if LIVE.exists() and LIVE.read_bytes() != self.cache_before:
            LIVE.write_bytes(self.cache_before)
            raise AssertionError("deals_cache.json was modified by a test")

    def convert(self, rows, now=NOW, allow_example=False):
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv(rows, directory)
            return manual_fares.convert_file(path, now=now, allow_example=allow_example)

    def errors(self, rows, now=NOW):
        try:
            self.convert(rows, now=now)
        except manual_fares.ValidationError as exc:
            return exc.errors
        self.fail("expected a validation error")

    def test_schema_columns_match_the_scout_file(self):
        schema = json.loads((ROOT / "data" / "manual_fares.schema.json").read_text())
        self.assertEqual(schema["required"], manual_fares.COLUMNS)
        self.assertEqual(list(schema["properties"]), manual_fares.COLUMNS)
        self.assertFalse(schema["additionalProperties"])
        header = (ROOT / "data" / "manual_fares.csv").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(header, ",".join(manual_fares.COLUMNS))

    def test_example_fixture_converts_only_when_asked(self):
        with self.assertRaises(manual_fares.ValidationError) as caught:
            manual_fares.convert_file(EXAMPLE, now=NOW, allow_example=False)
        self.assertIn("EXAMPLE", str(caught.exception))

        payload, report = manual_fares.convert_file(EXAMPLE, now=NOW, allow_example=True)
        self.assertEqual(report["published"], 5)
        self.assertEqual(report["examples"], 5)
        self.assertEqual(payload["fare_source"], "manual")
        self.assertEqual(payload["fare_label"], "from, no bags")
        self.assertEqual(payload["travellers"], 1)
        encoded = json.dumps(payload)
        self.assertNotIn("screenshot_ref", encoded)
        self.assertNotIn("EXAMPLE/", encoded)
        self.assertNotIn("not a real fare", encoded)

        ork_weekend = payload["airports"]["ORK"]["weekend_boards"]
        codes = {deal["code"] for board in ork_weekend for deal in board["deals"]}
        self.assertEqual(codes, {"FAO", "BVA"})
        faro = next(deal for board in ork_weekend for deal in board["deals"] if deal["code"] == "FAO")
        self.assertEqual(faro["price"], 111.11)
        self.assertEqual(faro["out_fare_eur"], 100.01)
        self.assertEqual(faro["stops"], 0)
        self.assertEqual(faro["source"], "manual")
        self.assertEqual(faro["fare_label"], "from, no bags")
        self.assertEqual(faro["checked_at"], "2026-11-13T18:05:00Z")
        self.assertEqual(faro["checked_at_dublin"], "13 Nov 2026, 18:05")
        self.assertFalse(faro["stale"])
        self.assertEqual(faro["out_flight"], "FR9991")
        self.assertTrue(faro["matched_shortlist"])

        beauvais = next(deal for board in ork_weekend for deal in board["deals"] if deal["code"] == "BVA")
        self.assertEqual(beauvais["city"], "Paris")
        self.assertEqual(beauvais["airport_label"], "Beauvais")

        week_codes = [deal["code"] for board in payload["airports"]["DUB"]["week_boards"] for deal in board["deals"]]
        self.assertEqual(week_codes, ["BCN"])
        special = payload["airports"]["DUB"]["special_boards"]
        self.assertEqual(special[0]["trip_type"], "christmas")
        self.assertEqual(special[0]["deals"][0]["code"], "MAD")
        self.assertFalse(special[0]["deals"][0]["matched_shortlist"])
        aer = next(deal for board in payload["airports"]["DUB"]["weekend_boards"]
                   for deal in board["deals"] if deal["code"] == "AGP")
        self.assertEqual(aer["airlines"], "Aer Lingus")
        self.assertIn("aerlingus.com", aer["source_url"])

    def test_example_cannot_be_written_to_the_live_cache(self):
        code = manual_fares.main([
            "--csv", str(EXAMPLE),
            "--allow-example",
            "--publish",
            "--force",
            "--out", str(LIVE),
        ])
        self.assertEqual(code, 1)
        self.assertEqual(LIVE.read_bytes(), self.cache_before)

    def test_cork_and_dublin_only_and_marrakesh_is_skipped(self):
        for origin, needle in (("KIR", "Kerry"), ("SNN", "Shannon"), ("ORKK", "ORK or DUB")):
            text = " ".join(self.errors([{"origin": origin}]))
            self.assertIn(needle, text)
        self.assertEqual(manual_fares.EXCLUDED_DESTINATIONS["RAK"], "Marrakesh")
        text = " ".join(self.errors([{"destination": "RAK"}]))
        self.assertIn("Marrakesh", text)
        self.assertIn("excluded until a destination page is approved", text)
        self.assertNotIn("policy", text.lower())
        self.assertTrue(self.errors([{"destination": "ZZZ"}]))

        payload, report = self.convert([
            {"destination": "RAK", "screenshot_ref": "checks/2026-11-13/rak.png"},
            {"destination": "AGP", "screenshot_ref": "checks/2026-11-13/agp.png"},
        ])
        self.assertEqual(report["excluded"], 1)
        self.assertIn("excluded until a destination page is approved", report["excluded_messages"][0])
        codes = [deal["code"] for board in payload["airports"]["ORK"]["weekend_boards"]
                 for deal in board["deals"]]
        self.assertEqual(codes, ["AGP"])
        self.assertNotIn("RAK", json.dumps(payload))

        kerry = self.errors([{"origin": "KIR", "destination": "RAK"}])
        self.assertTrue(any("Kerry" in item for item in kerry))

    def test_date_price_and_checked_at_rules(self):
        self.assertTrue(self.errors([{"ret_date": "2026-12-01", "nights": "1"}]))
        self.assertTrue(any("span" in item for item in self.errors([{"nights": "3"}])))
        self.assertTrue(self.errors([{"total_pp_eur": "0"}]))
        self.assertTrue(self.errors([{"out_fare_eur": "-5", "total_pp_eur": "6.10"}]))
        self.assertTrue(any("differs" in item for item in self.errors([{"total_pp_eur": "200"}])))
        future = (NOW + dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertTrue(any("future" in item for item in self.errors([{"checked_at_utc": future}])))
        self.assertTrue(any("timezone" in item for item in self.errors(
            [{"checked_at_utc": "2026-11-13T18:05:00"}])))
        self.assertTrue(self.errors([{
            "source_url": "https://www.skyscanner.ie/transport/flights/ork/fao/",
        }]))
        self.assertTrue(self.errors([{"airline": "Lufthansa"}]))

    def test_stale_flag_and_hide(self):
        payload, report = self.convert([{}], now=NOW + dt.timedelta(hours=49))
        deal = payload["airports"]["ORK"]["weekend_boards"][0]["deals"][0]
        self.assertTrue(deal["stale"])
        self.assertEqual(report["stale"], 1)
        self.assertEqual(report["published"], 1)

        with self.assertRaises(manual_fares.ValidationError) as caught:
            self.convert([{}], now=NOW + dt.timedelta(hours=169))
        self.assertIn("expired", str(caught.exception))

    def test_departed_row_is_dropped(self):
        payload, report = self.convert([
            {"out_date": "2026-11-10", "ret_date": "2026-11-12", "nights": "2",
             "screenshot_ref": "checks/2026-11-13/old.png"},
            {"destination": "AGP", "screenshot_ref": "checks/2026-11-13/agp.png"},
        ])
        self.assertEqual(report["departed"], 1)
        codes = [deal["code"] for board in payload["airports"]["ORK"]["weekend_boards"]
                 for deal in board["deals"]]
        self.assertEqual(codes, ["AGP"])

    def test_duplicate_keeps_the_newer_check(self):
        payload, report = self.convert([
            {"checked_at_utc": "2026-11-13T18:05:00Z", "total_pp_eur": "111.11"},
            {"checked_at_utc": "2026-11-14T09:00:00Z", "total_pp_eur": "111.11",
             "out_fare_eur": "50.00", "ret_fare_eur": "61.11",
             "screenshot_ref": "checks/2026-11-14/ork-fao.png"},
        ])
        self.assertEqual(report["duplicates"], 1)
        deal = payload["airports"]["ORK"]["weekend_boards"][0]["deals"][0]
        self.assertEqual(deal["checked_at"], "2026-11-14T09:00:00Z")
        self.assertEqual(deal["out_fare_eur"], 50)

    def test_cities_cover_the_destination_pages(self):
        missing = set(generate_pages.CITIES) - set(manual_fares.DESTINATIONS)
        self.assertEqual(missing, set())

    def test_flightapi_page_is_unchanged_and_manual_row_is_labelled(self):
        cache = json.loads((ROOT / "deals_cache.json").read_text())
        counts = {code: len(generate_pages.collect_fares(cache, code)) for code in generate_pages.CITIES}
        rows = generate_pages.collect_fares(cache, "FAO")
        disk = (ROOT / "destinations" / "faro.html").read_text()
        body = re.search(r"<tbody>\n(.*)\n</tbody>", disk, re.S).group(1)
        self.assertEqual(generate_pages.fare_tbody(rows), body)
        slug, city, country, blurb = generate_pages.CITIES["FAO"]
        updated = generate_pages.fmt_date(cache["updated_utc"][:10])
        page = generate_pages.page_html("FAO", slug, city, country, blurb, rows, updated, counts)
        self.assertEqual(page, disk)
        self.assertNotIn("from, no bags", page)
        self.assertNotIn("data-checked-at", page)

        payload, _report = manual_fares.convert_file(EXAMPLE, now=NOW, allow_example=True)
        manual_rows = generate_pages.collect_fares(payload, "FAO")
        manual_body = generate_pages.fare_tbody(manual_rows)
        self.assertIn("from €111.11 return, no bags", manual_body)
        self.assertIn("Checked on ryanair.com", manual_body)
        self.assertIn("13 Nov 2026, 18:05", manual_body)
        self.assertIn('data-checked-at="2026-11-13T18:05:00Z"', manual_body)
        self.assertIn("https://www.ryanair.com/ie/en/trip/flights/select?example=1", manual_body)
        paris = generate_pages.collect_fares(payload, "CDG")
        paris_body = generate_pages.fare_tbody(paris)
        self.assertIn("Beauvais", paris_body)
        manual_counts = dict(counts)
        manual_counts["FAO"] = len(manual_rows)
        manual_page = generate_pages.page_html(
            "FAO", slug, city, country, blurb, manual_rows, updated, manual_counts)
        self.assertIn("Checked on ryanair.com", manual_page)
        self.assertIn("data-checked-at", manual_page)
        self.assertIn("from €111.11 return, no bags", manual_page)
        self.assertIn("STALE_HOURS = 48", manual_page)
        self.assertIn("HIDE_HOURS = 168", manual_page)
        self.assertIn("No fare in the current scan", manual_page)
        self.assertNotIn("gtag", generate_pages.CHECKED_ASSETS)
        self.assertNotIn("googletagmanager", generate_pages.CHECKED_ASSETS)

    def test_refresh_switch_does_not_call_flightapi_or_touch_the_live_cache(self):
        self.assertFalse(refresh_deals.use_manual_fares())
        with tempfile.TemporaryDirectory() as directory:
            path = write_csv([{}], directory)
            out = pathlib.Path(directory) / "out.json"
            env = os.environ.copy()
            previous = {key: os.environ.get(key) for key in
                        ("FARE_SOURCE", "MANUAL_FARES_CSV", "MANUAL_FARES_OUT", "FLIGHTAPI_KEY")}
            os.environ["FARE_SOURCE"] = "manual"
            os.environ["MANUAL_FARES_CSV"] = str(path)
            os.environ["MANUAL_FARES_OUT"] = str(out)
            os.environ.pop("FLIGHTAPI_KEY", None)
            try:
                with self.assertRaises(SystemExit) as caught:
                    refresh_deals.main()
                self.assertEqual(caught.exception.code, 0)
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
            written = json.loads(out.read_text())
            self.assertEqual(written["fare_source"], "manual")
            self.assertEqual(written["airports"]["ORK"]["weekend_boards"][0]["deals"][0]["price"], 111.11)
        self.assertEqual(LIVE.read_bytes(), self.cache_before)

    def test_live_csv_skips_unknown_airports_and_keeps_the_newest_duplicate(self):
        path = ROOT / "data" / "manual_fares.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        keys = [
            (row["origin"], row["destination"], row["out_date"], row["ret_date"], row["airline"])
            for row in rows
        ]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(rows), 113)
        edi = next(row for row in rows if row["origin"] == "ORK" and row["destination"] == "EDI"
                   and row["out_date"] == "2026-12-06" and row["airline"] == "Ryanair")
        self.assertEqual(edi["checked_at_utc"], "2026-11-14T00:28:20Z")
        self.assertEqual(edi["screenshot_ref"], "ba5e7516")

        with self.assertRaises(manual_fares.ValidationError) as caught:
            manual_fares.convert_file(path, now=NOW)
        text = str(caught.exception)
        for code in ("ARN", "BTS", "CGN", "DBV", "GDN", "HAM", "POZ", "RBA"):
            self.assertIn(code, text)
        self.assertNotIn("Kerry", text)
        self.assertNotIn("Shannon", text)

        deals, report = manual_fares.supplement_deals(path, now=NOW)
        rejected = {item["destination"] for item in report["rejected"]}
        self.assertEqual(rejected, {"ARN", "BTS", "CGN", "DBV", "GDN", "HAM", "POZ", "RBA"})
        self.assertEqual(len(report["rejected"]), 9)
        self.assertGreater(report["blank_screenshot"], 0)
        self.assertTrue(any(deal["code"] == "MXP" for deal in deals))
        alicante = next(
            deal for deal in deals
            if deal["origin_airport"] == "ORK" and deal["code"] == "ALC"
            and deal["depart_date"] == "2026-12-05" and deal["return_date"] == "2026-12-12"
        )
        self.assertFalse(alicante["matched_shortlist"])
        self.assertEqual(alicante["price"], 66.74)
        self.assertNotIn("RAK", {deal["code"] for deal in deals})
        self.assertEqual(LIVE.read_bytes(), self.cache_before)

    def test_supplement_fills_empty_origins_and_leaves_flightapi_fares(self):
        deals, _report = manual_fares.supplement_deals(now=NOW)
        cache = json.loads((ROOT / "deals_cache.json").read_text())

        def shown(code):
            flight = generate_pages.collect_fares(cache, code)
            return generate_pages.supplement_rows(code, flight, deals)

        beauvais = shown("BVA")
        self.assertTrue(beauvais)
        self.assertTrue(all(row.get("checked_at") for row in beauvais))
        by_origin = {}
        for row in beauvais:
            by_origin.setdefault(row["from"], []).append(row)
        self.assertEqual(set(by_origin), {"Cork", "Dublin"})
        self.assertEqual(len(by_origin["Dublin"]), 1)
        self.assertEqual(by_origin["Dublin"][0]["price"], 32.98)
        self.assertEqual(by_origin["Dublin"][0]["dep"], "2026-12-05")
        self.assertIn("ryanair.com", by_origin["Dublin"][0]["source_url"])

        faro = shown("FAO")
        self.assertTrue(faro)
        self.assertFalse(any(row.get("checked_at") for row in faro))

        alicante = shown("ALC")
        self.assertFalse(any(row.get("source_url") for row in alicante))

        for code in ("GVA", "LYS", "MUC", "PRG"):
            rows = shown(code)
            self.assertFalse(any(row.get("checked_at") for row in rows))

        athens = shown("ATH")
        self.assertEqual({row["from"] for row in athens}, {"Dublin"})
        self.assertEqual(athens[0]["price"], 90.98)
        self.assertNotIn("Cork", [row["from"] for row in athens])

        malpensa = shown("MXP")
        self.assertEqual(malpensa[0]["from"], "Dublin")
        self.assertEqual(malpensa[0]["price"], 45.73)

        aer = {
            "from": "Cork",
            "kind": "Week",
            "dep": "2026-12-16",
            "ret": "2026-12-23",
            "nights": 7,
            "price": 147.85,
            "airline": "Aer Lingus",
            "saver": False,
            "code": "ACE",
            "checked_at": "2026-11-14T01:02:43Z",
            "checked_at_dublin": "14 Nov 2026, 01:02",
            "source_url": "https://www.aerlingus.com/html/flightSearchResult.html#/fare",
            "fare_label": "from, no bags",
            "stale": False,
            "airport_label": "",
        }
        body = generate_pages.fare_tbody([aer])
        self.assertIn("Checked on aerlingus.com", body)
        self.assertIn("aerlingus.com", body)
        self.assertIn("from €147.85 return, no bags", body)
        self.assertNotIn("ryanair.com", body)

        slug, city, country, blurb = generate_pages.CITIES["MAD"]
        madrid_rows = shown("MAD")
        self.assertTrue(madrid_rows)
        self.assertFalse(any(row.get("checked_at") for row in madrid_rows))
        self.assertEqual({row["from"] for row in madrid_rows}, {"Dublin"})
        counts = {code: len(shown(code)) for code in generate_pages.CITIES}
        html = generate_pages.page_html(
            "MAD", slug, city, country, blurb, madrid_rows,
            generate_pages.fmt_date(cache["updated_utc"][:10]), counts)
        title = re.search(r"<title>([^<]+)</title>", html).group(1)
        self.assertEqual(title, "Dublin to Madrid flights | Holiday Chasers")
        self.assertLessEqual(len(title), 60)
        self.assertIn("<h1>Dublin to Madrid flights</h1>", html)
        description = re.search(r'<meta name="description" content="([^"]*)">', html).group(1)
        self.assertIn("Dublin", description)
        routes = re.search(r'<div class="routes">(.*?)</div>', html, re.S).group(1)
        self.assertNotIn("Cork", routes)
        self.assertIn('src="/consent.js"', html)
        self.assertEqual(LIVE.read_bytes(), self.cache_before)

    def test_view_time_script_drops_a_week_old_fare_and_build_time_does_too(self):
        deals, report = manual_fares.supplement_deals(now=NOW + dt.timedelta(hours=169))
        self.assertEqual(deals, [])
        self.assertTrue(report["expired"])
        script = generate_pages.checked_assets([{
            "checked_at": "2026-11-13T18:05:00Z",
        }])
        self.assertIn("data-checked-at", script)
        self.assertIn("HIDE_HOURS = 168", script)
        self.assertIn("STALE_HOURS = 48", script)
        self.assertIn("data-manual-fallback", script)
        self.assertIn("removeChild", script)
        consent = (ROOT / "consent.js").read_text(encoding="utf-8")
        self.assertIn("hc_consent", consent)
        self.assertIn('location.hostname !== "holidaychasers.ie"', consent)
        for name in ("hero_dub_classic.html", "sun_dub_classic.html", "sun_ork_classic.html"):
            text = (ROOT / "social" / "p" / name).read_text(encoding="utf-8")
            self.assertNotIn("data-manual", text)
            self.assertNotIn("manual_fares", text)

    def test_workflow_file_does_not_call_the_converter(self):
        text = (ROOT / ".github" / "workflows" / "refresh_deals.yml").read_text()
        self.assertNotIn("manual_fares", text)
        self.assertNotIn("FARE_SOURCE", text)


if __name__ == "__main__":
    unittest.main()
