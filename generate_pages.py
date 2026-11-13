#!/usr/bin/env python3
"""
Holiday Chasers Ireland — SEO destination page generator.

Runs in the GitHub Action right after refresh_deals.py. Reads the fresh
deals_cache.json and writes:

  destinations/<slug>.html   one static, indexable page per destination
  sitemap.xml                homepage, info pages, and all destination pages
  index.html footer          destination links, same cities as these pages
  404.html                   branded not-found page; trailing-slash redirects

Pages are rebuilt on every scan, so Google sees fresh fares every few days.
Zero API credits — everything renders from data already paid for.
"""

import html as html_lib
import json, os, re, datetime as dt

import refresh_deals

SITE = "https://holidaychasers.ie"
OUT_DIR = "destinations"
CACHE = "deals_cache.json"

# Static pages linked from the destination footer and listed in the sitemap.
# Kept here so a deal refresh does not drop them.
INFO_PAGES = (
    "how-it-works.html",
    "about.html",
    "contact.html",
)

# slug + one-line intro per destination (kept short; the fares are the content)
CITIES = {
    "ALC": ("alicante", "Alicante", "Spain", "Costa Blanca beaches, an old-town castle and some of Spain's most reliable sunshine."),
    "BCN": ("barcelona", "Barcelona", "Spain", "Gaudí, beach and late dinners — the classic city break that never misses."),
    "AGP": ("malaga", "Malaga", "Spain", "Gateway to the Costa del Sol with a buzzing old town and year-round warmth."),
    "PMI": ("palma-mallorca", "Palma Mallorca", "Spain", "Cathedral views, island beaches and easy family resorts a short hop away."),
    "MAD": ("madrid", "Madrid", "Spain", "Big-city Spain: world-class art, tapas crawls and late-night energy."),
    "TFS": ("tenerife", "Tenerife", "Spain", "Winter sun favourite — volcano hikes, black-sand beaches and family resorts."),
    "ACE": ("lanzarote", "Lanzarote", "Spain", "Otherworldly volcanic landscapes and dependable sunshine all year."),
    "FAO": ("faro", "Faro", "Portugal", "The door to the Algarve's golden beaches, golf and seafood."),
    "LIS": ("lisbon", "Lisbon", "Portugal", "Hills, trams and pastel de nata — Europe's most charming capital break."),
    "OPO": ("porto", "Porto", "Portugal", "Port cellars, riverside dinners and azulejo-covered streets."),
    "FCO": ("rome", "Rome", "Italy", "The eternal city — ruins, piazzas and the world's best people-watching."),
    "BGY": ("milan", "Milan", "Italy", "Fashion, the Duomo and aperitivo hour — with the lakes an hour away."),
    "CDG": ("paris", "Paris", "France", "Museums, cafés and riverside walks — always a good idea."),
    "NCE": ("nice", "Nice", "France", "Riviera glamour, promenade strolls and Old Town markets."),
    "AMS": ("amsterdam", "Amsterdam", "Netherlands", "Canals, bikes and world-class museums in Europe's easiest weekend city."),
    "BER": ("berlin", "Berlin", "Germany", "History, nightlife and neighbourhood culture at refreshingly fair prices."),
    "MUC": ("munich", "Munich", "Germany", "Beer gardens, Alpine day trips and Bavaria's handsome capital."),
    "BUD": ("budapest", "Budapest", "Hungary", "Thermal baths, ruin bars and grand Danube views — superb value."),
    "KRK": ("krakow", "Krakow", "Poland", "A perfectly preserved old town, hearty food and easy day trips."),
    "WMI": ("warsaw", "Warsaw", "Poland", "A rebuilt old town, serious museums and a booming food scene."),
    "PRG": ("prague", "Prague", "Czech Republic", "Fairytale bridges, castle views and Europe's best beer."),
    "EDI": ("edinburgh", "Edinburgh", "Scotland", "Castle, closes and cosy pubs — a short hop with big atmosphere."),
    "STN": ("london", "London", "England", "Theatre, markets, museums — the quickest big-city fix from Ireland."),
    "MAN": ("manchester", "Manchester", "England", "Football, music heritage and a friendly northern weekend."),
    "GVA": ("geneva", "Geneva", "Switzerland", "Lakeside calm with the Alps on the doorstep."),
    "MLA": ("malta", "Malta", "Malta", "Honey-stone harbours, sea swims and 300 days of sun."),
    "VIE": ("vienna", "Vienna", "Austria", "Coffee houses, palaces and concert halls — imperial Europe at its best."),
    "ATH": ("athens", "Athens", "Greece", "The Acropolis, rooftop tavernas and island ferries from the port."),
    "VLC": ("valencia", "Valencia", "Spain", "City beach, paella's birthplace and the futuristic Arts & Sciences quarter."),
    "CPH": ("copenhagen", "Copenhagen", "Denmark", "Harbour swims, design shops and the world's happiest cycling city."),
    "SVQ": ("seville", "Seville", "Spain", "Flamenco, orange trees and Andalusia's most romantic streets."),
    "VCE": ("venice", "Venice", "Italy", "Canals, vaporetti and golden light — like nowhere else on earth."),
    "PSA": ("pisa", "Pisa", "Italy", "The leaning tower plus Tuscany — Florence is an hour by train."),
    "ZAD": ("zadar", "Zadar", "Croatia", "Roman ruins, the Sea Organ and Adriatic island hopping."),
    "RHO": ("rhodes", "Rhodes", "Greece", "A walled medieval town wrapped in Greek-island beaches."),
    "FUE": ("fuerteventura", "Fuerteventura", "Spain", "The Canaries' best beaches — huge dunes and turquoise water."),
    "LPA": ("las-palmas", "Las Palmas", "Spain", "Gran Canaria's capital: city beach, old town and winter warmth."),
    "ZRH": ("zurich", "Zurich", "Switzerland", "Lake swims, old-town lanes and trains straight into the Alps."),
    "BHX": ("birmingham", "Birmingham", "England", "Canals, curry mile and a revived city centre — a quick hop from Cork."),
    "BRS": ("bristol", "Bristol", "England", "Harbourside street art, Clifton Bridge and a thriving food scene."),
    "LPL": ("liverpool", "Liverpool", "England", "Beatles history, waterfront museums and a famously warm welcome."),
    "GLA": ("glasgow", "Glasgow", "Scotland", "Music venues, Victorian architecture and the gateway to the Highlands."),
    "CRL": ("brussels", "Brussels", "Belgium", "Grand Place, waffles and chocolate — flying into Charleroi, with a shuttle to the centre."),
    "LYS": ("lyon", "Lyon", "France", "France's food capital: bouchons, Roman ruins and a hillside old town."),
    "ADB": ("izmir", "Izmir", "Turkey", "Aegean sunshine, bazaars and Ephesus within easy reach."),
}

