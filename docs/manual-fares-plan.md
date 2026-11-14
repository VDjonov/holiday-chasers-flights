# Manual fares: replacing FlightAPI with the fare scout

Holiday Chasers currently buys return fares from FlightAPI.io (about $49 a month) and writes them into `deals_cache.json`. The homepage (`app.js`), the destination and route pages (`generate_pages.py`), and the social posters (`social/generate_posts.py`) all read that file. This note is the plan for letting a fare-scout assistant fill the same file from fares a person has opened on the airline's own site.

The FlightAPI path stays in place. The scheduled workflow is not changed, and nothing in this change calls Ryanair, Aer Lingus, or FlightAPI.

## 1. The file the scout fills in

The scout writes `data/manual_fares.csv`. The header is fixed, in this order:

`origin`, `destination`, `out_date`, `ret_date`, `nights`, `trip_type`, `airline`, `out_flight`, `out_time`, `ret_flight`, `ret_time`, `out_fare_eur`, `ret_fare_eur`, `total_pp_eur`, `source_url`, `checked_at_utc`, `matched_shortlist`, `seats_note`, `screenshot_ref`

`data/manual_fares.schema.json` is the JSON Schema for one row. The committed `data/manual_fares.csv` is the header only, ready for real checks. `data/manual_fares.example.csv` is a fixture: every row is labelled `EXAMPLE` in `screenshot_ref` and `seats_note`, the flight numbers are `FR999x` / `EI999x`, and the amounts are obvious placeholders (`111.11`, `222.22`, `333.33`, `300.50`, `200.00`). The converter will not write those rows into `deals_cache.json`.

What each column means:

- `origin` is `ORK` or `DUB`. Kerry (`KIR`) and Shannon (`SNN`) are rejected by name, not just as unknown codes.
- `destination` is an IATA code the site already has a page for, plus `BVA` for Paris Beauvais. Marrakesh (`RAK`) is rejected. It is not on the site, and it stays off.
- `out_date` and `ret_date` are `YYYY-MM-DD`. The return is on or after the outbound. `nights` is the exact number of days between them. A departure date already in the past (Europe/Dublin) is dropped. Dates more than 400 days ahead are rejected.
- `trip_type` is a short slug. `weekend` and `week` fill the homepage boards. Anything else, including `christmas`, is kept and listed on the destination page.
- `airline` is `Ryanair` or `Aer Lingus`.
- `out_flight`, `out_time`, `ret_flight`, `ret_time` are the flights that were opened. Times are 24-hour `HH:MM`.
- `out_fare_eur` and `ret_fare_eur` are the Basic Fare for each leg. `total_pp_eur` is the return total per person. All three are greater than 0 and at most 5000. The total must equal the two legs within €0.50. This is 1 adult, taxes included, no bags.
- `source_url` is the https page that was opened. Ryanair must be `ryanair.com`. Aer Lingus must be `aerlingus.com`.
- `checked_at_utc` is ISO 8601 with a timezone. It is stored as UTC. It must not be in the future (a 5-minute clock skew is allowed). The site shows it in Europe/Dublin.
- `matched_shortlist` is `true` or `false`: whether that total was within €0.50 of the shortlist figure. The shortlist figure itself is not a column and is not published.
- `seats_note` is optional, for a seats-left remark.
- `screenshot_ref` is required. It is an id such as `checks/2026-11-13/ork-fao.png`, not a file the website serves. A value starting with `EXAMPLE` marks a fixture.

There is no checker column. The scout's column list is fixed, and the screenshot id is the audit of who looked. A name can be added later. It should not be squeezed into another column.

The whole file is rejected if any row fails. A bad line does not silently disappear from the board.

## 2. How this becomes the site, without turning FlightAPI off

`manual_fares.py` reads the CSV and writes the same `deals_cache.json` shape the scanner already writes: `airports.ORK` and `airports.DUB`, each with `weekend_boards` and `week_boards`, plus the old top-level Cork keys. Each deal still has `city`, `country`, `code`, dates, `nights`, `price`, `stops`, `airlines`, and `source`.

For a scout row, `price` is `total_pp_eur`, `stops` is 0, `source` is `manual`, and `fare_label` is `from, no bags`. The leg fares, flight numbers, times, `source_url`, `checked_at`, `checked_at_dublin`, `matched_shortlist`, and `trip_type` ride along. `screenshot_ref` does not. It stays in the CSV.

`weekend` rows go on the weekend boards. `week` rows go on the week boards. Other trip types go on `special_boards`. The homepage has no third toggle, so a Christmas fare shows in the destination table, and the homepage subtitle mentions it when a manual cache is loaded.

