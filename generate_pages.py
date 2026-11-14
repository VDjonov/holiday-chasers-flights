#!/usr/bin/env python3
"""
Holiday Chasers Ireland — SEO destination page generator.

Runs in the GitHub Action right after refresh_deals.py. Reads the fresh
deals_cache.json and writes:

  destinations/<slug>.html   one static, indexable page per destination
  sitemap.xml                homepage, info pages, and all destination pages
  index.html footer          destination links, same cities as these pages
  index.html popular routes  refreshed in place, inside the Popular routes tab
  404.html                   branded not-found page; trailing-slash redirects

Pages are rebuilt on every scan, so Google sees fresh fares every few days.
Zero API credits — everything renders from data already paid for.
"""

import html as html_lib
import json, os, re, subprocess, datetime as dt
from urllib.parse import urlencode, urlparse

import refresh_deals
import manual_fares

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
    "BVA": ("paris-beauvais", "Paris Beauvais", "France",
            "Paris from Beauvais: museums, the river and neighbourhood walks, with the airport well north of the city."),
    "MXP": ("milan-malpensa", "Milan Malpensa", "Italy",
            "Milan from Malpensa: the cathedral, the galleries and a walk in the centre."),
    "LUX": ("luxembourg", "Luxembourg", "Luxembourg",
            "A compact old town above a river valley, reached from Findel airport."),
    "BRU": ("brussels-airport", "Brussels Airport", "Belgium",
            "Brussels from the city airport at Zaventem: the Grand Place and the old centre."),
    "AGA": ("agadir", "Agadir", "Morocco",
            "A beach city on the Atlantic, with the bay and the seafront as the usual walk."),
    "FNC": ("funchal", "Funchal", "Portugal",
            "Madeira's capital: the harbour, the old town and gardens above the port."),
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
    "BVA": "Paris from Beauvais",
    "MXP": "Milan from Malpensa",
    "LUX": "old-town city breaks",
    "BRU": "city-airport breaks",
    "AGA": "Atlantic beach breaks",
    "FNC": "Madeira harbour breaks",
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
        "title": "Rhodes flights from Cork & Dublin | Holiday Chasers",
        "h1": "Flights to Rhodes from Cork and Dublin",
        "lead": "Flights to Rhodes from Cork and Dublin",
        "intro": (
            "This scan stored no Rhodes fare from Cork or from Dublin. It only prices "
            "through 30 January 2027. Ryanair lists Cork to Rhodes from May 2027 and "
            "Dublin to Rhodes from March 2027. No price is estimated for the gap."
        ),
        "desc": (
            "Flights to Rhodes from Cork and Dublin. No fare in this scan, through 30 Jan 2027. "
            "Ryanair lists Cork from May 2027 and Dublin from March 2027."
        ),
        "fare_answer": (
            "This scan stored no Rhodes fare from Cork or Dublin. It only prices through "
            "30 January 2027. Ryanair lists Cork to Rhodes from May 2027 and Dublin to "
            "Rhodes from March 2027. No price is estimated for the gap."
        ),
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
        "title": "Cork to Krakow flights | Fly direct from Dublin | Holiday Chasers",
        "h1": "Cork to Krakow flights: fly direct from Dublin",
        "lead": "Cork to Krakow flights: fly direct from Dublin",
        "desc": (
            "Cork to Krakow flights: no direct Cork route in this scan. "
            "Dublin to Krakow with Ryanair, from €{price} return per person."
        ),
        "intro": (
            "There is no direct flight from Cork to Krakow in this scan. Ryanair's "
            "route list does not include Cork to Krakow. The direct route is Dublin "
            "to Krakow with Ryanair, from €{price} per person on the latest scan."
        ),
        "price_answer": (
            "There is no direct Cork to Krakow fare in this scan. The cheapest "
            "Dublin to Krakow return it stored is €{price} per person, with Ryanair. "
            "Prices refresh automatically every few days."
        ),
        "airline_answer": (
            "Ryanair flies Dublin to Krakow, and that is the only direct route on "
            "this scan. Ryanair's route list does not include Cork to Krakow, so "
            "this page does not show a Cork fare."
        ),
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
             "No. There is no direct flight from Cork to Krakow in this scan, and Ryanair's route list does not include Cork to Krakow. The direct route is Dublin to Krakow with Ryanair."),
            ("Does Dublin fly to Krakow every day?",
             "Ryanair says the Dublin to Krakow flight runs every day, typically once a day and sometimes twice. The table shows the weekend and one-week dates the latest scan actually stored."),
        ],
    },
    "PSA": {
        "title": "Dublin to Pisa flights | No Cork fare in this scan | Holiday Chasers",
        "h1": "Dublin to Pisa flights",
        "lead": "Dublin to Pisa flights",
        "desc": (
            "Dublin to Pisa flights with Ryanair, from €{price} return per person. "
            "No Cork fare in this scan. Ryanair lists Cork to Pisa again from March 2027."
        ),
        "intro": (
            "The fares on this page are Dublin to Pisa with Ryanair, from €{price} "
            "per person on the latest scan. There is no direct Cork fare in this scan. "
            "Ryanair shows no Cork to Pisa flight from November 2026 through February 2027, "
            "and lists that route again from March 2027."
        ),
        "price_answer": (
            "The cheapest fare in this scan is a Dublin to Pisa return at €{price} "
            "per person, with Ryanair. There is no Cork fare stored."
        ),
        "airline_answer": (
            "Ryanair flies Dublin to Pisa, and those are the fares in the table. "
            "Ryanair also lists Cork to Pisa, but shows no fare from November 2026 "
            "through February 2027, and this scan stored none."
        ),
        "sections": [
            ("Cork", [
                "Ryanair's Cork to Pisa page shows no fare for November 2026 through February 2027. From March 2027 it lists flights on multiple days each week. Dates on the page include Friday 23 April 2027, Friday 21 May 2027, Monday 9 August 2027 and Friday 3 September 2027.",
                "The schedule this scan uses is Mondays and Fridays from 3 April 2026 to 23 October 2026, with nothing after that, so the scan stored no Cork fare.",
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
    "OPO": {
        "title": "Dublin to Porto flights | No Cork fare in this scan | Holiday Chasers",
        "h1": "Dublin to Porto flights",
        "lead": "Dublin to Porto flights",
        "desc": (
            "Dublin to Porto flights with Ryanair, from €{price} return per person. "
            "No Cork fare in this scan. Ryanair and Aer Lingus publish no Cork to Porto page."
        ),
        "intro": (
            "The fares on this page are Dublin to Porto. The cheapest return on the "
            "latest scan is €{price} per person. This scan does not price Cork to Porto, "
            "and neither Ryanair nor Aer Lingus publishes a Cork to Porto page."
        ),
        "price_answer": (
            "The cheapest Dublin to Porto return in this scan is €{price} per person, "
            "with Ryanair. No Cork fare is stored. No price is taken from an airline website."
        ),
        "airline_answer": (
            "Ryanair's Dublin to Porto page, checked 13 November 2026, lists a fare in "
            "every month from November 2026 through October 2027 and says the flight runs "
            "every day, with one departure each day. Aer Lingus has no Dublin to Porto page. "
            "Neither airline has a Cork to Porto page. The table shows the airline on the stored fares."
        ),
        "sections": [
            ("Cork", [
                "Ryanair and Aer Lingus have no Cork to Porto page. Checked 13 November 2026, both addresses returned no page. This scan does not price Cork to Porto, and no Cork fare is stored.",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Porto page, checked 13 November 2026, lists a fare in every month from November 2026 through October 2027 and says the flight runs every day, with one departure each day. Dates on that page include Sunday 29 November 2026, Sunday 6 December 2026, Friday 1 January 2027, Friday 19 February 2027 and Monday 15 March 2027. The weekday row on Ryanair's table is the same on every route, so it is not used as a timetable.",
                "Aer Lingus has no Dublin to Porto page.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Is there a direct flight from Cork to Porto?",
             "Not on the two airline sites checked. Ryanair and Aer Lingus have no Cork to Porto page, and this scan does not price Cork to Porto. The direct route on this page is Dublin to Porto with Ryanair."),
            ("Does Ryanair fly Dublin to Porto every day?",
             "Ryanair's Dublin to Porto page says the flight runs every day, with one departure each day, and lists a fare in every month from November 2026 through October 2027. The table is the weekend and one-week dates the latest scan stored."),
        ],
    },
    "ATH": {
        "title": "Dublin to Athens flights | No fare in this scan | Holiday Chasers",
        "h1": "Dublin to Athens flights",
        "lead": "Dublin to Athens flights",
        "desc": (
            "Dublin to Athens flights. No fare in this scan. Ryanair lists the route. "
            "Aer Lingus shows fares from March 2027. Neither airline has a Cork page."
        ),
        "intro": (
            "This scan stored no Athens fare from Dublin or from Cork, so no price is shown. "
            "Ryanair publishes Dublin to Athens. Aer Lingus shows no Dublin departure from "
            "November 2026 through February 2027 and lists fares from March 2027. "
            "Neither airline publishes a Cork to Athens page."
        ),
        "fare_answer": (
            "No Athens fare is in the current scan, from Dublin or from Cork. "
            "No price is estimated, and none is copied from an airline website."
        ),
        "airline_answer": (
            "Ryanair's Dublin to Athens page, checked 13 November 2026, lists a fare in "
            "every month from November 2026 through October 2027 and says the flight runs "
            "on most days of the month, with one departure on an operating day. "
            "Aer Lingus shows no Dublin departure from November 2026 through February 2027, "
            "lists fares from March 2027, and calls the flight direct at about 3 hours 50 minutes. "
            "Neither airline has a Cork to Athens page. The scan stored no fare, so the table names no carrier."
        ),
        "sections": [
            ("Cork", [
                "Ryanair and Aer Lingus have no Cork to Athens page. Checked 13 November 2026, both addresses returned no page. This scan does not price Cork to Athens.",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Athens page, checked 13 November 2026, lists a fare in every month from November 2026 through October 2027 and says the flight runs on most days of the month, with one departure on an operating day. Dates on that page include Monday 16 November 2026, Thursday 21 January 2027, Monday 22 February 2027, Monday 1 March 2027 and Monday 25 October 2027. The weekday row on Ryanair's table is the same on every route, so it is not used as a timetable.",
                "Aer Lingus's Dublin to Athens page shows no departure for November 2026 through February 2027 and lists fares from March 2027. The page calls it a direct flight of about 3 hours 50 minutes. Its fare note says displayed fares may include a connection, so a calendar price there is not treated as a direct seat. The page is not used as a daily timetable.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Is there a Cork to Athens flight?",
             "Ryanair and Aer Lingus have no Cork to Athens page. This scan does not price Cork to Athens, and it stored no Dublin fare either."),
            ("Why is there no Athens price?",
             "The latest scan stored no Athens return. Ryanair is selling Dublin to Athens, and Aer Lingus lists Dublin fares from March 2027, but this page shows a price only after a scan stores a real return."),
        ],
    },
    "EDI": {
        "title": "Edinburgh flights from Cork & Dublin | Short castle-city hops | Holiday Chasers",
        "h1": "Edinburgh flights from Cork and Dublin",
        "lead": "Edinburgh flights from Cork and Dublin",
        "airline_answer": (
            "Ryanair publishes both Cork to Edinburgh and Dublin to Edinburgh. "
            "Checked 13 November 2026, its Cork page says one departure a day and its Dublin page says four to five a day. "
            "Aer Lingus's Dublin page is headed as direct flights and says it offers multiple daily flights of about one hour. "
            "Aer Lingus's Cork page shows no fare from November 2026 through October 2027. "
            "The airlines in the table are the ones on the latest stored fares."
        ),
        "sections": [
            ("Cork", [
                "Ryanair's Cork to Edinburgh page, checked 13 November 2026, says the flight runs every day, with one departure each day, and lists a fare in every month from November 2026 through October 2027. Aer Lingus's Cork to Edinburgh page shows no fare for those same months.",
                "The published dates, and whether the stored Cork fares fit a weekend, are on the Cork to Edinburgh page.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Edinburgh page, checked 13 November 2026, says the flight runs every day, typically with four to five departures, and lists a fare in every month from November 2026 through October 2027. Aer Lingus's Dublin page is headed as direct flights and says it offers multiple daily flights of about one hour. Its fare note says displayed fares may include a connection.",
                "The published dates are on the Dublin to Edinburgh page.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Do both Cork and Dublin fly to Edinburgh?",
             "Ryanair publishes both. It says Cork has one departure a day and Dublin typically has four to five. Aer Lingus publishes multiple daily flights from Dublin and shows no Cork fare from November 2026 through October 2027."),
            ("Where are the single-airport pages?",
             "Cork to Edinburgh and Dublin to Edinburgh each have a page with that airport's fares only, and with a note on whether those dates fit a weekend or a week."),
        ],
    },
    "BCN": {
        "title": "Barcelona flights from Cork & Dublin | City, beach and Gaudí | Holiday Chasers",
        "h1": "Barcelona flights from Cork and Dublin",
        "lead": "Barcelona flights from Cork and Dublin",
        "airline_answer": (
            "Ryanair publishes both Cork to Barcelona and Dublin to Barcelona. "
            "Checked 13 November 2026, its Dublin page says the flight runs every day, typically three to four times, and its Cork page says several days each week. "
            "Aer Lingus's Dublin page says it operates direct flights at least twice a day. "
            "Aer Lingus's Cork page shows no fare from November 2026 through October 2027. "
            "The airlines in the table are the ones on the latest stored fares."
        ),
        "sections": [
            ("Cork", [
                "Ryanair's Cork to Barcelona page, checked 13 November 2026, says flights run on several days each week, with one departure on each operating day, and lists a fare in every month from November 2026 through October 2027. Aer Lingus's Cork to Barcelona page shows no fare for those months.",
                "The dates Ryanair publishes, and whether the stored Cork fares fit a weekend, are on the Cork to Barcelona page.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Barcelona page, checked 13 November 2026, says the flight runs every day, typically with three to four departures. Aer Lingus's Dublin page says it operates direct flights at least twice a day, about 2 hours 25 minutes, and warns that displayed fares may include a connection.",
                "The published dates are on the Dublin to Barcelona page.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Who flies to Barcelona from Cork and from Dublin?",
             "Ryanair publishes both airports. It says Dublin runs every day and Cork runs on several days each week. Aer Lingus says Dublin is direct, at least twice a day, and shows no Cork fare from November 2026 through October 2027. The table names whoever came back on the latest scan."),
            ("Where are the single-airport pages?",
             "Cork to Barcelona and Dublin to Barcelona each have a page with that airport's fares only. The Cork page is the one that says whether those stored dates can be a weekend."),
        ],
    },
    "FUE": {
        "title": "Fuerteventura flights from Cork & Dublin | Canary dune beaches | Holiday Chasers",
        "h1": "Fuerteventura flights from Cork and Dublin",
        "lead": "Fuerteventura flights from Cork and Dublin",
        "airline_answer": (
            "Ryanair publishes both Cork to Fuerteventura and Dublin to Fuerteventura. "
            "Checked 13 November 2026, its Cork page says a few flights each month and its Dublin page says most days, about five flights a week. "
            "Aer Lingus's Dublin page calls the flight direct, about 4 hours 20 minutes. "
            "Aer Lingus has no Cork to Fuerteventura page. "
            "The airlines in the table are the ones on the latest stored fares."
        ),
        "sections": [
            ("Cork", [
                "Ryanair's Cork to Fuerteventura page, checked 13 November 2026, says it operates a few flights each month, with one departure on each operating day, and lists a fare in every month from November 2026 through October 2027. Aer Lingus has no Cork to Fuerteventura page.",
                "Whether those stored Cork dates can be a weekend is answered on the Cork to Fuerteventura page. A weekend on this scan has to leave Thursday, Friday or Saturday.",
                "SCAN",
            ]),
            ("Dublin", [
                "Ryanair's Dublin to Fuerteventura page, checked 13 November 2026, says flights run on most days of the week, about five a week, with one departure on an operating day. Aer Lingus's Dublin page calls it a direct flight of about 4 hours 20 minutes and warns that displayed fares may include a connection.",
                "The published dates are on the Dublin to Fuerteventura page.",
                "SCAN",
            ]),
        ],
        "faqs": [
            ("Is Cork to Fuerteventura the same schedule as Dublin?",
             "No. Ryanair says Cork is a few flights each month and Dublin is most days, about five flights a week. Aer Lingus publishes a direct Dublin flight and has no Cork page. The stored dates are on each route page."),
            ("Where are the single-airport pages?",
             "Cork to Fuerteventura and Dublin to Fuerteventura each have a page with that airport's fares only, and with the weekend or one-week verdict for those dates."),
        ],
    },
}

# Airport-to-city facts checked 13 November 2026. No flight price is copied
# from these pages. A city is omitted when the official page did not yield
# a usable route, time or mode list.
TRANSPORT = {
    "TFS": (
        "Tenerife South Airport's own page lists Titsa buses. Line 40 runs Costa Adeje station, Los Cristianos and the airport. "
        "Line 10 runs Santa Cruz, Cruce Caletillas, Cruce San Isidro and the airport. "
        "Night line 711 runs Santa Cruz, the airport, Los Cristianos and Costa Adeje. "
        "Line 415 runs El Fraile, the airport and San Isidro. "
        "Line 343 runs direct between Tenerife Sur and Tenerife Norte with no stops, and the airport says that ride takes 50 minutes. "
        "This page does not copy the Titsa timetable."
    ),
    "FUE": (
        "Fuerteventura Airport's own page lists Tiadhe buses. "
        "Line 3 connects the airport with Puerto del Rosario, Caleta de Fuste and Las Salinas. "
        "Line 10 connects the airport with Puerto del Rosario and Morro Jable. "
        "Line 16 connects the airport with Puerto del Rosario and Gran Tarajal. "
        "This page does not copy the Tiadhe timetable."
    ),
    "ATH": (
        "Athens International Airport says Metro Line 3, the blue line, connects the airport with Athens city centre and with Piraeus, at Dimotiko Theatro. "
        "The same page estimates 60 minutes by that metro to Piraeus station, and 65 minutes to Piraeus by suburban railway. "
        "The suburban railway also connects the airport with Larissis station. "
        "Express buses on the airport's page are X95 to Syntagma, X96 to Piraeus, X93 to the Kifissos and Liosion intercity bus stations, and X97 to Elliniko. "
        "The airport estimates 90 minutes on the X96 to Piraeus. It does not give a minute count for the metro into the centre, so none is stated here."
    ),
    "OPO": (
        "Metro do Porto's own FAQ puts the airport at Aeroporto, zone N10, and Trindade at zone C1. "
        "It says the trip from Aeroporto to Trindade crosses four zones, so the Andante title for that ride is a Z4. "
        "Andante is the card for the metro, for STCP buses and for CP urban trains. "
        "The FAQ does not give a journey time, so none is stated here."
    ),
    "EDI": (
        "Edinburgh Airport's getting-there page lists bus, tram, taxi, train and car. "
        "That page does not publish a journey time, so none is stated here."
    ),
    "PSA": (
        "PisaMover, the shuttle operator, says it connects Galileo Galilei Airport with Pisa Centrale station, calling at an intermediate stop on the way. "
        "It runs every day from 6:00 to midnight, and until 1:00 from 1 June to 30 September. "
        "The operator says the ride between the airport and Pisa Centrale takes about 5 minutes, including that stop."
    ),
    "BVA": (
        "Paris-Beauvais Airport is well north of Paris. "
        "Check the airport's own site for the ride into the city. "
        "This page does not quote a timetable or a fare."
    ),
    "MXP": (
        "Milan Malpensa is north-west of the city. "
        "Check the airport's own site for the ride into Milan. "
        "This page does not quote a timetable or a fare."
    ),
    "LUX": (
        "Luxembourg Airport is east of the city, at Findel. "
        "Check the airport's own site for the ride into town. "
        "This page does not quote a timetable or a fare."
    ),
    "BRU": (
        "Brussels Airport is at Zaventem, north-east of the city centre. "
        "Check the airport's own site for the ride into town. "
        "This page does not quote a timetable or a fare."
    ),
    "AGA": (
        "Agadir Al Massira Airport is south of the city, inland from the bay. "
        "Check the airport's own site for the ride into town. "
        "This page does not quote a timetable or a fare."
    ),
    "FNC": (
        "Funchal Airport is east of the city, on the hillside above the coast. "
        "Check the airport's own site for the ride into town. "
        "This page does not quote a timetable or a fare."
    ),
}

# What the city is, in generic terms. No prices, no timetables.
PLACE_NOTES = {
    "BVA": (
        "Most trips through Beauvais are for Paris: museums, the river and a neighbourhood walk. "
        "Beauvais itself is the town beside the airport."
    ),
    "MXP": (
        "Milan's usual city break is the cathedral, the shopping galleries and a walk in the centre. "
        "The lakes are a separate day out from the city."
    ),
    "LUX": (
        "Luxembourg's old town sits above the river valley. "
        "The usual walk is the old streets and the view over the gorge."
    ),
    "BRU": (
        "This page is Brussels Airport at Zaventem, the airport beside the city. "
        "The usual centre is the Grand Place and the streets and galleries around it."
    ),
    "AGA": (
        "Agadir is a beach city on Morocco's Atlantic coast. "
        "The seafront and the bay are the usual reason for the trip."
    ),
    "FNC": (
        "Funchal is the capital of Madeira. "
        "The harbour, the old town and the gardens above the port are the usual walk."
    ),
}

# One page per origin, only where that airline page exists and the scan prices
# the origin, and where Cork and Dublin are different enough that the combined
# destination page cannot say it. Paragraphs are the airline site, checked
# 13 November 2026. Scan days and prices are filled in at build time.
ROUTES = (
    {
        "slug": "cork-to-edinburgh",
        "code": "EDI",
        "origin": "Cork",
        "title": "Cork to Edinburgh flights | Holiday Chasers",
        "h1": "Cork to Edinburgh flights",
        "link": "Cork to Edinburgh",
        "paragraphs": [
            "Ryanair's Cork to Edinburgh page, checked 13 November 2026, says the flight runs every day, with one departure each day, and lists a fare in every month from November 2026 through October 2027. Dates on that page include Saturday 28 November 2026, Saturday 5 December 2026, Saturday 30 January 2027, Saturday 20 February 2027 and Sunday 7 March 2027. The weekday row on Ryanair's table is the same on every route, so it is not used as a timetable.",
            "Aer Lingus's Cork to Edinburgh page shows no fare for November 2026 through October 2027. This page does not treat that as a second carrier.",
        ],
        "faqs": [
            ("Does Ryanair fly from Cork to Edinburgh every day?",
             "Ryanair's Cork to Edinburgh page says the flight runs every day, with one departure each day, and lists a fare in every month from November 2026 through October 2027."),
            ("Does Aer Lingus fly from Cork to Edinburgh?",
             "Aer Lingus's Cork to Edinburgh page shows no fare for November 2026 through October 2027. The latest scan's carrier is whoever is named on the stored fares below."),
        ],
    },
    {
        "slug": "dublin-to-edinburgh",
        "code": "EDI",
        "origin": "Dublin",
        "title": "Dublin to Edinburgh flights | Holiday Chasers",
        "h1": "Dublin to Edinburgh flights",
        "link": "Dublin to Edinburgh",
        "paragraphs": [
            "Ryanair's Dublin to Edinburgh page, checked 13 November 2026, says the flight runs every day, typically with four to five departures, and lists a fare in every month from November 2026 through October 2027. Dates on that page include Monday 30 November 2026, Wednesday 16 December 2026, Wednesday 27 January 2027, Saturday 20 February 2027 and Tuesday 2 March 2027.",
            "Aer Lingus's Dublin to Edinburgh page is headed as direct flights and says it offers multiple daily flights, with a flight time of about one hour. Its fare note says displayed fares may include a connection, so a calendar price on that page is not treated here as proof of a direct seat. No Aer Lingus price is copied onto this page.",
        ],
        "faqs": [
            ("How often does Dublin fly to Edinburgh?",
             "Ryanair says every day, typically four to five departures. Aer Lingus's page is headed as direct flights and says multiple daily flights of about one hour. The table is only the returns the latest scan stored."),
            ("Is the Aer Lingus Dublin to Edinburgh flight direct?",
             "Aer Lingus heads the page as direct flights and gives a flight time of about one hour. The same page warns that displayed fares may include a connection. This scan's table names the airline on each stored fare."),
        ],
    },
    {
        "slug": "cork-to-barcelona",
        "code": "BCN",
        "origin": "Cork",
        "title": "Cork to Barcelona flights | Holiday Chasers",
        "h1": "Cork to Barcelona flights",
        "link": "Cork to Barcelona",
        "paragraphs": [
            "Ryanair's Cork to Barcelona page, checked 13 November 2026, says flights run on several days each week, with one departure on each operating day, and lists a fare in every month from November 2026 through October 2027. Dates published on that page include Monday 30 November 2026, Monday 14 December 2026, Monday 25 January 2027, Monday 1 February 2027 and Monday 1 March 2027. Those Mondays are the dates the page shows, not a claim that Monday is the only day.",
            "Aer Lingus's Cork to Barcelona page shows no fare for November 2026 through October 2027.",
        ],
        "faqs": [
            ("Does Cork fly to Barcelona every day?",
             "Ryanair does not say every day. Its Cork to Barcelona page says several days each week, with one departure on each operating day. The dates it publishes on the page include five Mondays from November 2026 to March 2027."),
            ("Does Aer Lingus fly from Cork to Barcelona?",
             "Aer Lingus's Cork to Barcelona page shows no fare for November 2026 through October 2027."),
        ],
    },
    {
        "slug": "dublin-to-barcelona",
        "code": "BCN",
        "origin": "Dublin",
        "title": "Dublin to Barcelona flights | Holiday Chasers",
        "h1": "Dublin to Barcelona flights",
        "link": "Dublin to Barcelona",
        "paragraphs": [
            "Ryanair's Dublin to Barcelona page, checked 13 November 2026, says the flight runs every day, typically with three to four departures, and lists a fare in every month from November 2026 through October 2027. Dates on that page include Sunday 29 November 2026, Thursday 3 December 2026, Monday 11 January 2027, Wednesday 3 February 2027 and Wednesday 3 March 2027.",
            "Aer Lingus's Dublin to Barcelona page says it operates direct flights at least twice a day, and that the direct flight takes around 2 hours 25 minutes. Its fare note says displayed fares may include a connection. No Aer Lingus price is copied onto this page.",
        ],
        "faqs": [
            ("How often does Dublin fly to Barcelona?",
             "Ryanair says every day, typically three to four departures. Aer Lingus says direct flights at least twice a day, about 2 hours 25 minutes, and warns that displayed fares may include a connection."),
            ("Which airline is in the Dublin to Barcelona table?",
             "Only the airline on each stored fare. Ryanair and Aer Lingus both publish the route. A carrier appears in the table when the latest scan stored a return with that airline."),
        ],
    },
    {
        "slug": "cork-to-fuerteventura",
        "code": "FUE",
        "origin": "Cork",
        "title": "Cork to Fuerteventura flights | Holiday Chasers",
        "h1": "Cork to Fuerteventura flights",
        "link": "Cork to Fuerteventura",
        "paragraphs": [
            "Ryanair's Cork to Fuerteventura page, checked 13 November 2026, says it operates a few flights each month, with one departure on each operating day, and lists a fare in every month from November 2026 through October 2027. Dates on that page include Wednesday 25 November 2026, Sunday 13 December 2026, Sunday 24 January 2027, Wednesday 3 February 2027 and Sunday 7 March 2027. The page also says a typical departure time that does not match those published times, so no clock time is repeated here.",
            "Aer Lingus has no Cork to Fuerteventura page.",
        ],
        "faqs": [
            ("How often does Cork fly to Fuerteventura?",
             "Ryanair says a few flights each month, with one departure on each operating day. It lists a fare in every month from November 2026 through October 2027. Aer Lingus has no Cork to Fuerteventura page."),
            ("Can I do a weekend from Cork to Fuerteventura on this scan?",
             "Only if the stored departure is a Thursday, Friday or Saturday. A weekend here is 2 or 3 nights on one of those days. The paragraph above the table says whether the latest Cork fares are that shape or a one-week trip."),
        ],
    },
    {
        "slug": "dublin-to-fuerteventura",
        "code": "FUE",
        "origin": "Dublin",
        "title": "Dublin to Fuerteventura flights | Holiday Chasers",
        "h1": "Dublin to Fuerteventura flights",
        "link": "Dublin to Fuerteventura",
        "paragraphs": [
            "Ryanair's Dublin to Fuerteventura page, checked 13 November 2026, says flights run on most days of the week, typically one flight on an operating day, about five flights a week. It lists a fare in every month from November 2026 through October 2027. Dates on that page include Tuesday 17 November 2026, Wednesday 2 December 2026, Monday 4 January 2027, Sunday 21 February 2027 and Tuesday 2 March 2027.",
            "Aer Lingus's Dublin to Fuerteventura page calls it a direct flight of about 4 hours 20 minutes. The November 2026 calendar on that page shows fares on Saturday 14, 21 and 28 November 2026. The month list shows fares for November 2026, December 2026, January 2027 and March 2027, and no result for February 2027 or for April 2027 through October 2027. Its fare note says displayed fares may include a connection. No Aer Lingus price is copied onto this page.",
        ],
        "faqs": [
            ("How often does Dublin fly to Fuerteventura?",
             "Ryanair says most days of the week, about five flights a week, one departure on an operating day. Aer Lingus calls its Dublin flight direct, about 4 hours 20 minutes, and shows Saturday fares on 14, 21 and 28 November 2026."),
            ("Is a Dublin to Fuerteventura weekend in this scan?",
             "A weekend here leaves Thursday, Friday or Saturday for 2 or 3 nights. The paragraph above the table says which of those the latest Dublin fares actually are."),
        ],
    },
)

# Title head is what sits before " | Holiday Chasers" (19 characters).
# Heads are kept at 41 characters or fewer so the full title is about 60.
# H1s follow the Search Console wording and stay honest when Cork is not the fare.
SEARCH = {
    "RHO": ("Rhodes flights from Cork & Dublin", "Flights to Rhodes from Cork and Dublin"),
    "PSA": ("Dublin to Pisa flights", "Dublin to Pisa flights"),
    "BER": ("Cork to Berlin | Dublin fares", "Flights to Berlin from Cork: Dublin fares in this scan"),
    "FAO": ("Flights to Faro from Cork", "Flights to Faro from Cork and Dublin"),
    "VCE": ("Dublin to Venice flights", "Dublin to Venice flights"),
    "MAD": ("Dublin to Madrid flights", "Dublin to Madrid flights"),
    "KRK": ("Cork to Krakow | From Dublin", "Cork to Krakow flights: fly direct from Dublin"),
    "BUD": ("Cork to Budapest | Dublin fares", "Flights to Budapest from Cork: Dublin fares in this scan"),
    "CPH": ("Cork to Copenhagen | Dublin", "Cork to Copenhagen flights: Dublin fares in this scan"),
    "MLA": ("Malta from Cork | Dublin fares", "Flights to Malta from Cork: Dublin fares in this scan"),
    "OPO": ("Cork to Porto | Dublin only", "Cork to Porto flights: fly from Dublin"),
    "FUE": ("Fuerteventura from Cork", "Flights to Fuerteventura from Cork"),
    "AGP": ("Malaga flights from Cork", "Flights to Malaga from Cork"),
    "LIS": ("Cork to Lisbon | Dublin fares", "Cork to Lisbon flights: Dublin fares in this scan"),
    "SVQ": ("Cork to Seville flights", "Cork to Seville flights"),
    "ATH": ("Dublin to Athens flights", "Dublin to Athens flights"),
    "ALC": ("Dublin to Alicante flights", "Dublin to Alicante flights"),
    "FCO": ("Dublin to Rome flights", "Dublin to Rome flights"),
    "NCE": ("Nice from Cork | Dublin fares", "Flights to Nice from Cork: Dublin fares in this scan"),
    "ZAD": ("Dublin to Zadar flights", "Dublin to Zadar flights"),
    "TFS": ("Tenerife flights from Cork", "Flights to Tenerife from Cork"),
    "PMI": ("Palma flights from Cork & Dublin", "Flights to Palma from Cork and Dublin"),
    "ACE": ("Lanzarote flights from Cork", "Flights to Lanzarote from Cork"),
    "BCN": ("Cork to Barcelona flights", "Cork to Barcelona flights"),
    "EDI": ("Edinburgh flights from Cork", "Edinburgh flights from Cork"),
    "AMS": ("Amsterdam flights from Cork", "Amsterdam flights from Cork"),
    "CDG": ("Paris flights from Cork", "Paris flights from Cork"),
    "PRG": ("Prague flights from Cork", "Prague flights from Cork"),
    "MUC": ("Munich flights from Cork", "Munich flights from Cork"),
    "LPA": ("Las Palmas flights from Cork", "Flights to Las Palmas from Cork and Dublin"),
    "BVA": ("Paris Beauvais from Cork & Dublin", "Flights to Paris Beauvais from Cork and Dublin"),
    "MXP": ("Dublin to Milan Malpensa", "Dublin to Milan Malpensa flights"),
    "LUX": ("Dublin to Luxembourg flights", "Dublin to Luxembourg flights"),
    "BRU": ("Dublin to Brussels Airport", "Dublin to Brussels Airport flights"),
    "AGA": ("Dublin to Agadir flights", "Dublin to Agadir flights"),
    "FNC": ("Dublin to Funchal flights", "Dublin to Funchal flights"),
    "VLC": ("Cork to Valencia | Dublin fares", "Flights to Valencia from Cork: Dublin fares in this scan"),
    "ZRH": ("Cork to Zurich | Dublin fares", "Cork to Zurich flights: Dublin fares in this scan"),
    "BGY": ("Milan flights from Dublin", "Milan flights from Dublin"),
    "WMI": ("Cork to Warsaw | Dublin fares", "Cork to Warsaw flights: Dublin fares in this scan"),
    "VIE": ("Cork to Vienna | Dublin fares", "Flights to Vienna from Cork: Dublin fares in this scan"),
    "STN": ("London flights from Cork", "London flights from Cork"),
    "MAN": ("Manchester flights from Cork", "Manchester flights from Cork"),
    "GVA": ("Geneva flights from Cork", "Geneva flights from Cork"),
    "BHX": ("Cork to Birmingham flights", "Cork to Birmingham flights"),
    "BRS": ("Cork to Bristol flights", "Cork to Bristol flights"),
    "LPL": ("Cork to Liverpool flights", "Cork to Liverpool flights"),
    "GLA": ("Cork to Glasgow flights", "Cork to Glasgow flights"),
    "CRL": ("Cork to Brussels flights", "Cork to Brussels flights"),
    "LYS": ("Cork to Lyon flights", "Cork to Lyon flights"),
    "ADB": ("Cork to Izmir | No fare yet", "Cork to Izmir flights: no fare in this scan"),
}

TRIP_PARAGRAPH = (
    "This scan prices two trip lengths. A weekend is 2 or 3 nights and leaves on "
    "Thursday, Friday or Saturday. A week is 6, 7 or 8 nights, and 7 nights is preferred. "
    "A date is listed only when a real return fare came back for one of those shapes."
)

# Homepage links. href is the path. Anchor text follows the search, not a price.
POPULAR_ROUTES = (
    ("/destinations/rhodes.html", "Rhodes", "Dublin to Rhodes", "Hand-checked on ryanair.com"),
    ("/destinations/pisa.html", "Pisa", "Dublin to Pisa", "Cork fare hand-checked"),
    ("/destinations/berlin.html", "Berlin", "Flights to Berlin from Cork", "Dublin fares in this scan"),
    ("/destinations/faro.html", "Faro", "Flights to Faro from Cork", "Cork and Dublin"),
    ("/destinations/venice.html", "Venice", "Dublin to Venice", "No Cork fare in this scan"),
    ("/destinations/madrid.html", "Madrid", "Dublin to Madrid", "Dublin fares in this scan"),
    ("/destinations/krakow.html", "Krakow", "Cork to Krakow", "Fly direct from Dublin"),
    ("/destinations/budapest.html", "Budapest", "Budapest from Cork", "Dublin fares in this scan"),
    ("/destinations/copenhagen.html", "Copenhagen", "Cork to Copenhagen", "Dublin fares in this scan"),
    ("/destinations/malta.html", "Malta", "Malta from Cork", "Dublin fares in this scan"),
    ("/destinations/porto.html", "Porto", "Cork to Porto", "Fly from Dublin"),
    ("/routes/cork-to-fuerteventura.html", "Fuerteventura", "Cork to Fuerteventura", "A few flights a month"),
    ("/destinations/malaga.html", "Malaga", "Malaga from Cork", "Cork and Dublin"),
    ("/destinations/lisbon.html", "Lisbon", "Cork to Lisbon", "Dublin fares in this scan"),
    ("/destinations/seville.html", "Seville", "Cork to Seville", "Cork and Dublin"),
    ("/destinations/athens.html", "Athens", "Dublin to Athens", "Hand-checked on ryanair.com"),
    ("/destinations/alicante.html", "Alicante", "Dublin to Alicante", "Cork and Dublin"),
    ("/destinations/rome.html", "Rome", "Dublin to Rome flights", "Dublin fares"),
    ("/destinations/nice.html", "Nice", "Nice from Cork", "Dublin fares in this scan"),
    ("/destinations/zadar.html", "Zadar", "Dublin to Zadar", "Hand-checked on ryanair.com"),
    ("/destinations/tenerife.html", "Tenerife", "Tenerife from Cork", "Cork and Dublin"),
    ("/routes/dublin-to-edinburgh.html", "Edinburgh", "Dublin to Edinburgh", "Daily on Ryanair's page"),
    ("/routes/cork-to-barcelona.html", "Barcelona", "Cork to Barcelona", "Several days a week"),
)
POPULAR_START = "<!-- hc-popular-routes -->"
POPULAR_END = "<!-- /hc-popular-routes -->"
# The cards live inside this tab panel. A refresh updates them there and
# moves a block that is still sitting outside the panel back into it.
ROUTES_TAB_ID = "tab-routes"


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


# Paris Beauvais is a separate airport. Its fares also belong on the Paris page.
PAGE_AIRPORTS = {"CDG": ("CDG", "BVA")}

# Origins named on pages for airports checked on ryanair.com on 13–14 Nov 2026.
# This is not the FlightAPI route list. Leaving a code out of refresh_deals
# keeps the scheduled scan from spending credits on it.
PAGE_ORIGINS = {
    "BVA": ("ORK", "DUB"),
    "MXP": ("DUB",),
    "LUX": ("DUB",),
    "BRU": ("DUB",),
    "AGA": ("DUB",),
    "FNC": ("DUB",),
}

# Madrid is Dublin only on this scan. The page does not name Cork.
DUBLIN_ONLY_PAGES = {"MAD"}

# These airports already have destination pages. Manual rows for them are
# kept in the CSV and are not added to the page. No new page is created.
SUPPLEMENT_SKIP = {"GVA", "LYS", "MUC", "PRG"}


def _page_airports(code):
    return PAGE_AIRPORTS.get(code, (code,))


def collect_fares(cache, code):
    """All scanned direct fares for one destination, both airports."""
    wanted = {c.upper() for c in _page_airports(code)}
    rows = []
    for ap_code, ap_name in (("ORK", "Cork"), ("DUB", "Dublin")):
        ap = (cache.get("airports") or {}).get(ap_code) or {}
        groups = [
            ("Weekend", ap.get("weekend_boards") or []),
            ("Week", ap.get("week_boards") or []),
        ]
        for board in ap.get("special_boards") or []:
            label = str(board.get("trip_type") or "trip").replace("_", " ").strip().title() or "Trip"
            groups.append((label, [board]))
        for kind, boards in groups:
            for b in boards:
                deal = next((d for d in (b.get("deals") or [])
                             if (d.get("code") or "").upper() in wanted), None)
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
                    "code": (deal.get("code") or "").upper(),
                    "checked_at": deal.get("checked_at") or "",
                    "checked_at_dublin": deal.get("checked_at_dublin") or "",
                    "source_url": deal.get("source_url") or "",
                    "fare_label": deal.get("fare_label") or "",
                    "stale": bool(deal.get("stale")),
                    "airport_label": deal.get("airport_label") or "",
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


def _page_origin_pairs(code):
    """(name, IATA) pairs this page may name.

    PAGE_ORIGINS is the verified list for airports that are not all on the
    FlightAPI route list. Every other city still shows Cork and Dublin, and
    says when the scanner does not price one of them.
    """
    if code in PAGE_ORIGINS:
        allowed = set(PAGE_ORIGINS[code])
        return [pair for pair in (("Cork", "ORK"), ("Dublin", "DUB")) if pair[1] in allowed]
    if code in DUBLIN_ONLY_PAGES:
        return [("Dublin", "DUB")]
    return [("Cork", "ORK"), ("Dublin", "DUB")]


def empty_copy(code, city, updated):
    """Honest explanation when the cache has no fare. Never states a price."""
    if code in PAGE_ORIGINS:
        who = " and ".join(name for name, _ap in _page_origin_pairs(code))
        return (
            f"No fare in the current scan ({updated}). "
            f"This page is for direct returns from {who}. "
            f"A price is shown here only after a scan stores a real return."
        )
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


def _iso(value):
    if not isinstance(value, str):
        return ""
    try:
        return value if dt.date.fromisoformat(value).isoformat() == value else ""
    except ValueError:
        return ""


AP_CODE = {"Cork": "ORK", "Dublin": "DUB"}


def featured_fare(rows):
    """Cheapest scanned fare that has an airport and both dates. None if the
    page has prices but no usable dates — the caller must not invent any."""
    priced = []
    for row in rows:
        ap = AP_CODE.get(row.get("from") or "")
        dep, ret = _iso(row.get("dep") or ""), _iso(row.get("ret") or "")
        price = row.get("price")
        if not ap or not dep or not ret or price in (None, ""):
            continue
        priced.append((price, dep, 0 if ap == "ORK" else 1, ap, ret, row.get("code") or ""))
    if not priced:
        return None
    # The code is not part of the ordering, so a tie still picks the first row.
    price, dep, _order, ap, ret, deal_code = min(priced, key=lambda item: item[:5])
    return {"from": ap, "dep": dep, "ret": ret, "price": price, "code": deal_code}


CHECKED_ASSETS = """<style>
.basis{font-weight:600;font-size:11px;color:var(--muted)}
.checked{display:block;font-weight:500;font-size:11px;color:var(--muted);margin-top:4px}
.checked[data-stale="1"]{color:#9A3412}
a.fare-link{color:inherit}
</style>
<script>
(function () {
  var STALE_HOURS = __STALE_HOURS__;
  var HIDE_HOURS = __HIDE_HOURS__;
  function rel(then) {
    var mins = Math.round((Date.now() - then.getTime()) / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return mins + " minute" + (mins === 1 ? "" : "s") + " ago";
    var hours = Math.round(mins / 60);
    if (hours < STALE_HOURS) return hours + " hour" + (hours === 1 ? "" : "s") + " ago";
    var days = Math.round(hours / 24);
    return days + " day" + (days === 1 ? "" : "s") + " ago";
  }
  var rows = document.querySelectorAll("tr[data-manual][data-checked-at]");
  var now = Date.now();
  for (var i = 0; i < rows.length; i++) {
    var tr = rows[i];
    var el = tr.querySelector(".checked");
    var then = new Date(tr.getAttribute("data-checked-at"));
    if (!el || isNaN(then.getTime())) continue;
    var age = now - then.getTime();
    if (age >= HIDE_HOURS * 3600000) {
      if (tr.parentNode) tr.parentNode.removeChild(tr);
      continue;
    }
    var host = el.getAttribute("data-host") || "the airline site";
    var dublin = el.getAttribute("data-dublin") || "";
    var stale = age >= STALE_HOURS * 3600000;
    if (stale) el.setAttribute("data-stale", "1");
    else el.removeAttribute("data-stale");
    var when = dublin ? " (" + dublin + " Dublin)" : "";
    var warn = stale ? " · fare may have changed" : "";
    el.textContent = "Checked on " + host + " " + rel(then) + when + warn;
  }
  var blocks = document.querySelectorAll("[data-fare-block]");
  for (var j = 0; j < blocks.length; j++) {
    var block = blocks[j];
    var body = block.querySelector("tbody");
    if (!body || body.querySelector("tr")) continue;
    var wrap = block.querySelector(".table-wrap");
    var heading = block.querySelector("h2");
    var fallback = block.querySelector("template[data-manual-fallback]");
    if (wrap) wrap.hidden = true;
    if (heading) heading.hidden = true;
    if (fallback && fallback.content) block.appendChild(fallback.content.cloneNode(true));
  }
  if (!document.querySelector("tbody tr")) {
    var lead = document.querySelector("[data-manual-lead]");
    var dropped = document.querySelector(".empty-fare p");
    if (lead && dropped) lead.textContent = dropped.textContent;
  }
})();
</script>
"""


def checked_note(rows):
    if not any(row.get("checked_at") for row in rows):
        return ""
    return " · from, no bags · Dublin time is when that fare was checked"


def checked_assets(rows):
    if not any(row.get("checked_at") for row in rows):
        return ""
    return (CHECKED_ASSETS
            .replace("__STALE_HOURS__", str(manual_fares.STALE_HOURS))
            .replace("__HIDE_HOURS__", str(manual_fares.HIDE_HOURS)))


def _format_price(price):
    if isinstance(price, float):
        return f"{price:.2f}"
    return str(price)


def _checked_moment(iso, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    text = (iso or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    then = dt.datetime.fromisoformat(text).astimezone(dt.timezone.utc)
    return now.astimezone(dt.timezone.utc) - then


def relative_checked(iso, now=None):
    """Same buckets as the page script: minutes, then hours, then days."""
    try:
        age = _checked_moment(iso, now)
    except (ValueError, TypeError):
        return "recently"
    mins = int(age.total_seconds() / 60 + 0.5)
    if mins < 1:
        return "just now"
    if mins < 60:
        unit = "minute" if mins == 1 else "minutes"
        return f"{mins} {unit} ago"
    hours = int(mins / 60 + 0.5)
    if hours < manual_fares.STALE_HOURS:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit} ago"
    days = int(hours / 24 + 0.5)
    unit = "day" if days == 1 else "days"
    return f"{days} {unit} ago"


def _row_is_stale(row, now=None):
    checked = row.get("checked_at") or ""
    if not checked:
        return False
    try:
        age = _checked_moment(checked, now)
    except (ValueError, TypeError):
        return bool(row.get("stale"))
    return age > dt.timedelta(hours=manual_fares.STALE_HOURS)


def _fare_host(url):
    host = (urlparse(url or "").hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def checked_price_extra(row):
    """Empty unless this fare was read by the scout. FlightAPI rows stay as they are."""
    if not row.get("checked_at"):
        return ""
    return manual_price_html(row, linked=False)


def checked_line(row):
    checked = row.get("checked_at") or ""
    if not checked:
        return ""
    host = _fare_host(row.get("source_url") or "") or "the airline site"
    dublin = row.get("checked_at_dublin") or ""
    stale = _row_is_stale(row)
    stale_attr = ' data-stale="1"' if stale else ""
    fallback = f"Checked on {html_lib.escape(host)} {html_lib.escape(relative_checked(checked))}"
    if dublin:
        fallback += f" ({html_lib.escape(dublin)} Dublin)"
    if stale:
        fallback += " · fare may have changed"
    return (
        f"<div class=\"checked\" data-checked-at=\"{html_lib.escape(checked, quote=True)}\""
        f" data-host=\"{html_lib.escape(host, quote=True)}\""
        f" data-dublin=\"{html_lib.escape(dublin, quote=True)}\"{stale_attr}>{fallback}</div>"
    )


def manual_price_html(row, linked=True):
    phrase = f"from €{_format_price(row.get('price'))} return, no bags"
    line = checked_line(row)
    if not linked or not row.get("source_url"):
        return f" <span class=\"basis\">{html_lib.escape(phrase)}</span>{line}"
    url = html_lib.escape(row["source_url"], quote=True)
    return (
        f"<a class=\"fare-link\" href=\"{url}\" rel=\"noopener noreferrer\" target=\"_blank\">"
        f"{html_lib.escape(phrase)}</a>{line}"
    )


def fare_row(row):
    origin = row["from"]
    if row.get("airport_label"):
        origin = f"{row['from']} → {html_lib.escape(row['airport_label'])}"
    nights = f" · {row['nights']}n" if row["nights"] else ""
    saver = " 💡" if row["saver"] else ""
    if row.get("checked_at"):
        attrs = (
            f" data-manual=\"1\""
            f" data-checked-at=\"{html_lib.escape(row['checked_at'], quote=True)}\""
        )
        price = manual_price_html(row)
    else:
        attrs = ""
        price = f"€{row['price']}{saver}{checked_price_extra(row)}"
    return (
        f"<tr{attrs}><td>{origin}</td><td>{row['kind']}</td>"
        f"<td>{fmt_date(row['dep'])} → {fmt_date(row['ret'])}{nights}</td>"
        f"<td class='p'>{price}</td>"
        f"<td>{html_lib.escape(row['airline'])}</td></tr>"
    )


def fare_tbody(rows):
    """The <tbody> inner HTML for one destination. Also the fare fingerprint.

    An empty scan is the empty string. The page shows a no-fare panel then,
    not a table row.
    """
    if not rows:
        return ""
    return "\n".join(fare_row(row) for row in rows)


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
    manual = [r for r in rows if r.get("checked_at")]
    scanned = [r for r in rows if not r.get("checked_at")]
    if manual and not scanned:
        bits = []
        ordered = sorted(manual, key=lambda item: (item.get("price") or 0, item.get("dep") or ""))
        for row in ordered:
            host = _fare_host(row.get("source_url") or "") or "the airline site"
            when = ""
            if row.get("dep") and row.get("ret"):
                when = f" on {fmt_date(row['dep'])} to {fmt_date(row['ret'])}"
            airline = row.get("airline") or "The airline"
            bits.append(
                f"A {airline} return checked on {host}{when}, "
                f"from €{_format_price(row.get('price'))} return, no bags."
            )
        return " ".join(bits) + " It is not a fare from the FlightAPI scan."
    if not scanned:
        return f"The latest scan stored no {origin} fare."
    rows = scanned
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


def auto_sections(code, city, rows=None):
    """Scan facts only. Does not invent an airline weekday pattern."""
    rows = rows or []
    by_origin = {}
    for row in rows:
        by_origin.setdefault(row["from"], []).append(row)
    if code in PAGE_ORIGINS or code in DUBLIN_ONLY_PAGES:
        return [(origin, ["SCAN"]) for origin, _ap in _page_origin_pairs(code)]
    served = set(refresh_deals.served_origins(code))
    sections = []
    for origin, ap in _page_origin_pairs(code):
        has_manual = any(row.get("checked_at") for row in by_origin.get(origin, []))
        if ap not in served and not has_manual:
            sections.append((origin, [
                f"This scan does not price {origin} to {city}.",
            ]))
        else:
            sections.append((origin, ["SCAN"]))
    return sections


def trip_fit_paragraph(origin, rows):
    """Which stored fares are a weekend (Thu–Sat, 2–3 nights) or a week (6–8)."""
    manual = [r for r in rows if r.get("checked_at")]
    scanned = [r for r in rows if not r.get("checked_at")]
    if manual and not scanned:
        return (
            f"The {origin} fare in the table was opened on the airline site. "
            "It is not one of the weekend or one-week dates from the FlightAPI scan."
        )
    def shape(group, label):
        if not group:
            return f"The latest scan stored no {label} trip from {origin}."
        nights = sorted({
            int(r["nights"]) for r in group if str(r.get("nights") or "").isdigit()
        })
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days = sorted({
            dt.date.fromisoformat(r["dep"]).strftime("%A") for r in group if r.get("dep")
        }, key=order.index)
        night_text = _name_list([f"{n}-night" for n in nights]) if nights else "the stored length"
        day_text = _name_list(days) if days else "the stored days"
        return (
            f"The latest scan stored {label} trips from {origin}, departing on {day_text}, "
            f"on {night_text} trips."
        )
    weekend = [r for r in rows if r["kind"] == "Weekend"]
    week = [r for r in rows if r["kind"] == "Week"]
    return shape(weekend, "weekend") + " " + shape(week, "one-week")


def route_section(code, city, rows):
    guide = GUIDES.get(code)
    manual_only = bool(rows) and all(row.get("checked_at") for row in rows)
    if guide and guide.get("sections") and not manual_only:
        sections = guide["sections"]
        origin_names = ("Cork", "Dublin")
        heading = "Routes from Cork and Dublin"
    else:
        sections = auto_sections(code, city, rows)
        origin_names = tuple(name for name, _ap in _page_origin_pairs(code))
        heading = "Routes from " + " and ".join(origin_names)
    by_origin = {}
    for row in rows:
        by_origin.setdefault(row["from"], []).append(row)
    parts = [f"<h2>{html_lib.escape(heading)}</h2>"]
    for section_heading, paragraphs in sections:
        parts.append(f"<h3>{html_lib.escape(section_heading)}</h3>")
        for para in paragraphs:
            text = _scan_paragraph(section_heading, by_origin.get(section_heading, [])) if para == "SCAN" else para
            parts.append(f"<p>{html_lib.escape(text, quote=False)}</p>")
    parts.append("<h3>Weekend or one week</h3>")
    parts.append(f"<p>{html_lib.escape(TRIP_PARAGRAPH)}</p>")
    for origin in origin_names:
        parts.append(f"<p>{html_lib.escape(trip_fit_paragraph(origin, by_origin.get(origin, [])))}</p>")
    return "\n".join(parts)


def city_image(code):
    """Existing city photo when the repo has one, otherwise the site image."""
    rel = f"social/assets/cities/{code}.jpg"
    if os.path.exists(rel):
        return f"{SITE}/{rel}"
    return f"{SITE}/og-image.png"


def breadcrumb_ld(items):
    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": url}
            for i, (name, url) in enumerate(items, 1)
        ],
    }
    return json.dumps(payload).replace("<", "\\u003c")


def route_links_html(code):
    links = [r for r in ROUTES if r["code"] == code]
    if not links:
        return ""
    bits = [
        '<a href="/routes/{slug}.html">{label}</a>'.format(
            slug=html_lib.escape(r["slug"], quote=True),
            label=html_lib.escape(r["link"]),
        )
        for r in links
    ]
    return "<h2>Route guides</h2>\n<p class=\"rel\">" + " · ".join(bits) + "</p>"


def _fill_price(text, min_p, bold=False):
    """Swap €{price} for the scanned fare. Bold is only for the visible intro."""
    if "{price}" not in text:
        return text
    if not min_p:
        return text.replace("€{price}", "")
    shown = f"<b>€{min_p}</b>" if bold else f"€{min_p}"
    return text.replace("€{price}", shown)


def page_html(code, slug, city, country, blurb, rows, updated, fare_counts):
    prices = [r["price"] for r in rows if r["price"]]
    min_p = min(prices) if prices else None
    airlines = sorted({r["airline"] for r in rows if r["airline"] != "—"})
    manual_rows = [r for r in rows if r.get("checked_at")]
    manual_only = bool(rows) and len(manual_rows) == len(rows)
    guide = GUIDES.get(code)
    head, h1 = SEARCH[code]
    title = f"{head} | Holiday Chasers"
    if len(title) > 60:
        raise SystemExit(f"title is {len(title)} characters, over 60: {title}")
    if "(2026)" in title or title.lower().startswith("cheap flights"):
        raise SystemExit(f"stale title pattern: {title}")
    if guide and guide.get("desc") and not manual_rows and (min_p or "{price}" not in guide["desc"]):
        desc = _fill_price(guide["desc"], min_p)
    elif min_p:
        desc = (
            f"{h1}. From €{min_p} return per person. "
            "Weekend and one-week trips from scanned fares."
        )
    else:
        desc = f"{h1}. No fare in the current scan. No price is estimated."
    desc = desc if len(desc) <= 160 else _clip(desc, 160)

    fare_rows = fare_tbody(rows)

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
            (f"Which airlines did the latest scan store for {city}?",
             (_name_list(airlines) + " are the airlines on the stored fares. "
              "That is who came back in the scan, not a full timetable.")
             if airlines else
             "The latest scan stored no airline name for this city."),
            (f"What's the best way to find cheap dates for {city}?",
             "Open the trip planner on our homepage — it uses the same scanned fares "
             "and builds the trip around the date you pick."),
        ]
    else:
        lead = gap
        note = f"Direct flights only · prices per person, return · last scanned {updated}"
        related_heading = "Destinations with fares right now"
        cta_label = "See Cork &amp; Dublin deals that are on the board →"
        if code in PAGE_ORIGINS:
            who = " and ".join(name for name, _ap in _page_origin_pairs(code))
            fare_q = f"How much are flights to {city} from {who} right now?"
            airline_q = f"Which airlines fly direct to {city} from {who}?"
        else:
            fare_q = f"How much are flights to {city} from Ireland right now?"
            airline_q = f"Which airlines fly direct to {city} from Cork or Dublin?"
        faq = [
            (fare_q, gap),
            (airline_q,
             "None are in the latest scan, so this page doesn't name a carrier or a price."),
            (f"Where can I see a fare while {city} has none?",
             "The destinations linked below have direct returns in the latest scan. "
             "The homepage board is the same data."),
        ]
    note += checked_note(rows)
    assets = checked_assets(rows)
    if guide and not manual_rows:
        if guide.get("intro"):
            lead = _fill_price(guide["intro"], min_p, bold=True)
        if guide.get("fare_answer"):
            faq[0] = (faq[0][0], guide["fare_answer"])
        elif guide.get("price_answer") and min_p:
            faq[0] = (faq[0][0], guide["price_answer"].format(price=min_p))
        if guide.get("airline_answer"):
            faq[1] = (
                f"Which airlines fly direct to {city} from Cork or Dublin?",
                guide["airline_answer"],
            )
        faq.extend(guide.get("faqs") or [])
    if manual_rows and min_p:
        who = _name_list([name for name in ("Cork", "Dublin") if any(r["from"] == name for r in manual_rows)])
        amount = _format_price(min_p)
        hosts = _name_list(sorted({
            _fare_host(r.get("source_url") or "") or "the airline site" for r in manual_rows
        }))
        if manual_only:
            lead = (
                f"Hand-checked {who} returns from <b>€{amount}</b>, no bags. "
                "The table is the cheapest fare opened on the airline site for each origin. "
                "It is not a price from the FlightAPI scan."
            )
            desc = f"{h1}. From €{amount} return, no bags. Hand-checked for {who}."
            note = f"Direct flights only · hand-checked return, no bags{checked_note(rows)}"
            faq = [
                (f"How much are flights to {city} from {who} right now?",
                 f"The cheapest hand-checked return is €{amount}, no bags, on {hosts}. "
                 "The time in the table is when that fare was read. It can move before you book."),
                (f"Which airline was checked for {city}?",
                 (_name_list(airlines) + ". The price links to the page that was opened.")
                 if airlines else
                 "The price links to the airline page that was opened."),
                (f"Is this the same figure as the homepage board?",
                 "No. The homepage board is the FlightAPI scan. This figure was read on the airline site "
                 "because that scan has no fare for this trip."),
            ]
        else:
            cheapest = min(rows, key=lambda r: r["price"])
            if cheapest.get("checked_at"):
                lead = (
                    f"Direct returns from <b>€{amount}</b>, no bags. "
                    "The lowest figure was checked on the airline site. "
                    "Fares already in the scan are unchanged."
                )
                desc = (
                    f"{h1}. From €{amount} return, no bags. "
                    "Hand-checked where this scan has no fare."
                )
        desc = desc if len(desc) <= 160 else _clip(desc, 160)
    faq.append((
        f"What trip lengths does this scan search for {city}?",
        TRIP_PARAGRAPH,
    ))
    transport = TRANSPORT.get(code)
    if transport:
        faq.append((f"How do I get from the airport into town after landing in {city}?", transport))
    faq_html = "\n".join(
        f"<details><summary>{html_lib.escape(q, quote=False)}</summary>"
        f"<p>{html_lib.escape(a, quote=False)}</p></details>" for q, a in faq)
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in faq]}).replace("<", "\\u003c")
    # data-hc-* is read by consent.js after consent. This is the page's only
    # booking-funnel link. With a stored fare, /?dest=&from=&out=&ret= opens
    # that exact trip. With none, the same hook points at the homepage board.
    fare = featured_fare(rows)
    dest_code = (fare.get("code") if fare else "") or code
    if fare:
        cta_href = "/?" + urlencode((
            ("dest", dest_code), ("from", fare["from"]), ("out", fare["dep"]), ("ret", fare["ret"]),
        ))
        date_attrs = (
            f' data-hc-origin="{html_lib.escape(fare["from"], quote=True)}"'
            f' data-hc-out="{html_lib.escape(fare["dep"], quote=True)}"'
            f' data-hc-ret="{html_lib.escape(fare["ret"], quote=True)}"'
        )
    else:
        cta_href = ("/?dest=" + html_lib.escape(code, quote=True)) if rows else "/"
        date_attrs = ""
    cta_html = (
        '<a class="cta" href="{href}"'
        ' data-hc-event="flight_click"'
        ' data-hc-destination="{city}"'
        ' data-hc-dest="{code}"'
        ' data-hc-source="destination_page"{dates}>{label}</a>'
    ).format(
        href=html_lib.escape(cta_href, quote=True),
        code=html_lib.escape(dest_code, quote=True),
        city=html_lib.escape(city, quote=True),
        label=cta_label,
        dates=date_attrs,
    )
    routes_html = route_section(code, city, rows)
    routes_block = f'\n<div class="routes">\n{routes_html}\n</div>\n' if routes_html else ""
    place = PLACE_NOTES.get(code)
    notes_html = (
        "<h2>What to see</h2>\n"
        f"<p>{html_lib.escape(place, quote=False)}</p>\n"
    ) if place else ""
    page_url = f"{SITE}/destinations/{slug}.html"
    og_image = city_image(code)
    crumbs_html = (
        '<nav class="crumbs" aria-label="Breadcrumb">'
        '<a href="/">Home</a><span aria-hidden="true">/</span>'
        f'{html_lib.escape(city)}</nav>'
    )
    crumb_ld = breadcrumb_ld([
        ("Home", f"{SITE}/"),
        (city, page_url),
    ])
    route_links = route_links_html(code)
    transport_html = ""
    if transport:
        transport_html = (
            "<h2>Airport to the city</h2>\n"
            f"<p>{html_lib.escape(transport, quote=False)}</p>"
        )
    if rows:
        fare_block = (
            f"<h2>Every scanned date for {html_lib.escape(city)}</h2>\n"
            "<div class=\"table-wrap\">\n<table>\n"
            "<thead><tr><th>From</th><th>Trip</th><th>Dates</th><th>Per person</th><th>Airline</th></tr></thead>\n"
            f"<tbody>\n{fare_rows}\n</tbody>\n</table>\n</div>\n"
            f"<p class=\"note\">{note}</p>"
        )
        if manual_rows:
            fallback = (
                "<template data-manual-fallback>\n"
                "<div class=\"empty-fare\">\n"
                "<h2>No fare in the current scan</h2>\n"
                f"<p>No price is shown for {html_lib.escape(city)}. "
                "A fare appears here only after a scan stores a real return. "
                "Nothing on this page is an estimated price.</p>\n"
                "</div>\n"
                "</template>\n"
            )
            fare_block = f"<div data-fare-block=\"1\">\n{fare_block}{fallback}</div>"
    else:
        fare_block = (
            "<div class=\"empty-fare\">\n"
            "<h2>No fare in the current scan</h2>\n"
            f"<p>No price is shown for {html_lib.escape(city)}. "
            "A fare appears here only after a scan stores a real return. "
            "Nothing on this page is an estimated price.</p>\n"
            "</div>\n"
            f"<p class=\"note\">{note}</p>"
        )
    h1_html = html_lib.escape(h1)
    title = html_lib.escape(title)
    desc = html_lib.escape(desc, quote=True)
    lead_attrs = " data-manual-lead=\"1\"" if manual_only else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{og_image}">
<link rel="canonical" href="{page_url}">
<script type="application/ld+json">{faq_ld}</script>
<script type="application/ld+json">{crumb_ld}</script>
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
.crumbs{{font-size:13px;margin:0 0 14px;color:var(--muted)}}
.crumbs a{{color:var(--gold);font-weight:700;text-decoration:none}}
.crumbs span{{margin:0 6px}}
.empty-fare{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 18px 8px;margin:8px 0 18px}}
.empty-fare h2{{margin-top:0}}
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
{crumbs_html}
<h1>{h1_html}</h1>
<p class="sub">{blurb}</p>
<p{lead_attrs}>{lead}</p>
{cta_html}
{routes_block}
{fare_block}
{notes_html}{transport_html}
{route_links}

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
{assets}<script src="/consent.js" defer></script>
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
    for href, name, label, note in POPULAR_ROUTES:
        cards.append(
            '<a href="{href}">'
            '<span class="pr-kicker">{name}</span>'
            '<strong>{label}</strong>'
            '<span>{note}</span></a>'.format(
                href=html_lib.escape(href, quote=True),
                name=html_lib.escape(name),
                label=html_lib.escape(label),
                note=html_lib.escape(note),
            )
        )
    inner = (
        '<section class="popular-routes" aria-label="Popular routes">\n'
        '  <h2>Popular routes</h2>\n'
        '  <p>Pages for the searches that already reach the site. '
        'Where this scan has no Cork fare, the card says so.</p>\n'
        '  <div class="popular-grid">\n    '
        + "\n    ".join(cards)
        + "\n  </div>\n</section>"
    )
    return POPULAR_START + "\n" + inner + "\n" + POPULAR_END


def _popular_match(doc):
    if POPULAR_START not in doc or POPULAR_END not in doc:
        return None
    pattern = re.compile(
        re.escape(POPULAR_START) + r".*?" + re.escape(POPULAR_END), re.DOTALL)
    return pattern.search(doc)


_ROUTES_TAB_OPEN = re.compile(
    r'<section\b(?=[^>]*\bid="' + re.escape(ROUTES_TAB_ID) + r'")'
    r'(?=[^>]*\bclass="[^"]*\btab-content\b)[^>]*>'
)


def _routes_tab_open(doc):
    return _ROUTES_TAB_OPEN.search(doc)


def _popular_is_in_routes_tab(doc, match):
    """True when the block is the body of the Popular routes tab panel."""
    open_tag = _routes_tab_open(doc)
    if not open_tag or open_tag.end() > match.start():
        return False
    between = doc[open_tag.end():match.start()]
    if between.strip():
        return False
    return doc.find("</section>", match.end()) != -1


def homepage_with_popular_routes(doc):
    """Homepage HTML with Popular routes inside its tab panel.

    Returns None when the page has no Popular routes tab to put the block
    in. A refresh replaces the cards in place when they are already in that
    panel, and moves the whole block into the panel when an older page still
    has it above the tabs or below them. It never puts the block back outside
    the panel.
    """
    block = popular_routes_html()
    match = _popular_match(doc)
    if match and _popular_is_in_routes_tab(doc, match):
        if match.group(0) == block:
            return doc
        return doc[:match.start()] + block + doc[match.end():]
    if match:
        doc = doc[:match.start()] + doc[match.end():]
        doc = re.sub(r"\n{3,}", "\n\n", doc)
    open_tag = _routes_tab_open(doc)
    if not open_tag:
        return None
    suffix = doc[open_tag.end():].lstrip("\n")
    return doc[:open_tag.end()] + "\n" + block + "\n" + suffix


def popular_routes_will_change():
    path = "index.html"
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        doc = f.read()
    new = homepage_with_popular_routes(doc)
    return new is not None and new != doc


def update_popular_routes():
    """Insert or refresh the homepage popular-routes block. A deal refresh
    rewrites destination pages, so this block has to live in the generator.
    The cards stay inside the Popular routes tab. A refresh never moves
    them back out of that panel."""
    path = "index.html"
    if not os.path.exists(path):
        print("  skip popular routes: index.html missing")
        return
    with open(path, encoding="utf-8") as f:
        doc = f.read()
    new = homepage_with_popular_routes(doc)
    if new is None:
        print("  skip popular routes: no insertion point in index.html")
        return
    if new != doc:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"  updated homepage popular routes ({len(POPULAR_ROUTES)} links)")
    else:
        print("  homepage popular routes already current")


def write_404(route_slugs=()):
    """Branded 404. Known trailing-slash destination and route URLs redirect."""
    slugs = json.dumps(sorted(item[0] for item in CITIES.values()))
    route_slugs_js = json.dumps(sorted(route_slugs))
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
  var routeSlugs = __ROUTES__;
  var path = location.pathname || "";
  var match = path.match(/^\\/destinations\\/([a-z0-9-]+)(?:\\.html)?\\/+$/);
  var routeMatch = path.match(/^\\/routes\\/([a-z0-9-]+)(?:\\.html)?\\/+$/);
  var list = match ? slugs : (routeMatch ? routeSlugs : null);
  var slug = match ? match[1] : (routeMatch ? routeMatch[1] : "");
  var folder = match ? "destinations" : "routes";
  if (!list) return;
  for (var i = 0; i < list.length; i++) {
    if (list[i] === slug) {
      location.replace("/" + folder + "/" + slug + ".html" + location.search + location.hash);
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
    page = page.replace("__SLUGS__", slugs).replace("__ROUTES__", route_slugs_js).replace("__LINKS__", links)
    with open("404.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote 404.html ({len(CITIES)} destination redirects)")


def read_sitemap_lastmods(path="sitemap.xml"):
    """loc -> lastmod already published. Missing file or tag returns nothing."""
    if not os.path.exists(path):
        return {}
    text = open(path, encoding="utf-8").read()
    out = {}
    for block in re.findall(r"<url>(.*?)</url>", text, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        last = re.search(r"<lastmod>([^<]+)</lastmod>", block)
        if loc and last:
            out[loc.group(1)] = last.group(1).strip()
    return out


def git_file_date(path):
    """Last commit date for path (YYYY-MM-DD), or None if git cannot say."""
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%cs", "--", path],
            text=True, stderr=subprocess.DEVNULL, timeout=10).strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return out if re.fullmatch(r"\d{4}-\d{2}-\d{2}", out) else None


def file_tbody(path):
    if not os.path.exists(path):
        return None
    html = open(path, encoding="utf-8").read()
    match = re.search(r"<tbody>\n(.*)\n</tbody>", html, re.S)
    if match:
        return match.group(1)
    if 'class="empty-fare"' in html:
        return ""
    return None


def destination_lastmod(slug, fare_rows, cache_date, previous):
    """Scan date when the fare table changed. Otherwise keep the old lastmod."""
    url = f"{SITE}/destinations/{slug}.html"
    path = os.path.join(OUT_DIR, f"{slug}.html")
    old_rows = file_tbody(path)
    if old_rows is not None and old_rows == fare_rows:
        if url in previous:
            return previous[url]
        return git_file_date(path) or cache_date
    return cache_date


def static_lastmod(path, url, cache_date, previous, changed=False):
    """Info pages and the homepage are not the fare scan.

    A deal refresh must not stamp About or Contact with the cache date.
    Use the file's last commit, then the date already in the sitemap.
    """
    if changed:
        return cache_date
    return git_file_date(path) or previous.get(url) or cache_date


def homepage_footer_will_change():
    path = "index.html"
    if not os.path.exists(path):
        return False
    doc = open(path, encoding="utf-8").read()
    if FOOTER_START not in doc or FOOTER_END not in doc:
        return False
    pattern = re.compile(
        re.escape(FOOTER_START) + r".*?" + re.escape(FOOTER_END), re.S)
    match = pattern.search(doc)
    if not match:
        return False
    new = FOOTER_START + "\n    " + city_links() + "\n    " + FOOTER_END
    return match.group(0) != new


def sitemap_entry(loc, freq, priority, lastmod):
    last = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    return (f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq>"
            f"<priority>{priority}</priority>{last}</url>")


def _fare_table(rows, empty_city):
    if not rows:
        return (
            "<div class=\"empty-fare\">\n"
            "<h2>No fare in the current scan</h2>\n"
            f"<p>No price is shown for {html_lib.escape(empty_city)}. "
            "A fare appears here only after a scan stores a real return.</p>\n"
            "</div>"
        )
    body = fare_tbody(rows)
    table = (
        "<div class=\"table-wrap\">\n<table>\n"
        "<thead><tr><th>From</th><th>Trip</th><th>Dates</th><th>Per person</th><th>Airline</th></tr></thead>\n"
        f"<tbody>\n{body}\n</tbody>\n</table>\n</div>"
    )
    if not any(row.get("checked_at") for row in rows):
        return table
    fallback = (
        "<template data-manual-fallback>\n"
        "<div class=\"empty-fare\">\n"
        "<h2>No fare in the current scan</h2>\n"
        f"<p>No price is shown for {html_lib.escape(empty_city)}. "
        "A fare appears here only after a scan stores a real return.</p>\n"
        "</div>\n"
        "</template>"
    )
    return f"<div data-fare-block=\"1\">\n{table}\n{fallback}\n</div>"


def route_page_html(route, city, dest_slug, rows, updated):
    """One airport, one city. Prices only from the rows passed in."""
    origin = route["origin"]
    mine = [r for r in rows if r["from"] == origin]
    prices = [r["price"] for r in mine if r["price"]]
    min_p = min(prices) if prices else None
    manual_only = bool(mine) and all(row.get("checked_at") for row in mine)
    title = route["title"]
    h1 = route["h1"]
    if len(title) > 60:
        raise SystemExit(f"route title is {len(title)} characters, over 60: {title}")
    if manual_only and min_p:
        amount = _format_price(min_p)
        host = _fare_host(mine[0].get("source_url") or "") or "the airline site"
        desc = f"{h1}. From €{amount} return, no bags, checked on {host}."
        lead = (
            f"A hand-checked {origin} to {city} return from <b>€{amount}</b>, no bags. "
            "The FlightAPI scan has no fare for this route."
        )
    elif min_p:
        desc = (
            f"{h1}. From €{min_p} return per person on the latest scan. "
            "No price is copied from an airline website."
        )
        lead = (
            f"The latest scan stored {origin} to {city} returns from "
            f"<b>€{min_p} per person</b>. The paragraphs below are the airline's own "
            "wording, checked 13 November 2026, and the dates this scan actually stored."
        )
    else:
        desc = f"{h1}. No fare in the current scan. No price is estimated."
        lead = (
            f"No {origin} to {city} fare is in the current scan, so no price is shown. "
            "Nothing below is an estimated fare."
        )
    desc = desc if len(desc) <= 160 else _clip(desc, 160)
    page_url = f"{SITE}/routes/{route['slug']}.html"
    dest_url = f"{SITE}/destinations/{dest_slug}.html"
    og_image = city_image(route["code"])
    paras = list(route["paragraphs"])
    paras.append(TRIP_PARAGRAPH)
    paras.append(trip_fit_paragraph(origin, mine))
    body = "\n".join(f"<p>{html_lib.escape(p, quote=False)}</p>" for p in paras)
    transport = TRANSPORT.get(route["code"])
    transport_html = ""
    faqs = list(route["faqs"])
    faqs.append((
        f"What trip lengths does this scan search on {origin} to {city}?",
        TRIP_PARAGRAPH + " " + trip_fit_paragraph(origin, mine),
    ))
    if transport:
        transport_html = (
            "<h2>Airport to the city</h2>\n"
            f"<p>{html_lib.escape(transport, quote=False)}</p>"
        )
        faqs.append((
            f"How do I get from the airport into town after landing in {city}?",
            transport,
        ))
    faq_html = "\n".join(
        f"<details><summary>{html_lib.escape(q, quote=False)}</summary>"
        f"<p>{html_lib.escape(a, quote=False)}</p></details>"
        for q, a in faqs
    )
    faq_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faqs
        ],
    }).replace("<", "\\u003c")
    crumb_ld = breadcrumb_ld([
        ("Home", f"{SITE}/"),
        (city, dest_url),
        (h1, page_url),
    ])
    siblings = [
        r for r in ROUTES if r["code"] == route["code"] and r["slug"] != route["slug"]
    ]
    links = [
        f'<a href="/destinations/{html_lib.escape(dest_slug, quote=True)}.html">{html_lib.escape(city)} from Cork and Dublin</a>',
        '<a href="/">all deals</a>',
    ]
    for sib in siblings:
        links.insert(0, (
            f'<a href="/routes/{html_lib.escape(sib["slug"], quote=True)}.html">'
            f'{html_lib.escape(sib["link"])}</a>'
        ))
    fare = featured_fare(mine)
    dest_code = (fare.get("code") if fare else "") or route["code"]
    if fare:
        cta_href = "/?" + urlencode((
            ("dest", dest_code), ("from", fare["from"]),
            ("out", fare["dep"]), ("ret", fare["ret"]),
        ))
        date_attrs = (
            f' data-hc-out="{html_lib.escape(fare["dep"], quote=True)}"'
            f' data-hc-ret="{html_lib.escape(fare["ret"], quote=True)}"'
        )
        origin_code = fare["from"]
    else:
        cta_href = ("/?dest=" + route["code"]) if mine else "/"
        date_attrs = ""
        origin_code = "ORK" if origin == "Cork" else "DUB"
    cta = (
        '<a class="cta" href="{href}" data-hc-event="flight_click" '
        'data-hc-destination="{city}" data-hc-dest="{code}" '
        'data-hc-origin="{origin}" data-hc-source="route_page"{dates}>{label}</a>'
    ).format(
        href=html_lib.escape(cta_href, quote=True),
        city=html_lib.escape(city, quote=True),
        code=html_lib.escape(dest_code, quote=True),
        origin=html_lib.escape(origin_code, quote=True),
        dates=date_attrs,
        label=html_lib.escape(
            f"Open the {city} deal — live prices, hotels & costs →" if mine
            else "See Cork & Dublin deals that are on the board →"
        ),
    )
    # The label above uses a raw ampersand in the Python string, then escape()
    # turns it into &amp; inside the anchor text. Good.
    crumbs = (
        '<nav class="crumbs" aria-label="Breadcrumb">'
        '<a href="/">Home</a><span aria-hidden="true">/</span>'
        f'<a href="/destinations/{html_lib.escape(dest_slug, quote=True)}.html">{html_lib.escape(city)}</a>'
        f'<span aria-hidden="true">/</span>{html_lib.escape(h1)}</nav>'
    )
    if manual_only:
        note = "Direct flights only · hand-checked return, no bags"
    else:
        note = (
            f"Direct flights only · prices per person, return · last scanned {updated}"
            + (" · 💡 = midweek saver" if mine else "")
        )
    note += checked_note(mine)
    assets = checked_assets(mine)
    route_lead_attrs = " data-manual-lead=\"1\"" if manual_only else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
