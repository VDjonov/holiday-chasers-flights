"""Destination pages for the airports checked on ryanair.com, 13–14 Nov 2026.

No network. Prices come only from deals_cache.json. The FlightAPI route list
is not extended.
"""

import json
import pathlib
import re
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.modules.setdefault("requests", types.ModuleType("requests"))

import generate_pages
import manual_fares
import refresh_deals

NEW = {
    "BVA": ("Cork", "Dublin"),
    "MXP": ("Dublin",),
    "LUX": ("Dublin",),
    "BRU": ("Dublin",),
    "AGA": ("Dublin",),
    "FNC": ("Dublin",),
}
BANNED = ("Kerry", "Shannon", "Marrakesh", "all Irish airports")


def _meta(html, name):
    match = re.search(
        rf'<meta name="{name}" content="([^"]*)">', html)
    if not match:
        match = re.search(
            rf'<meta property="{name}" content="([^"]*)">', html)
    return match.group(1) if match else ""


class DestinationPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = json.loads((ROOT / "deals_cache.json").read_text())
        cls.updated = generate_pages.fmt_date(cls.cache["updated_utc"][:10])
        cls.counts = {
            code: len(generate_pages.collect_fares(cls.cache, code))
            for code in generate_pages.CITIES
        }

    def page(self, code):
        slug, city, country, blurb = generate_pages.CITIES[code]
        rows = generate_pages.collect_fares(self.cache, code)
        html = generate_pages.page_html(
            code, slug, city, country, blurb, rows, self.updated, self.counts)
        return html, rows

    def test_scanner_route_list_does_not_gain_the_new_airports(self):
        scanner = {row[0] for row in refresh_deals.DESTINATIONS}
        self.assertTrue(NEW.keys().isdisjoint(scanner))
        for code in ("MAD", "LPA", "ALC", "CRL"):
            self.assertIn(code, scanner)

    def test_existing_airports_keep_their_pages(self):
        slugs = {code: item[0] for code, item in generate_pages.CITIES.items()}
        self.assertEqual(slugs["MAD"], "madrid")
        self.assertEqual(slugs["LPA"], "las-palmas")
        self.assertEqual(slugs["ALC"], "alicante")
        self.assertEqual(slugs["CRL"], "brussels")
        self.assertEqual(slugs["BGY"], "milan")
        self.assertEqual(slugs["CDG"], "paris")
        self.assertNotIn("gran-canaria", slugs.values())
        self.assertNotIn("charleroi", slugs.values())
        self.assertNotIn("marrakesh", slugs.values())
        self.assertEqual(
            generate_pages.SEARCH["MAD"],
            ("Cork to Madrid | Dublin fares", "Cork to Madrid flights: Dublin fares in this scan"),
        )
        self.assertEqual(generate_pages.SEARCH["LPA"][0], "Las Palmas flights from Cork")
        self.assertIn("Cork and Dublin", generate_pages.SEARCH["LPA"][1])
        self.assertEqual(
            generate_pages.SEARCH["ALC"],
            ("Dublin to Alicante flights", "Dublin to Alicante flights"),
        )

    def test_every_city_has_a_title_and_a_manual_fare_code(self):
        self.assertEqual(set(generate_pages.SEARCH), set(generate_pages.CITIES))
        missing = set(generate_pages.CITIES) - set(manual_fares.DESTINATIONS)
        self.assertEqual(missing, set())

    def test_new_pages_name_the_verified_origins_and_invent_no_price(self):
        for code, origins in NEW.items():
            html, rows = self.page(code)
            title = re.search(r"<title>([^<]+)</title>", html).group(1)
            title = title.replace("&amp;", "&")
            desc = _meta(html, "description").replace("&amp;", "&")
            self.assertLessEqual(len(title), 60, title)
            self.assertLessEqual(len(desc), 155, desc)
            self.assertIn("FAQPage", html)
            self.assertIn("BreadcrumbList", html)
            self.assertIn('property="og:image"', html)
            self.assertIn('data-hc-event="flight_click"', html)
            self.assertIn('src="/consent.js"', html)
            self.assertNotIn("privacy", html.lower())
            for word in BANNED:
                self.assertNotIn(word, html)
            for origin in origins:
                self.assertIn(origin, desc)
                self.assertIn(origin, title + " " + html)
            routes = re.search(r'<div class="routes">(.*?)</div>', html, re.S).group(1)
            if origins == ("Dublin",):
                self.assertNotIn("Cork", routes)
                self.assertIn("from Dublin", html)
                self.assertNotIn("Cork service", html)
            else:
                self.assertIn("Cork", routes)
                self.assertIn("Dublin", routes)
                self.assertIn("from Cork and Dublin", html)
            self.assertIn("<h2>What to see</h2>", html)
            self.assertIn("<h2>Airport to the city</h2>", html)
            if not rows:
                self.assertIn("No fare in the current scan", html)
                self.assertNotRegex(html, r"€\d")
            else:
                self.fail(f"{code} unexpectedly has scanned fares")