Two clocks apply, both counted from `checked_at_utc`:

- After 48 hours the fare is still shown and marked stale ("fare may have changed").
- After 168 hours (7 days) it is left out.
- A trip whose outbound date has already passed is left out.

`MANUAL_FARE_STALE_HOURS` and `MANUAL_FARE_HIDE_HOURS` override those, if set before the script starts. With one or two runs a day, 48 hours means a missed run still shows, with a warning, and a week-old fare does not sit on the board looking current.

How to run it:

- `python manual_fares.py --dry-run` checks the CSV and writes nothing.
- `python manual_fares.py --publish --force` writes `deals_cache.json`.
- `FARE_SOURCE=manual python refresh_deals.py` does the same and does not call FlightAPI. `MANUAL_FARES_CSV` and `MANUAL_FARES_OUT` can point elsewhere.

Unset, `FARE_SOURCE` stays on FlightAPI, which still requires `FLIGHTAPI_KEY` and still uses SerpApi only as the existing fallback. `.github/workflows/refresh_deals.yml` is untouched, so the 05:00 UTC schedule keeps buying FlightAPI fares until someone deliberately switches it.

The live cache today holds 845 fares. A manual file of about 90 rows is far under the existing safety rule (keep the old file if a run would publish less than half). Replacing the board is refused unless `--force` or `FORCE_CACHE_WRITE=1` is set. That is intentional. Turning the flag on by accident must not blank the site.

`app.js` and `generate_pages.py` only add the new lines when a deal has `checked_at` or `fare_label`. Regenerating today's pages from the FlightAPI cache produces the same HTML. Social posters are not changed in this step. They read `deals_cache.json`, so they would quote manual fares only after a forced publish. Do that in a later, deliberate run. The pages under `social/p/` are left as they are.

## 3. Which routes, and how often

Counted from `refresh_deals.py` as of 14 November 2026.

The scanner lists 45 destinations: 33 from Cork and 38 from Dublin, 71 airport-routes in all. It prices 8 weekend anchors and 10 week anchors. That is 1,278 route-and-date combinations before the schedule is applied. The Cork and Dublin schedules skip 276 of those on this date, leaving 1,002 primary queries. Near-term weeks can add up to 212 midweek probes, and each airport can add up to 40 rescue probes. The cache published on 13 November 2026 holds 845 of those fares.

The scout's measured pace is 12–15 seconds to open one route-and-date on ryanair.com, read both Basic Fares, and save a screenshot. About 25 checks took about 5 minutes. There were no captchas in about 40 checks. Aer Lingus is not in that timing. It uses a search form and will be slower. Plan for 50–100 checks a run, and one or two runs a day. That is 50–200 checks a day, not 1,000.

There is no Search Console export in this repo, so this list is not ranked by impressions. It is the scout's winter brief, limited to routes the site already publishes (Beauvais is the one addition, and it is attached to the Paris page). If a Search Console export later disagrees, swap a route in by dropping a date pair. Do not grow past 100 checks a run.

Twenty-two routes, Cork and Dublin unless noted:

- Winter sun, both airports: Faro `FAO`, Malaga `AGP`, Lanzarote `ACE`, Fuerteventura `FUE`, Tenerife South `TFS`, Gran Canaria `LPA`.
- City breaks, both airports: Edinburgh `EDI`, Barcelona `BCN`, Paris Beauvais `BVA`.
- City break, Dublin only: Porto `OPO`.
- Dublin only: Madrid `MAD`, Krakow `KRK`, Athens `ATH`.

Leave these out for the winter:

- Rhodes, Zadar, and Palma. They are seasonal.
- Pisa from Cork. It is seasonal from Cork. Dublin–Pisa is not on the priority list either, so it is not in the daily set.
- Izmir. There is no Ryanair route.
- Marrakesh. It is excluded by policy, and the converter rejects `RAK`.

A day that fits the clock:

- Run 1, 44 checks: each of the 22 routes, the nearest weekend (2 nights) and the nearest week (7 nights). At 12–15 seconds that is about 9–11 minutes of page reading, inside one run of 50.
- Run 2, another 44: the following weekend and the following week. Together that is 88 checks, about 18–22 minutes, inside a 100-check cap, plus the time to build the shortlist and file the screenshots.
- In late November and December, use one second run for `christmas` instead: the six sun routes from both airports (12) and Edinburgh from both (2). Spend the rest of that run re-checking whatever is actually on the homepage.