# Distinctive half of each <title>, after "flights from Cork & Dublin | ".
HOOKS = {
    "ALC": "Costa Blanca sun",
    "BCN": "city, beach and Gaudí",
    "AGP": "Costa del Sol breaks",
    "PMI": "Mallorca island breaks",
    "MAD": "city breaks and tapas",
    "TFS": "winter sun",
    "ACE": "year-round volcanic sun",
    "FAO": "Algarve beach holidays",
    "LIS": "tram and hillside breaks",
    "OPO": "riverside city breaks",
    "FCO": "city breaks in Italy",
    "BGY": "city and lakes breaks",
    "CDG": "weekend city breaks",
    "NCE": "French Riviera trips",
    "AMS": "canal city breaks",
    "BER": "neighbourhood city breaks",
    "MUC": "Bavaria and the Alps",
    "BUD": "Danube city breaks",
    "KRK": "old-town city breaks",
    "WMI": "old-town and museum breaks",
    "PRG": "bridge and castle breaks",
    "EDI": "short castle-city hops",
    "STN": "Stansted city breaks",
    "MAN": "northern weekend hops",
    "GVA": "lake and ski-season trips",
    "MLA": "harbour and sun breaks",
    "VIE": "palace and concert breaks",
    "ATH": "Acropolis city breaks",
    "VLC": "beach and city breaks",
    "CPH": "harbour city breaks",
    "SVQ": "Andalusia city breaks",
    "VCE": "canal city breaks",
    "PSA": "Tuscany breaks",
    "ZAD": "Adriatic summer trips",
    "RHO": "Greek island breaks",
    "FUE": "Canary dune beaches",
    "LPA": "Gran Canaria city and beach",
    "ZRH": "lake and Alpine trips",
    "BHX": "short city hops from Cork",
    "BRS": "harbourside city breaks",
    "LPL": "waterfront weekend hops",
    "GLA": "city and Highland hops",
    "CRL": "Charleroi city breaks",
    "LYS": "food-city breaks",
    "ADB": "Aegean sun breaks",
}

# Same country, region, or a nearby city. Earlier groups win.
REGIONS = (
    ["ALC", "VLC", "AGP", "SVQ", "MAD", "BCN", "PMI"],
    ["TFS", "ACE", "FUE", "LPA"],
    ["FAO", "LIS", "OPO"],
    ["FCO", "BGY", "VCE", "PSA"],
    ["CDG", "NCE", "LYS"],
    ["ATH", "RHO", "MLA", "ADB"],
    ["ZAD", "VCE", "PSA", "FCO"],
    ["AMS", "CRL", "CDG", "LYS"],
    ["BER", "MUC", "VIE", "PRG", "BUD", "ZRH", "GVA"],
    ["KRK", "WMI", "PRG", "BUD", "BER"],
    ["EDI", "GLA", "MAN", "LPL", "BHX", "BRS", "STN"],
    ["GVA", "ZRH", "MUC", "LYS"],
    ["FAO", "AGP", "ALC", "SVQ", "TFS", "ACE", "FUE", "LPA", "MLA"],
)

