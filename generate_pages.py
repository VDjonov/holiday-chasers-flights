#!/usr/bin/env python3
"""
Holiday Chasers Ireland — SEO destination page generator.

Runs in the GitHub Action right after refresh_deals.py. Reads the fresh
deals_cache.json and writes:

  destinations/<slug>.html   one static, indexable page per destination
  sitemap.xml                homepage + all destination pages, real lastmod

Pages are rebuilt on every scan, so Google sees fresh fares every few days.
Zero API credits — everything renders from data already paid for.
"""

import json, os, datetime as dt

SITE = "https://holidaychasers.ie"
OUT_DIR = "destinations"
CACHE = "deals_cache.json"

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
    "WAW": ("warsaw", "Warsaw", "Poland", "A rebuilt old town, serious museums and a booming food scene."),
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
}


def fmt_date(iso):
    try:
        return dt.date.fromisoformat(iso).strftime("%a %-d %b")
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
                             if code in (d.get("code") or "")), None)
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


def page_html(code, slug, city, country, blurb, rows, updated, all_slugs):
    year = dt.date.today().year
    prices = [r["price"] for r in rows if r["price"]]
    min_p = min(prices) if prices else None
    airlines = sorted({r["airline"] for r in rows if r["airline"] != "—"})
    title = f"Cheap Flights to {city} from Cork & Dublin ({year}) | Holiday Chasers"
    desc = (f"Live direct-flight deals to {city} from Cork and Dublin — "
            + (f"from €{min_p} return per person. " if min_p else "")
            + "Scanned automatically every few days, with weekend and one-week trips.")

    fare_rows = "\n".join(
        f"<tr><td>{r['from']}</td><td>{r['kind']}</td>"
        f"<td>{fmt_date(r['dep'])} → {fmt_date(r['ret'])}"
        + (f" · {r['nights']}n" if r["nights"] else "") + "</td>"
        f"<td class='p'>€{r['price']}" + (" 💡" if r["saver"] else "") + "</td>"
        f"<td>{r['airline']}</td></tr>"
        for r in rows) or "<tr><td colspan='5'>No direct fares on the current scan — check the live planner.</td></tr>"

    # related: same country first, then neighbours in the list
    related = [(s, c) for k, (s, c, co, _) in CITIES.items() if co == country and k != code][:3]
    if len(related) < 3:
        for k, (s, c, co, _) in CITIES.items():
            if k != code and (s, c) not in related:
                related.append((s, c))
            if len(related) == 3:
                break
    related_html = " · ".join(f'<a href="/destinations/{s}.html">{c}</a>' for s, c in related)

    faq = [
        (f"How much are flights to {city} from Ireland right now?",
         (f"The cheapest direct return we found on our latest scan is €{min_p} per person. "
          if min_p else "See the live table above for the latest scanned fares. ")
         + "Prices refresh automatically every few days."),
        (f"Which airlines fly direct to {city} from Cork or Dublin?",
         (", ".join(airlines) if airlines else "See the fares table")
         + " operate the direct routes we track."),
        (f"What's the best way to find cheap dates for {city}?",
         "Open the trip planner on our homepage — it checks live prices for every "
         "date around your trip and builds the whole holiday: flights, hotels and costs."),
    ]
    faq_html = "\n".join(
        f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in faq)
    faq_ld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}}
                       for q, a in faq]})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
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
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:14px}}
th{{text-align:left;background:var(--cream);padding:10px 12px;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
td{{padding:10px 12px;border-top:1px solid var(--line)}}td.p{{font-weight:800}}
h2{{font-size:20px;margin:34px 0 10px}}
details{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:8px 0}}
summary{{font-weight:700;cursor:pointer}}
details p{{margin-top:8px;color:var(--muted);font-size:14px}}
footer{{text-align:center;color:var(--muted);font-size:12px;padding:24px}}
.rel{{font-size:14px}}.rel a{{color:var(--gold);font-weight:700;text-decoration:none}}
.note{{font-size:12px;color:var(--muted);margin-top:8px}}
</style>
</head>
<body>
<header><a href="/">Holiday Chasers</a><span style="font-size:12px;color:#c8d0da">Cork &amp; Dublin flight deals</span></header>
<main>
<h1>Cheap flights to {city} from Cork &amp; Dublin</h1>
<p class="sub">{blurb}</p>
<p>{('Direct returns from <b>€' + str(min_p) + ' per person</b> on our latest scan. ') if min_p else ''}We automatically scan real fares for weekend breaks and one-week holidays to {city}, so you don't have to keep checking.</p>
<a class="cta" href="/">Plan this trip — live prices, hotels &amp; costs →</a>

<h2>Every scanned date for {city}</h2>
<table>
<thead><tr><th>From</th><th>Trip</th><th>Dates</th><th>Per person</th><th>Airline</th></tr></thead>
<tbody>
{fare_rows}
</tbody>
</table>
<p class="note">Direct flights only · prices per person, return · last scanned {updated} · 💡 = midweek saver</p>

<h2>Good to know</h2>
{faq_html}

<h2>More destinations</h2>
<p class="rel">{related_html} · <a href="/">all deals →</a></p>
</main>
<footer>© Holiday Chasers Ireland · <a href="/" style="color:var(--muted)">holidaychasers.ie</a></footer>
</body>
</html>"""


def main():
    with open(CACHE, encoding="utf-8") as f:
        cache = json.load(f)
    updated_iso = (cache.get("updated_utc") or "")[:10] or dt.date.today().isoformat()
    updated = fmt_date(updated_iso)

    os.makedirs(OUT_DIR, exist_ok=True)
    all_slugs = [v[0] for v in CITIES.values()]
    urls = []
    for code, (slug, city, country, blurb) in CITIES.items():
        rows = collect_fares(cache, code)
        html = page_html(code, slug, city, country, blurb, rows, updated, all_slugs)
        with open(os.path.join(OUT_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        urls.append(f"{SITE}/destinations/{slug}.html")
        print(f"  wrote {slug}.html ({len(rows)} fares)")

    # sitemap: homepage + destination pages
    lastmod = updated_iso
    entries = [f"  <url><loc>{SITE}/</loc><changefreq>daily</changefreq>"
               f"<priority>1.0</priority><lastmod>{lastmod}</lastmod></url>"]
    entries += [f"  <url><loc>{u}</loc><changefreq>weekly</changefreq>"
                f"<priority>0.8</priority><lastmod>{lastmod}</lastmod></url>"
                for u in urls]
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "\n".join(entries) + "\n</urlset>\n")
    print(f"wrote sitemap.xml ({1 + len(urls)} urls)")


if __name__ == "__main__":
    main()