Covering the scanner's full 18 date-pairs on these 22 routes would be 396 checks. At 100 a day that takes four days, which is already outside a 48-hour fresh window. The manual board is four date pairs, not eighteen.

Paris on the site today is Charles de Gaulle (`CDG`). The scout checks Beauvais (`BVA`). Those rows use the city name Paris, are labelled Beauvais, and show on the Paris page as "Cork → Beauvais" or "Dublin → Beauvais". They are not stored as CDG.

Aer Lingus is allowed by the file format and is not part of the daily 88. Time about five hand checks on the search form before any Aer Lingus route takes a Ryanair slot. Bristol from Cork is the obvious candidate, and it is not in the winter list yet.

## 4. What the site shows, and the trade-offs

On a deal that carries `checked_at`, the homepage card and the trip guide say when it was read, for example "Checked on ryanair.com 3 hours ago (13 Nov 2026, 18:05 Dublin)". The price caption is "from, no bags" instead of "per person". A stale fare adds "fare may have changed". FlightAPI deals do not have these fields, so their cards stay as they are.

Destination pages and route pages get the same facts in the price cell: "from, no bags", and "Checked on ryanair.com" with the Dublin time. A small script on those pages refreshes the "3 hours ago" phrase from the stored UTC time. It does not load analytics. The consent bar and `consent.js` are unchanged, so GA4 stays behind consent.

### Could the Ryanair shortlist feed the site on its own?

The scout's first step reads Ryanair's public fare data: the cheapest return by route and date, with no login. The second step opens each shortlisted fare on ryanair.com and reads the Basic Fare. In the checks so far, the page agreed with the shortlist within €0.50, and about 40 opens produced no captcha.

That is evidence the shortlist often matches the Basic Fare. It is not permission to republish it.

Ryanair's website terms restrict automated access and the reuse of what is on the site. A fare table their own pages request is still their service. Seeing no captcha is not a licence. Aer Lingus's terms also restrict unauthorised automated use, and that path has not been measured.

Publishing the shortlist, and using a person only to confirm the fares that happen to be on the homepage, would cover more dates for the same 50–100 opens. It would also make the site a mirror of an automated extract, and the figure might not be the Basic Fare the "from, no bags" label promises. This plan does not do that. The shortlist is an internal queue. The published price is the Basic Fare from the page that was opened. `matched_shortlist` records whether the two agreed. If they do not, the page price is the one that is stored, and the flag is false. There is no Ryanair client in this change. Doing the other model needs a written licence, or an explicit decision that the terms risk is accepted. It should not be slipped in as a convenience.

### The other trade-offs

- Coverage. 88 fresh manual fares against 845 stored fares, and against about 1,000 primary queries. London, Alicante, Milan, and most of the current board are absent from the daily list. After a forced switch, `generate_pages.py` would rebuild those pages from whatever is in the cache. A city with no manual row becomes the existing empty-fare page, which already refuses to invent a price. Until that forced publish, the FlightAPI pages stay.
- Staleness. FlightAPI refreshes the whole board every few days. A manual fare is a point in time. The 48-hour flag and the 7-day cutoff are how the site says so. A fare can still move between checks. The label is "from, no bags", not a promise that the same seat is still there.
- Time. Two runs is on the order of 20–40 minutes of opening pages, before shortlisting and filing screenshots. Aer Lingus will add to that. This is a person or an assistant doing a repeated task, not a credit on an invoice.
- Consistency. One fare brand (Basic, 1 adult, taxes in, no bag), one screenshot per row, Cork and Dublin only. That is more specific than "cheapest direct" from FlightAPI, which can be a different bundle. It is also narrower, and two checkers can still mis-read a fee. The screenshot is how that gets caught.
- Destination pages. They keep working. A manual row adds the checked time and the no-bags label. Cities outside the 22 routes keep their last FlightAPI table until someone publishes a manual cache over the top. Route pages use the same table, so they gain the same line.
- Social posts. `social/generate_posts.py` will quote whatever `deals_cache.json` contains. This change does not rebuild posters and does not edit `social/p/`. Publish manual fares first, then decide whether the next poster run should use them.
- Price accuracy. The number is the fare that was on the airline page at `checked_at`, without a bag. Someone who adds a cabin bag will pay more. The card has to keep saying "from, no bags", or the figure is misleading.

## What is deliberately not in this change

- The scheduled workflow, and any spend on FlightAPI.
- A client that fetches Ryanair or Aer Lingus fares.
- Real prices. The only filled CSV is the EXAMPLE fixture, and it cannot be written to the live cache.
- Edits under `social/p/`.
- Any change to the consent gate around GA4.