# Pages Search Console already shows. Titles and H1s follow the query, and
# still carry the Cork & Dublin framing. Copy below is limited to the scan
# schedule in refresh_deals.py, fares in deals_cache.json, or an airline page
# checked for this change. Do not add a route, day or carrier that is not there.
# "SCAN" is replaced with a sentence built from the latest cache.
GUIDES = {
    "PMI": {
        "title": "Flights to Palma from Cork & Dublin | Mallorca | Holiday Chasers",
        "h1": "Flights to Palma from Cork and Dublin",
        "lead": "Flights to Palma from Cork and Dublin",
        "airline_answer": (
            "Ryanair lists both Cork to Mallorca and Dublin to Mallorca. "
            "Aer Lingus's Dublin to Palma page shows no departures for November 2026 "
            "through April 2027, and lists May 2027. The latest scan stored no fare, "
            "so the table does not add a carrier from a booking."
        ),
        "sections": [
            ("Cork", [
                "Ryanair lists Cork to Mallorca. The schedule this scan uses has no Cork to Palma flights after 24 October 2026 until Tuesdays from 18 May 2027 through 31 August 2027.",
                "A Tuesday departure can be priced as a week of 6, 7 or 8 nights. It cannot be priced as a weekend, because weekends on this scan leave Thursday, Friday or Saturday.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair lists Dublin to Mallorca. The schedule this scan uses starts Dublin to Palma on 11 March 2027, on Tuesdays and Thursdays, through 24 October 2027.",
                "Aer Lingus's own Dublin to Palma page shows no departures for November 2026 through April 2027, and lists May 2027. A Thursday can be priced as a weekend of 2 or 3 nights, and either Tuesday or Thursday can be priced as a week of 6, 7 or 8 nights, once those dates sit inside the scan window.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("When do Palma flights from Cork and Dublin start again?",
             "On the schedule this scan uses, Dublin to Palma is Tuesdays and Thursdays from 11 March 2027 to 24 October 2027, and Cork to Palma is Tuesdays from 18 May 2027 to 31 August 2027. No price is shown until a scan stores a real return."),
            ("Can I book a weekend to Palma from Cork?",
             "Not on the next Cork dates in this scan's schedule. Those are Tuesdays only, and a weekend here has to leave on Thursday, Friday or Saturday. A Tuesday can still make a one-week trip of 6, 7 or 8 nights."),
        ],
    },
    "TFS": {
        "title": "Flights to Tenerife from Cork & Dublin | Holiday Chasers",
        "h1": "Flights to Tenerife from Cork and Dublin",
        "lead": "Flights to Tenerife from Cork and Dublin",
        "sections": [
            ("Cork", [
                "Ryanair lists Cork to Tenerife. Aer Lingus describes a direct Cork to Tenerife flight of about 4 hours 10 minutes, shows a departure on Monday 23 November 2026, and also lists July 2027 and September 2027.",
                "The schedule this scan uses from 26 October to 20 December 2026 is Mondays, Thursdays, Fridays, Saturdays and Sundays. From 28 March 2027 it is Mondays, Wednesdays and Fridays through 31 July 2027.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair lists Dublin to Tenerife. Dublin has no separate weekday schedule in this scan, so it is priced on the usual weekend and week boards.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Are there flights to Tenerife from Cork?",
             "Yes. Ryanair lists Cork to Tenerife, and the latest scan stores Ryanair returns from Cork. Aer Lingus also publishes a direct Cork to Tenerife flight, including Monday 23 November 2026."),
            ("Which days does this scan treat as Cork to Tenerife days?",
             "From 26 October to 20 December 2026 the schedule is Mondays, Thursdays, Fridays, Saturdays and Sundays. From 28 March 2027 it is Mondays, Wednesdays and Fridays through 31 July 2027."),
        ],
    },
    "ACE": {
        "title": "Flights to Lanzarote from Cork & Dublin | Holiday Chasers",
        "h1": "Flights to Lanzarote from Cork and Dublin",
        "lead": "Flights to Lanzarote from Cork and Dublin",
        "sections": [
            ("Cork", [
                "Ryanair lists Cork to Lanzarote. Aer Lingus's flights-from-Cork page says the Lanzarote service is nonstop, and lists departures on 31 January 2027 and 26 April 2027.",
                "The schedule this scan uses through 13 December 2026 includes Mondays, Tuesdays, Wednesdays, Thursdays, Saturdays and Sundays. Friday is not in that overlap.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair lists Dublin to Lanzarote. Dublin has no separate weekday schedule in this scan, so it is priced on the usual weekend and week boards.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Which airlines fly to Lanzarote from Cork and Dublin?",
             "Ryanair lists both Cork to Lanzarote and Dublin to Lanzarote. Aer Lingus says its Cork to Lanzarote flight is nonstop. The airlines in the table are the ones on the latest stored fares."),
            ("Does Cork fly to Lanzarote on Fridays right now?",
             "Not on the schedule this scan uses through 13 December 2026. That overlap is Mondays, Tuesdays, Wednesdays, Thursdays, Saturdays and Sundays."),
        ],
    },
    "AGP": {
        "title": "Flights to Malaga from Cork & Dublin | Costa del Sol | Holiday Chasers",
        "h1": "Flights to Malaga from Cork and Dublin",
        "lead": "Flights to Malaga from Cork and Dublin",
        "sections": [
            ("Cork", [
                "Ryanair lists Cork to Malaga. Aer Lingus's Cork to Malaga page calls it a direct flight of about 2 hours 50 minutes, and shows November 2026, December 2026, January 2027, February 2027, March 2027 and June 2027.",
                "The schedule this scan uses from 2 November to 20 December 2026 is Mondays, Tuesdays, Wednesdays, Fridays, Saturdays and Sundays. Thursday is not in that window.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair lists Dublin to Malaga. Dublin has no separate weekday schedule in this scan, so it is priced on the usual weekend and week boards.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Who flies direct to Malaga from Cork?",
             "Ryanair lists Cork to Malaga, and Aer Lingus publishes it as a direct flight of about 2 hours 50 minutes. The table shows which of those airlines came back on the latest scan."),
            ("Which days does Cork to Malaga run this winter?",
             "From 2 November to 20 December 2026 the schedule this scan uses is Mondays, Tuesdays, Wednesdays, Fridays, Saturdays and Sundays."),
        ],
    },
    "FAO": {
        "title": "Flights to Faro from Cork & Dublin | Algarve | Holiday Chasers",
        "h1": "Flights to Faro from Cork and Dublin",
        "lead": "Flights to Faro from Cork and Dublin",
        "sections": [
            ("Cork", [
                "Ryanair lists Cork to Faro and shows a fare in every month from November 2026 through October 2027. Dates on that page include Sunday 29 November 2026, Sunday 6 December 2026, Friday 8 January 2027, Friday 5 February 2027 and Thursday 15 April 2027.",
                "The schedule this scan uses from 13 November to 13 December 2026 is Fridays and Sundays. From 28 March 2027 it is every day through 31 July 2027.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair lists Dublin to Faro. Dublin has no separate weekday schedule in this scan, so it is priced on the usual weekend and week boards.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Are there direct flights to Faro from Cork and Dublin?",
             "Yes. Ryanair lists both Cork to Faro and Dublin to Faro, and the latest scan stores Ryanair returns from both airports."),
            ("Which days is Cork to Faro on this scan's schedule?",
             "From 13 November to 13 December 2026 it is Fridays and Sundays. From 28 March 2027 the same schedule is every day through 31 July 2027."),
        ],
    },
    "RHO": {
        "title": "Flights to Rhodes from Ireland | Cork & Dublin | Holiday Chasers",
        "h1": "Flights to Rhodes from Ireland",
        "lead": "Flights to Rhodes from Ireland",
        "airline_answer": (
            "Ryanair lists both Cork to Rhodes and Dublin to Rhodes. "
            "Their Cork page has no fare from November 2026 through April 2027 and lists flights again from May 2027. "
            "Their Dublin page has no fare from November 2026 through February 2027 and lists flights from March 2027. "
            "The latest scan stored no fare, because those dates are outside the window it prices."
        ),
        "sections": [
            ("Cork", [
                "Ryanair's Cork to Rhodes page shows no fare from November 2026 through April 2027. From May 2027 it lists flights on several days each week. Dates on the page include Thursday 27 May 2027, Thursday 29 July 2027, Monday 23 August 2027, Monday 27 September 2027 and Monday 25 October 2027.",
                "The schedule this scan uses is Mondays and Thursdays from 1 June 2026 to 22 October 2026, and it has no 2027 Cork dates. That is why no Cork fare is stored, even though Ryanair is selling summer 2027.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Rhodes page shows no fare from November 2026 through February 2027. From March 2027 it lists flights on multiple days each week. Dates on the page include Tuesday 30 March 2027, Thursday 8 April 2027, Tuesday 24 August 2027, Thursday 16 September 2027 and Tuesday 26 October 2027.",
                "The schedule this scan uses for summer 2027 is Tuesdays, Thursdays and Saturdays from 30 March 2027 to 30 October 2027. This scan only prices through 30 January 2027, so no Dublin fare is stored yet.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Are there flights to Rhodes from Ireland?",
             "Ryanair lists Cork to Rhodes and Dublin to Rhodes. Neither is inside the dates this scan prices, which run through 30 January 2027, so there is no fare on this page."),
            ("When is the next Dublin to Rhodes season on this scan?",
             "Tuesdays, Thursdays and Saturdays from 30 March 2027 to 30 October 2027. Ryanair's own page also lists Tuesday 30 March 2027 and other Tuesdays and Thursdays through October 2027."),
        ],
    },
    "KRK": {
        "title": "Cork to Krakow flights | Cork & Dublin | Holiday Chasers",
        "h1": "Cork to Krakow flights",
        "lead": "Cork to Krakow flights",
        "sections": [
            ("Cork", [
                "Ryanair's city-to-city list includes Dublin to Krakow and does not include Cork to Krakow. This scan does not look for a Cork to Krakow flight, because that direct route is not on the list.",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Krakow page lists a fare in every month from November 2026 through October 2027 and says the flight runs every day, typically once a day and sometimes twice. Dates on the page include Monday 23 November 2026, Saturday 5 December 2026, Saturday 30 January 2027, Saturday 27 February 2027 and Saturday 6 March 2027.",
                "Dublin has no separate weekday schedule in this scan, so it is priced on the usual weekend and week boards.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Is there a direct flight from Cork to Krakow?",
             "Not on Ryanair's route list, and not in the routes this scan prices. The direct flight we track leaves from Dublin."),
            ("Does Dublin fly to Krakow every day?",
             "Ryanair says the Dublin to Krakow flight runs every day, typically once a day and sometimes twice. The table shows the weekend and one-week dates the latest scan actually stored."),
        ],
    },
    "PSA": {
        "title": "Dublin to Pisa flights | Cork & Dublin | Holiday Chasers",
        "h1": "Dublin to Pisa flights",
        "lead": "Dublin to Pisa flights",
        "sections": [
            ("Cork", [
                "Ryanair's Cork to Pisa page shows no fare for November 2026 through February 2027. From March 2027 it lists flights on multiple days each week. Dates on the page include Friday 23 April 2027, Friday 21 May 2027, Monday 9 August 2027 and Friday 3 September 2027.",
                "The schedule this scan uses is Mondays and Fridays from 3 April 2026 to 23 October 2026, with nothing after that, so this run stored no Cork fare.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Pisa page lists a fare in every month from November 2026 through October 2027 and says the flight runs on most days, at least once a day. Dates on the page include Thursday 10 December 2026, Monday 18 January 2027, Monday 1 February 2027 and Wednesday 5 May 2027.",
                "Dublin has no separate weekday schedule in this scan, so it is priced on the usual weekend and week boards. A Saturday in the table is a date the scan stored, not the only day the route flies.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Does Dublin fly direct to Pisa?",
             "Yes. Ryanair lists Dublin to Pisa in every month from November 2026 through October 2027, and says it runs on most days. The table is the returns the latest scan stored."),
            ("Are there Cork to Pisa flights this winter?",
             "Ryanair shows no Cork to Pisa fare for November 2026 through February 2027, then lists flights again from March 2027. This scan's Cork schedule ends on 23 October 2026, so no Cork fare is stored."),
        ],
    },
}

TRIP_PARAGRAPH = (
    "This scan prices two trip lengths. A weekend is 2 or 3 nights and leaves on "
    "Thursday, Friday or Saturday. A week is 6, 7 or 8 nights, and 7 nights is preferred. "
    "The table only includes a date when a real return fare came back for one of those shapes."
)

# Homepage links to the pages above. Anchor text follows the search, not a price.
POPULAR_ROUTES = (
    ("faro.html", "Faro", "Flights to Faro", "Cork and Dublin"),
    ("tenerife.html", "Tenerife", "Flights to Tenerife from Cork", "Cork and Dublin"),
    ("rhodes.html", "Rhodes", "Flights to Rhodes from Ireland", "Cork and Dublin"),
    ("krakow.html", "Krakow", "Cork to Krakow", "Direct from Dublin"),
    ("pisa.html", "Pisa", "Dublin to Pisa", "Cork and Dublin"),
    ("palma-mallorca.html", "Palma", "Flights to Palma", "Cork and Dublin"),
    ("lanzarote.html", "Lanzarote", "Flights to Lanzarote", "Cork and Dublin"),
    ("malaga.html", "Malaga", "Flights to Malaga", "Cork and Dublin"),
)
POPULAR_START = "<!-- hc-popular-routes -->"
POPULAR_END = "<!-- /hc-popular-routes -->"


def fmt_date(iso):
    try:
        return dt.date.fromisoformat(iso).strftime("%a %-d %b")
    except Exception:
        return iso or ""


def fmt_date_year(iso):
    try:
        return dt.date.fromisoformat(iso).strftime("%-d %b %Y")
    except Exception:
        return iso or ""


def collect_fares(cache, code):
    """All scanned direct fares for one destination, both airports."""
    rows = []
    for ap_code, ap_name in (("ORK", "Cork"), ("DUB", "Dublin")):
        ap = (cache.get("airports") or {}).get(ap_code) or {}
        for kind, boards in (("Weekend", ap.get("weekend_boards") or []),
                             ("Week", ap.get("week_boards") or [])):
            for b in boards:
                deal = next((d for d in (b.get("deals") or [])
                             if (d.get("code") or "").upper() == code), None)
                if not deal:
                    continue
                rows.append({
                    "from": ap_name,
                    "kind": kind,
                    "dep": deal.get("depart_date") or b.get("depart_date") or "",
                    "ret": deal.get("return_date") or b.get("return_date") or "",
                    "nights": deal.get("nights") or b.get("nights") or "",
                    "price": deal.get("price"),
                    "airline": (deal.get("airlines") or "—").split(",")[0].strip(),
                    "saver": bool(deal.get("midweek_saver")),
                })
    rows.sort(key=lambda r: r["dep"])
    return rows


def _clip(text, limit=158):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0].rstrip(".,; ")
    return cut + "…"


def related_destinations(code, fare_counts, limit=4):
    """Same country or a nearby city. Empty pages only link to places with fares."""
    country = CITIES[code][2]
    chosen = []

    def add(other, need_fare):
        if other == code or other not in CITIES or other in chosen:
            return
        if need_fare and not fare_counts.get(other):
            return
        chosen.append(other)

    for group in REGIONS:
        if code not in group:
            continue
        for other in group:
            add(other, True)
            if len(chosen) >= limit:
                return chosen
    for other, (_slug, _name, other_country, _blurb) in CITIES.items():
        if other_country == country:
            add(other, True)
            if len(chosen) >= limit:
                return chosen
    if fare_counts.get(code) and len(chosen) < 3:
        for group in REGIONS:
            if code not in group:
                continue
            for other in group:
                add(other, False)
                if len(chosen) >= limit:
                    return chosen
    # An empty page should not dead-end on one neighbour. These all have
    # fares on a normal scan; add() still skips any that are empty today.
    if not fare_counts.get(code):
        for other in ("AGP", "FAO", "ALC", "TFS", "BCN", "LIS", "FCO", "MLA"):
            add(other, True)
            if len(chosen) >= limit:
                break
    return chosen


def empty_copy(code, city, updated):
    """Honest explanation when the cache has no fare. Never states a price."""
    info = refresh_deals.coverage(code)
    window = fmt_date_year(info["window_end"].isoformat())
    flying = [o for o in info["origins"] if o["queryable"]]
    if flying:
        bits = []
        for origin in flying:
            if origin["days"]:
                bits.append(f"{origin['name']} flies direct on {origin['days']}")
            else:
                bits.append(f"{origin['name']} is on the scan")
        who = "; ".join(bits)
        missing = [o["name"] for o in info["origins"] if not o["queryable"]]
        only = ""
        if not missing and len(info["origins"]) == 1:
            other = "Cork" if info["origins"][0]["code"] == "DUB" else "Dublin"
            only = f" There is no {other} route."
        elif missing:
            only = " No " + " or ".join(missing) + " departure in this window."
        return (
            f"No fare was stored on the latest scan ({updated}). {who}, and those "
            f"days sit inside this scan, which runs through {window}.{only} "
            f"A price is shown here only after a scan stores a real return."
        )
    bits = []
    for origin in info["origins"]:
        if origin["next"]:
            when = fmt_date_year(origin["next"].isoformat())
            days = f", {origin['days']}" if origin["days"] else ""
            bits.append((origin["next"], f"{origin['name']} from {when}{days}"))
        else:
            bits.append((None, f"{origin['name']}: no restart date in the schedule we use"))
    bits.sort(key=lambda item: (item[0] is None, item[0] or dt.date.max))
    nxt = "; ".join(text for _when, text in bits) if bits else "no later direct service is in the schedule we scan"
    return (
        f"No direct flights from Cork or Dublin to {city} in the dates this scan "
        f"covers, through {window}. Next on that schedule: {nxt}. "
        f"We don't estimate a price for the gap."
    )


def _name_list(names):
    names = [name for name in names if name]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + " and " + names[-1]


def _scan_paragraph(origin, rows):
    """Airlines, weekdays and trip lengths actually stored for one airport."""
    if not rows:
        return f"The latest scan stored no {origin} fare."
    airlines = _name_list(sorted({
        r["airline"] for r in rows if r["airline"] and r["airline"] != "—"
    }))
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days = sorted({
        dt.date.fromisoformat(r["dep"]).strftime("%A")
        for r in rows if r.get("dep")
    }, key=order.index)
    nights = sorted({
        int(r["nights"]) for r in rows
        if str(r.get("nights") or "").isdigit()
    })
    text = (
        f"The latest scan stored {airlines} returns from {origin}"
        if airlines else
        f"The latest scan stored fares from {origin}"
    )
    if days:
        text += ", departing on " + _name_list(days)
    if nights:
        text += ", on " + _name_list([f"{n}-night" for n in nights]) + " trips"
    return text + "."


def route_section(code, rows):
    guide = GUIDES.get(code)
    if not guide:
        return ""
    by_origin = {}
    for row in rows:
        by_origin.setdefault(row["from"], []).append(row)
    parts = ["<h2>Routes from Cork and Dublin</h2>"]
    for heading, paragraphs in guide["sections"]:
        parts.append(f"<h3>{html_lib.escape(heading)}</h3>")
        for para in paragraphs:
            text = _scan_paragraph(heading, by_origin.get(heading, [])) if para == "SCAN" else para
            parts.append(f"<p>{html_lib.escape(text, quote=False)}</p>")
    parts.append("<h3>Weekend or one week</h3>")
    parts.append(f"<p>{html_lib.escape(TRIP_PARAGRAPH)}</p>")
    return "\n".join(parts)


def page_html(code, slug, city, country, blurb, rows, updated, fare_counts):
    prices = [r["price"] for r in rows if r["price"]]
    min_p = min(prices) if prices else None
    airlines = sorted({r["airline"] for r in rows if r["airline"] != "—"})
    hook = HOOKS.get(code, country)
    hook_sentence = hook[:1].upper() + hook[1:]
    title = f"{city} flights from Cork & Dublin | {hook_sentence} | Holiday Chasers"
    guide = GUIDES.get(code)
    h1 = f"Cheap flights to {city} from Cork & Dublin"
    if guide:
        title = guide["title"]
        h1 = guide["h1"]
    if min_p:
        desc = (
            f"Direct {city} flights from Cork and Dublin, from €{min_p} return "
            f"per person. {hook_sentence}. Weekend and one-week trips from real scanned fares."
        )
    else:
        info = refresh_deals.coverage(code)
        flying = [o for o in info["origins"] if o["queryable"] and o["days"]]
        nxts = sorted((o for o in info["origins"] if o["next"]), key=lambda o: o["next"])
        if flying:
            desc = (
                f"{city} flights from Cork and Dublin. No fare in the latest scan. "
                f"{flying[0]['name']} flies on {flying[0]['days']}. No price is estimated."
            )
        elif nxts:
            origin = nxts[0]
            desc = (
                f"{city} flights from Cork and Dublin. No direct flights in this "
                f"scan, through {fmt_date_year(info['window_end'].isoformat())}. "
                f"Next scheduled: {origin['name']} {fmt_date_year(origin['next'].isoformat())}."
            )
        else:
            desc = (
                f"{city} flights from Cork and Dublin. No direct fare in the latest "
                f"scan, and the schedule we use has no restart date."
            )
    if guide:
        if min_p:
            desc = (
                f"{guide['lead']}. From €{min_p} return per person. "
                f"{hook_sentence}. Weekend and one-week trips from real scanned fares."
            )
        else:
            desc = desc.replace(f"{city} flights from Cork and Dublin", guide["lead"], 1)
    desc = desc if len(desc) <= 160 else _clip(desc, 160)

    fare_rows = "\n".join(
        f"<tr><td>{r['from']}</td><td>{r['kind']}</td>"
        f"<td>{fmt_date(r['dep'])} → {fmt_date(r['ret'])}"
        + (f" · {r['nights']}n" if r["nights"] else "") + "</td>"
        f"<td class='p'>€{r['price']}" + (" 💡" if r["saver"] else "") + "</td>"
        f"<td>{html_lib.escape(r['airline'])}</td></tr>"
        for r in rows) or (
            "<tr><td colspan='5'>No direct fare in the latest scan.</td></tr>"
        )

    related = related_destinations(code, fare_counts)
    related_html = " · ".join(
        '<a href="/destinations/{slug}.html">{name}</a>'.format(
            slug=html_lib.escape(CITIES[k][0], quote=True),
            name=html_lib.escape(CITIES[k][1]),
        )
        for k in related
    )
    gap = empty_copy(code, city, updated)
    if min_p:
        lead = (
            f"Direct returns from <b>€{min_p} per person</b> on our latest scan. "
            f"We scan real fares for weekend breaks and one-week holidays to {city}."
        )
        note = (
            f"Direct flights only · prices per person, return · last scanned {updated} "
            f"· 💡 = midweek saver"
        )
        related_heading = "More destinations"
        cta_label = f"Open the {city} deal — live prices, hotels &amp; costs →"
        faq = [
            (f"How much are flights to {city} from Ireland right now?",
             f"The cheapest direct return we found on our latest scan is €{min_p} per person. "
             "Prices refresh automatically every few days."),
            (f"Which airlines fly direct to {city} from Cork or Dublin?",
             (", ".join(airlines) if airlines else "The airlines in the table")
             + " operate the direct routes on this scan."),
            (f"What's the best way to find cheap dates for {city}?",
             "Open the trip planner on our homepage — it uses the same scanned fares "
             "and builds the trip around the date you pick."),
        ]
    else:
        lead = gap
        note = f"Direct flights only · prices per person, return · last scanned {updated}"
        related_heading = "Destinations with fares right now"
        cta_label = "See Cork &amp; Dublin deals that are on the board →"
        faq = [
            (f"How much are flights to {city} from Ireland right now?",
             gap),
            (f"Which airlines fly direct to {city} from Cork or Dublin?",
             "None are in the latest scan, so this page doesn't name a carrier or a price."),
            (f"Where can I see a fare while {city} has none?",
             "The destinations linked below have direct returns in the latest scan. "
             "The homepage board is the same data."),
        ]
    if guide:
        if guide.get("airline_answer"):
            faq[1] = (faq[1][0], guide["airline_answer"])
        faq.extend(guide.get("faqs") or [])
    faq_html = "\n".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in faq]})
    # data-hc-* is read by consent.js after consent. This is the page's only
    # booking-funnel link. With a stored fare, /?dest= opens that deal. With
    # none, the same hook points at the homepage board instead of a deal that
    # is not there.
    cta_href = ("/?dest=" + html_lib.escape(code, quote=True)) if rows else "/"
    cta_html = (
        '<a class="cta" href="{href}"'
        ' data-hc-event="flight_click"'
        ' data-hc-destination="{city}"'
        ' data-hc-dest="{code}"'
        ' data-hc-source="destination_page">{label}</a>'
    ).format(
        href=cta_href,
        code=html_lib.escape(code, quote=True),
        city=html_lib.escape(city, quote=True),
        label=cta_label,
    )
    routes_html = route_section(code, rows)
    routes_block = f'\n<div class="routes">\n{routes_html}\n</div>\n' if routes_html else ""
    h1_html = html_lib.escape(h1)
    title = html_lib.escape(title)
    desc = html_lib.escape(desc, quote=True)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{SITE}/destinations/{slug}.html">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}/destinations/{slug}.html">
<script type="application/ld+json">{faq_ld}</script>
<style>
:root{{--ink:#0A1B2E;--ivory:#FBF7EF;--gold:#C9A24B;--muted:#6B7280;--line:#E7E2D6;--cream:#F4EFE3}}
*{{box-sizing:border-box;margin:0}}body{{font-family:Georgia,'Times New Roman',serif;background:var(--ivory);color:var(--ink);line-height:1.6}}
header{{background:var(--ink);color:var(--ivory);padding:14px 20px;display:flex;justify-content:space-between;align-items:center}}
header a{{color:var(--ivory);text-decoration:none;font-weight:700}}
main{{max-width:820px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:30px;line-height:1.2;margin-bottom:10px}}
.sub{{color:var(--muted);font-size:15px;margin-bottom:22px}}
.cta{{display:inline-block;background:var(--ink);color:var(--ivory);padding:13px 22px;border-radius:10px;text-decoration:none;font-weight:700;margin:8px 0 26px}}
.table-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;min-width:640px;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:14px}}
th{{text-align:left;background:var(--cream);padding:10px 12px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
td{{padding:10px 12px;border-top:1px solid var(--line)}}td.p{{font-weight:800}}
h2{{font-size:20px;margin:34px 0 10px}}
h3{{font-size:16px;margin:16px 0 4px}}
.routes p{{margin:0 0 10px}}
details{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:8px 0}}
summary{{font-weight:700;cursor:pointer}}
details p{{margin-top:8px;color:var(--muted);font-size:14px}}
footer{{text-align:center;color:var(--muted);font-size:12px;padding:24px}}
footer a.ext{{color:var(--ink);font-weight:600;border-bottom:1px solid var(--gold);text-decoration:none}}
.rel{{font-size:14px}}.rel a{{color:var(--gold);font-weight:700;text-decoration:none}}
.note{{font-size:12px;color:var(--muted);margin-top:8px}}
.consent-bar{{position:fixed;left:0;right:0;bottom:0;z-index:900;background:var(--ink);color:var(--ivory);padding:14px 20px;display:none;align-items:center;gap:16px;flex-wrap:wrap;box-shadow:0 -8px 30px rgba(10,27,46,.35);font-family:system-ui,sans-serif}}
.consent-bar.show{{display:flex}}
.consent-txt{{flex:1;font-size:13px;line-height:1.5;min-width:220px}}
.consent-txt b{{color:#E4D2A0}}
.consent-btns{{display:flex;gap:10px}}
.consent-btn{{padding:9px 18px;border-radius:100px;font-size:13px;font-weight:700;cursor:pointer;border:none;font-family:inherit}}
.consent-accept{{background:var(--gold);color:var(--ink)}}
.consent-decline{{background:transparent;color:var(--ivory);border:1px solid rgba(251,248,241,.35)}}
</style>
</head>
<body>
<header><a href="/">Holiday Chasers</a><span style="font-size:12px;color:#c8d0da">Cork &amp; Dublin flight deals</span></header>
<main>
<h1>{h1_html}</h1>
<p class="sub">{blurb}</p>
<p>{lead}</p>
{cta_html}
{routes_block}
<h2>Every scanned date for {city}</h2>
<div class="table-wrap">
<table>
<thead><tr><th>From</th><th>Trip</th><th>Dates</th><th>Per person</th><th>Airline</th></tr></thead>
<tbody>
{fare_rows}
</tbody>
</table>
</div>
<p class="note">{note}</p>

<h2>Good to know</h2>
{faq_html}

<h2>{related_heading}</h2>
<p class="rel">{related_html} · <a href="/">all deals →</a></p>
</main>
<footer>© Holiday Chasers Ireland · <a href="/" style="color:var(--muted)">holidaychasers.ie</a> · <a href="/how-it-works.html" style="color:var(--muted)">How it works</a> · <a href="/about.html" style="color:var(--muted)">About</a> · <a href="/contact.html" style="color:var(--muted)">Contact</a> · <a class="ext" href="https://www.facebook.com/holidaychasersie" rel="noopener" target="_blank">Facebook</a> · <a class="ext" href="https://www.instagram.com/holidaychasers.ie/" rel="noopener" target="_blank">Instagram</a></footer>
<div class="consent-bar" id="consentBar">
  <div class="consent-txt"><b>Quick one:</b> we use anonymous analytics to see which deals people love, so we can find better ones. No ads, no selling data.</div>
  <div class="consent-btns">
    <button class="consent-btn consent-decline" onclick="hcConsent(false)">No thanks</button>
    <button class="consent-btn consent-accept" onclick="hcConsent(true)">That's fine</button>
  </div>
</div>
<script src="/consent.js" defer></script>
</body>
</html>"""


FOOTER_START = "<!-- hc-footer-cities -->"
FOOTER_END = "<!-- /hc-footer-cities -->"


def city_links():
    """Alphabetical homepage/404 links for every destination page."""
    rows = sorted(CITIES.values(), key=lambda item: item[1].casefold())
    return " · ".join(
        '<a href="/destinations/{slug}.html">{name}</a>'.format(
            slug=html_lib.escape(slug, quote=True),
            name=html_lib.escape(name),
        )
        for slug, name, _country, _blurb in rows
    )


def update_homepage_footer():
    """Rewrite the marked city list in index.html from CITIES."""
    path = "index.html"
    if not os.path.exists(path):
        print("  skip homepage footer: index.html missing")
        return
    with open(path, encoding="utf-8") as f:
        doc = f.read()
    if FOOTER_START not in doc or FOOTER_END not in doc:
        print("  skip homepage footer: city-list markers missing")
        return
    pattern = re.compile(re.escape(FOOTER_START) + r".*?" + re.escape(FOOTER_END), re.DOTALL)
    replacement = FOOTER_START + "\n    " + city_links() + "\n    " + FOOTER_END
    new, count = pattern.subn(replacement, doc, count=1)
    if count != 1:
        print("  skip homepage footer: could not replace city list")
        return
    if new != doc:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"  updated homepage footer ({len(CITIES)} cities)")
    else:
        print("  homepage footer already current")


def popular_routes_html():
    cards = []
    for slug, name, label, note in POPULAR_ROUTES:
        cards.append(
            '<a href="/destinations/{slug}">'
            '<span class="pr-kicker">{name}</span>'
            '<strong>{label}</strong>'
            '<span>{note}</span></a>'.format(
                slug=html_lib.escape(slug, quote=True),
                name=html_lib.escape(name),
                label=html_lib.escape(label),
                note=html_lib.escape(note),
            )
        )
    inner = (
        '<section class="popular-routes" aria-label="Popular routes">\n'
        '  <h2>Popular routes</h2>\n'
        '  <p>Direct flights from Cork and Dublin. Each page has the routes we '
        'scan and the fares from the latest check.</p>\n'
        '  <div class="popular-grid">\n    '
        + "\n    ".join(cards)
        + "\n  </div>\n</section>"
    )
    return POPULAR_START + "\n" + inner + "\n" + POPULAR_END


def update_popular_routes():
    """Insert or refresh the homepage popular-routes block. A deal refresh
    rewrites destination pages, so this block has to live in the generator."""
    path = "index.html"
    if not os.path.exists(path):
        print("  skip popular routes: index.html missing")
        return
    with open(path, encoding="utf-8") as f:
        doc = f.read()
    block = popular_routes_html()
    if POPULAR_START in doc and POPULAR_END in doc:
        pattern = re.compile(re.escape(POPULAR_START) + r".*?" + re.escape(POPULAR_END), re.DOTALL)
        new, count = pattern.subn(block, doc, count=1)
        if count != 1:
            print("  skip popular routes: could not replace the block")
            return
    else:
        anchor = "<!-- ═══ TABS ═══ -->"
        if anchor not in doc:
            print("  skip popular routes: no insertion point in index.html")
            return
        new = doc.replace(anchor, block + "\n\n" + anchor, 1)
    if new != doc:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"  updated homepage popular routes ({len(POPULAR_ROUTES)} links)")
    else:
        print("  homepage popular routes already current")


def write_404():
    """Branded 404. Known /destinations/{slug}/ URLs redirect to the real page."""
    slugs = json.dumps(sorted(item[0] for item in CITIES.values()))
    links = city_links()
    page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page not found | Holiday Chasers</title>
<meta name="robots" content="noindex">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
<script>
(function () {
  var slugs = __SLUGS__;
  var path = location.pathname || "";
  var match = path.match(/^\\/destinations\\/([a-z0-9-]+)(?:\\.html)?\\/+$/);
  if (!match) return;
  var slug = match[1];
  for (var i = 0; i < slugs.length; i++) {
    if (slugs[i] === slug) {
      location.replace("/destinations/" + slug + ".html" + location.search + location.hash);
      return;
    }
  }
})();
</script>
<style>
:root{--ink:#0A1B2E;--ivory:#FBF7EF;--gold:#C9A24B;--muted:#6B7280;--line:#E7E2D6;--cream:#F4EFE3}
*{box-sizing:border-box;margin:0}body{font-family:Georgia,'Times New Roman',serif;background:var(--ivory);color:var(--ink);line-height:1.6}
header{background:var(--ink);color:var(--ivory);padding:14px 20px;display:flex;justify-content:space-between;align-items:center}
header a{color:var(--ivory);text-decoration:none;font-weight:700}
main{max-width:820px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:30px;line-height:1.2;margin-bottom:10px}
.sub{color:var(--muted);font-size:15px;margin-bottom:22px}
.cta{display:inline-block;background:var(--ink);color:var(--ivory);padding:13px 22px;border-radius:10px;text-decoration:none;font-weight:700;margin:8px 0 26px}
h2{font-size:20px;margin:34px 0 10px}
footer{text-align:center;color:var(--muted);font-size:12px;padding:24px}
footer a.ext{color:var(--ink);font-weight:600;border-bottom:1px solid var(--gold);text-decoration:none}
.rel{font-size:14px;line-height:2}.rel a{color:var(--gold);font-weight:700;text-decoration:none}
</style>
</head>
<body>
<header><a href="/">Holiday Chasers</a><span style="font-size:12px;color:#c8d0da">Cork &amp; Dublin flight deals</span></header>
<main>
<h1>Page not found</h1>
<p class="sub">That address isn't on Holiday Chasers. The link may be out of date, or the page never existed.</p>
<a class="cta" href="/">Back to today's deals</a>
<h2>All destinations</h2>
<p class="rel">__LINKS__</p>
</main>
<footer>© Holiday Chasers Ireland · <a href="/" style="color:var(--muted)">holidaychasers.ie</a> · <a class="ext" href="https://www.facebook.com/holidaychasersie" rel="noopener" target="_blank">Facebook</a> · <a class="ext" href="https://www.instagram.com/holidaychasers.ie/" rel="noopener" target="_blank">Instagram</a></footer>
</body>
</html>
"""
    page = page.replace("__SLUGS__", slugs).replace("__LINKS__", links)
    with open("404.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote 404.html ({len(CITIES)} destination redirects)")


def main():
    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)
    updated_iso = (cache.get("updated_utc") or "")[:10] or dt.date.today().isoformat()
    updated = fmt_date(updated_iso)

    os.makedirs(OUT_DIR, exist_ok=True)
    collected = []
    for code, (slug, city, country, blurb) in CITIES.items():
        collected.append((code, slug, city, country, blurb, collect_fares(cache, code)))
    fare_counts = {code: len(rows) for code, _slug, _city, _country, _blurb, rows in collected}
    urls = []
    for code, slug, city, country, blurb, rows in collected:
        html = page_html(code, slug, city, country, blurb, rows, updated, fare_counts)
        with open(os.path.join(OUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        urls.append(f"{SITE}/destinations/{slug}.html")
        print(f"  wrote {slug}.html ({len(rows)} fares)")

    # sitemap: homepage + info pages + destination pages
    lastmod = updated_iso
    entries = [f"  <url><loc>{SITE}/</loc><changefreq>daily</changefreq>"
               f"<priority>1.0</priority><lastmod>{lastmod}</lastmod></url>"]
    entries += [f"  <url><loc>{SITE}/{name}</loc><changefreq>monthly</changefreq>"
                f"<priority>0.4</priority><lastmod>{lastmod}</lastmod></url>"
                for name in INFO_PAGES]
    entries += [f"  <url><loc>{u}</loc><changefreq>weekly</changefreq>"
                f"<priority>0.8</priority><lastmod>{lastmod}</lastmod></url>"
                for u in urls]
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "\n".join(entries) + "\n</urlset>\n")
    print(f"wrote sitemap.xml ({1 + len(INFO_PAGES) + len(urls)} urls)")
    update_homepage_footer()
    update_popular_routes()
    write_404()


if __name__ == "__main__":
    main()