<title>{html_lib.escape(title)}</title>
<meta name="description" content="{html_lib.escape(desc, quote=True)}">
<link rel="canonical" href="{page_url}">
<meta property="og:title" content="{html_lib.escape(title)}">
<meta property="og:description" content="{html_lib.escape(desc, quote=True)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{og_image}">
<script type="application/ld+json">{faq_ld}</script>
<script type="application/ld+json">{crumb_ld}</script>
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
p{{margin:0 0 10px}}
.crumbs{{font-size:13px;margin:0 0 14px;color:var(--muted)}}
.crumbs a{{color:var(--gold);font-weight:700;text-decoration:none}}
.crumbs span{{margin:0 6px}}
.empty-fare{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 18px 8px;margin:8px 0 18px}}
.empty-fare h2{{margin-top:0}}
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
{crumbs}
<h1>{html_lib.escape(h1)}</h1>
<p class="sub">{html_lib.escape(origin)} only. The combined {html_lib.escape(city)} page lists both airports.</p>
<p{route_lead_attrs}>{lead}</p>
{cta}
{body}
{transport_html}
<h2>Fares on this route</h2>
{_fare_table(mine, city)}
<p class="note">{note}</p>
<h2>Good to know</h2>
{faq_html}
<h2>Also on this trip</h2>
<p class="rel">{' · '.join(links)}</p>
</main>
<footer>© Holiday Chasers Ireland · <a href="/" style="color:var(--muted)">holidaychasers.ie</a> · <a href="/how-it-works.html" style="color:var(--muted)">How it works</a> · <a href="/about.html" style="color:var(--muted)">About</a> · <a href="/contact.html" style="color:var(--muted)">Contact</a> · <a class="ext" href="https://www.facebook.com/holidaychasersie" rel="noopener" target="_blank">Facebook</a> · <a class="ext" href="https://www.instagram.com/holidaychasers.ie/" rel="noopener" target="_blank">Instagram</a></footer>
<div class="consent-bar" id="consentBar">
  <div class="consent-txt"><b>Quick one:</b> we use anonymous analytics to see which deals people love, so we can find better ones. No ads, no selling data.</div>
  <div class="consent-btns">
    <button class="consent-btn consent-decline" onclick="hcConsent(false)">No thanks</button>
    <button class="consent-btn consent-accept" onclick="hcConsent(true)">That's fine</button>
  </div>
</div>
{assets}<script src="/consent.js" defer></script>
</body>
</html>"""


def _deal_rank(deal):
    return (deal["price"], deal["depart_date"], deal.get("checked_at") or "")


def cheapest_manual(deals, code):
    """Cheapest still-valid manual fare for one destination, per origin."""
    best = {}
    for deal in deals:
        if deal.get("code") != code or deal.get("origin_airport") not in ("ORK", "DUB"):
            continue
        origin = deal["origin_airport"]
        prev = best.get(origin)
        if prev is None:
            best[origin] = deal
            continue
        new, old = _deal_rank(deal), _deal_rank(prev)
        if new[0] < old[0] or (new[0] == old[0] and (new[1] < old[1] or (new[1] == old[1] and new[2] > old[2]))):
            best[origin] = deal
    return best


def deal_to_row(deal):
    trip = deal.get("trip_type") or ""
    if trip == "weekend":
        kind = "Weekend"
    elif trip == "week":
        kind = "Week"
    else:
        kind = trip.replace("_", " ").strip().title() or "Trip"
    return {
        "from": "Cork" if deal["origin_airport"] == "ORK" else "Dublin",
        "kind": kind,
        "dep": deal.get("depart_date") or "",
        "ret": deal.get("return_date") or "",
        "nights": deal.get("nights") or "",
        "price": deal.get("price"),
        "airline": deal.get("airlines") or "—",
        "saver": False,
        "code": deal.get("code") or "",
        "checked_at": deal.get("checked_at") or "",
        "checked_at_dublin": deal.get("checked_at_dublin") or "",
        "source_url": deal.get("source_url") or "",
        "fare_label": deal.get("fare_label") or "from, no bags",
        "stale": bool(deal.get("stale")),
        "airport_label": deal.get("airport_label") or "",
    }


def supplement_rows(code, flight_rows, deals):
    """Keep FlightAPI rows. Add the cheapest manual fare only for an origin
    that has none. GVA, LYS, MUC and PRG are not displayed."""
    if code in SUPPLEMENT_SKIP:
        return list(flight_rows)
    have = {row["from"] for row in flight_rows}
    allowed = {name for name, _ap in _page_origin_pairs(code)}
    extra = []
    for origin, deal in cheapest_manual(deals, code).items():
        name = "Cork" if origin == "ORK" else "Dublin"
        if name not in allowed or name in have:
            continue
        extra.append(deal_to_row(deal))
    extra.sort(key=lambda row: (row["dep"], row["from"]))
    return list(flight_rows) + extra


def main():
    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)
    manual_deals, manual_report = manual_fares.supplement_deals()
    updated_iso = (cache.get("updated_utc") or "")[:10] or dt.date.today().isoformat()
    updated = fmt_date(updated_iso)
    previous_lastmod = read_sitemap_lastmods()

    os.makedirs(OUT_DIR, exist_ok=True)
    collected = []
    for code, (slug, city, country, blurb) in CITIES.items():
        flight_rows = collect_fares(cache, code)
        rows = supplement_rows(code, flight_rows, manual_deals)
        collected.append((code, slug, city, country, blurb, rows))
    fare_counts = {code: len(rows) for code, _slug, _city, _country, _blurb, rows in collected}
    urls = []
    dest_lastmod = {}
    for code, slug, city, country, blurb, rows in collected:
        # Compare against the page on disk before this run overwrites it.
        body = fare_tbody(rows)
        url = f"{SITE}/destinations/{slug}.html"
        dest_lastmod[url] = destination_lastmod(slug, body, updated_iso, previous_lastmod)
        html = page_html(code, slug, city, country, blurb, rows, updated, fare_counts)
        with open(os.path.join(OUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        urls.append(url)
        print(f"  wrote {slug}.html ({len(rows)} fares, lastmod {dest_lastmod[url]})")

    by_code = {code: (slug, city, rows) for code, slug, city, _country, _blurb, rows in collected}
    os.makedirs("routes", exist_ok=True)
    route_urls = []
    route_lastmod = {}
    for route in ROUTES:
        slug, city, rows = by_code[route["code"]]
        mine = [r for r in rows if r["from"] == route["origin"]]
        route_url = f"{SITE}/routes/{route['slug']}.html"
        route_path = os.path.join("routes", f"{route['slug']}.html")
        old_rows = file_tbody(route_path)
        body = fare_tbody(mine)
        if old_rows is not None and old_rows == body:
            route_lastmod[route_url] = (
                previous_lastmod.get(route_url) or git_file_date(route_path) or updated_iso)
        else:
            route_lastmod[route_url] = updated_iso
        html = route_page_html(route, city, slug, rows, updated)
        with open(route_path, "w", encoding="utf-8") as f:
            f.write(html)
        route_urls.append(route_url)
        print(f"  wrote routes/{route['slug']}.html (lastmod {route_lastmod[route_url]})")

    # lastmod follows the page that changed. Route pages use the same rule.
    home_url = f"{SITE}/"
    home_last = static_lastmod(
        "index.html", home_url, updated_iso, previous_lastmod,
        changed=homepage_footer_will_change() or popular_routes_will_change())
    entries = [sitemap_entry(home_url, "daily", "1.0", home_last)]
    entries += [sitemap_entry(
        f"{SITE}/{name}", "monthly", "0.4",
        static_lastmod(name, f"{SITE}/{name}", updated_iso, previous_lastmod))
        for name in INFO_PAGES]
    entries += [sitemap_entry(url, "weekly", "0.8", dest_lastmod[url]) for url in urls]
    entries += [sitemap_entry(url, "weekly", "0.7", route_lastmod[url]) for url in route_urls]
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "\n".join(entries) + "\n</urlset>\n")
    print(f"wrote sitemap.xml ({1 + len(INFO_PAGES) + len(urls) + len(route_urls)} urls)")
    update_homepage_footer()
    update_popular_routes()
    write_404([r["slug"] for r in ROUTES])
    if manual_report["rejected"]:
        print(f"manual fares rejected ({len(manual_report['rejected'])} rows):")
        for item in manual_report["rejected"]:
            print(" ", item["errors"][0])
    print(
        f"manual fares eligible={len(manual_deals)} "
        f"blank_screenshot={manual_report['blank_screenshot']} "
        f"excluded={len(manual_report['excluded'])}"
    )


if __name__ == "__main__":
    main()
