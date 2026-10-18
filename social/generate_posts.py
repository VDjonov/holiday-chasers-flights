"""
Build ready-to-post Facebook posts from the live fare cache.

Reads  deals_cache.json  (written by refresh_deals.py)
Writes social/out/<slot>.png   one 1080x1080 poster per post
       social/posts.json       captions + deep links + poster paths

Run after refresh_deals.py. Needs Playwright + Chromium to render posters
(pip install playwright && playwright install chromium).
Nothing is posted automatically: the Chrome extension (or you) posts.
"""
import sys
import json, os, re, datetime as dt, html, shutil, hashlib, io

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
REPO = os.path.dirname(ROOT)
CACHE = os.path.join(REPO, "deals_cache.json")
OUT = os.path.join(ROOT, "out")
BUILD = os.path.join(ROOT, "_build")
SITE = "holidaychasers.ie"
CITIES = os.path.join(ROOT, "assets", "cities")   # <CODE>.jpg; drop your own photo here to override

ORIGIN = {"ORK": "Cork", "DUB": "Dublin"}
SUN = {"ACE", "LPA", "FUE", "TFS", "FAO", "AGP", "ALC", "PMI", "MLA", "SVQ", "VLC"}
UK = {"MAN", "STN", "EDI"}          # cheap, but too common to headline a hero post
MIN_LEAD_DAYS = 7                    # last-minute fares are pricey: skip near dates


def d(s):
    return dt.date.fromisoformat(s)


def fmt_range(a, b):
    a, b = d(a), d(b)
    fa = f"{a.strftime('%a')} {a.day}"
    fb = f"{b.strftime('%a')} {b.day} {b.strftime('%b')}"
    if a.month != b.month:
        fa += f" {a.strftime('%b')}"
    return f"{fa} – {fb}"


def candidates(cache, today):
    """Cheapest fare per (airport, destination, board kind) that is far enough out."""
    best = {}
    for ap, v in cache["airports"].items():
        for kind, key in (("weekend", "weekend_boards"), ("week", "week_boards")):
            for b in v.get(key, []):
                for x in b.get("deals", []):
                    dep = x.get("depart_date") or b["depart_date"]
                    ret = x.get("return_date") or b["return_date"]
                    if (d(dep) - today).days < MIN_LEAD_DAYS or not x.get("price"):
                        continue
                    k = (ap, x["code"], kind)
                    c = dict(ap=ap, kind=kind, code=x["code"], city=x["city"], price=int(x["price"]),
                             dep=dep, ret=ret, stops=x.get("stops", 0), airline=x.get("airlines") or "")
                    if k not in best or c["price"] < best[k]["price"]:
                        best[k] = c
    return list(best.values())


def pick(cands, ap, kinds, n, exclude=(), sun=False, no_uk=False, direct=False):
    pool = [c for c in cands if c["ap"] == ap and c["kind"] in kinds and c["code"] not in exclude]
    if sun:
        pool = [c for c in pool if c["code"] in SUN]
    if no_uk:
        pool = [c for c in pool if c["code"] not in UK]
    if direct:
        pool = [c for c in pool if c["stops"] == 0]
    pool.sort(key=lambda c: (c["price"], c["dep"]))
    out, seen = [], set()
    for c in pool:
        if c["code"] in seen:
            continue
        seen.add(c["code"]); out.append(c)
        if len(out) == n:
            break
    return out


def link(c):
    return f"{SITE}/?dest={c['code']}&from={c['ap']}&utm_source=facebook&utm_medium=social"


# ── city photos ─────────────────────────────────────────────────────────────
def wiki_titles():
    """code -> Wikipedia article title, read from app.js so there is one source of truth."""
    try:
        js = open(os.path.join(REPO, "app.js"), encoding="utf-8").read()
        block = js[js.index("const CITY_WIKI"):]
        block = block[:block.index("};")]
        return dict(re.findall(r'([A-Z]{3}):"([^"]+)"', block))
    except Exception:
        return {}


# Wikipedia's lead image for an island/region is often a satellite shot. Use a nicer article for these.
PHOTO_TITLE = {"ACE": ["Timanfaya_National_Park"], "FUE": ["Corralejo", "Corralejo_Natural_Park", "Playa_de_Sotavento"],
               "TFS": ["Teide_National_Park", "Mount_Teide"]}


def city_photo(code, city):
    """Path to a cached photo for this destination, downloading from Wikipedia once. None if unavailable."""
    path = os.path.join(CITIES, f"{code}.jpg")
    if os.path.exists(path):
        return path
    try:
        import requests
        from PIL import Image
        titles = PHOTO_TITLE.get(code) or [wiki_titles().get(code) or city.replace(" ", "_")]
        hdr = {"User-Agent": "HolidayChasersBot/1.0 (https://holidaychasers.ie; info@holidaychasers.ie)"}
        img = None
        for title in titles:
            try:
                r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(title, safe="_,()"),
                                 headers=hdr, timeout=20)
                r.raise_for_status()
                j = r.json()
                src = (j.get("thumbnail") or {}).get("source") or (j.get("originalimage") or {}).get("source")
                if not src:
                    continue
                src = re.sub(r"/\d+px-", "/1280px-", src)
                img = requests.get(src, headers=hdr, timeout=30)
                img.raise_for_status()
                break
            except Exception as ex:
                print("  photo try failed:", code, title, "-", ex)
                img = None
        if img is None:
            return None
        im = Image.open(io.BytesIO(img.content)).convert("RGB")
        if im.width < 500:                       # too small to look good full-bleed
            return None
        im.thumbnail((1280, 1280))
        os.makedirs(CITIES, exist_ok=True)
        im.save(path, quality=82, optimize=True)
        print("  photo:", code, title, im.size)
        return path
    except Exception as ex:
        print("  no photo for", code, "-", ex)
        return None


def bg_url(code, city):
    p = city_photo(code, city)
    return None if not p else "file://" + p


# ── captions ────────────────────────────────────────────────────────────────
def pickv(seed, options):
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


def caption_hero(c, today):
    o = ORIGIN[c["ap"]]
    tag = pickv(c["code"] + str(today), [
        "Direct flights, per-person fares.",
        "Real fare, checked this week.",
        "Book with the airline in a couple of clicks.",
    ])
    return (f"✈️ Return flights from {o} to {c['city']} from €{c['price']} per person, {fmt_range(c['dep'], c['ret'])}. "
            f"Flights only. {tag} {link(c)}")


def caption_cards(label, cs, today):
    a, b = cs[0], cs[1]
    o = ORIGIN[a["ap"]]
    return (f"✈️ {label}, return flights from {o}: {a['city']} from €{a['price']} per person, {fmt_range(a['dep'], a['ret'])}. "
            f"Or {b['city']} from €{b['price']} ({fmt_range(b['dep'], b['ret'])}). "
            f"Flights only. Fares change, so check the live deal: {link(a)}")


# ── posters ─────────────────────────────────────────────────────────────────
CSS = """
@font-face{font-family:Fraunces;font-weight:700;src:url(../assets/fonts/fraunces-latin-700-normal.woff2)}
@font-face{font-family:Inter;font-weight:400;src:url(../assets/fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:Inter;font-weight:600;src:url(../assets/fonts/inter-latin-600-normal.woff2)}
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1080px;background:#0A1B2E;font-family:Inter,sans-serif;color:#FBF8F1;position:relative;overflow:hidden}
.top{position:absolute;left:0;top:0;right:0;height:210px;background:#FBF8F1;display:flex;align-items:center;justify-content:space-between;padding:0 64px}
.top img{height:132px}
.pill{font:600 26px Inter;letter-spacing:.14em;text-transform:uppercase;color:#0A1B2E;border:3px solid #C9A24B;border-radius:60px;padding:14px 30px}
.main{position:absolute;left:64px;right:64px;top:250px;bottom:170px;display:flex;flex-direction:column}
.eyebrow{font:600 26px Inter;letter-spacing:.16em;text-transform:uppercase;color:#C9A24B}
.route{font:700 92px/1.05 Fraunces,serif;margin-top:18px}.route span,.h span{color:#C9A24B}
.price{font:700 290px/1 Fraunces,serif;color:#E4D2A0;margin-top:30px;letter-spacing:-.02em;display:flex;align-items:flex-end;gap:28px}
.price small{font:400 40px/1.25 Inter;color:#FBF8F1;letter-spacing:0;padding-bottom:42px;white-space:nowrap}
.dates{font:600 52px Inter;margin-top:26px}
.foot{position:absolute;left:64px;right:64px;bottom:44px;border-top:3px solid #C9A24B;padding-top:22px;display:flex;justify-content:space-between;align-items:center;font:400 25px Inter;color:#E4D2A0}
.foot b{font:700 34px Fraunces,serif;color:#FBF8F1}
.card{background:#1C3148;border-radius:26px;padding:18px 40px;display:flex;justify-content:space-between;align-items:center;margin-top:22px}
.card .c{font:700 58px/1.1 Fraunces,serif}.card .c div{font:400 30px Inter;color:#E4D2A0;margin-top:8px}
.card .p{font:700 120px/1 Fraunces,serif;color:#E4D2A0;text-align:right;text-shadow:0 2px 14px rgba(10,27,46,.85)}.card .p div{font:400 24px Inter;color:#FBF8F1;margin-top:4px}
.h{font:700 70px/1.08 Fraunces,serif;margin-top:16px}
.photo{position:absolute;left:0;right:0;top:210px;bottom:0;background-size:cover;background-position:center}
.shade{position:absolute;left:0;right:0;top:210px;bottom:0;background:linear-gradient(180deg,rgba(10,27,46,.55) 0%,rgba(10,27,46,.35) 35%,rgba(10,27,46,.88) 78%,rgba(10,27,46,.96) 100%)}
.main,.foot{z-index:2}
.pill i{font-style:normal;color:#C9A24B}
.badge{display:inline-block;align-self:flex-start;margin-top:18px;font:600 28px Inter;letter-spacing:.1em;text-transform:uppercase;background:#C9A24B;color:#0A1B2E;border-radius:50px;padding:12px 28px}
.card{position:relative;overflow:hidden;background-size:cover;background-position:center;min-height:150px}
.card:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,27,46,.92) 0%,rgba(10,27,46,.72) 38%,rgba(10,27,46,.18) 78%,rgba(10,27,46,.3) 100%)}
.card>*{position:relative}
.credit{font:400 17px Inter;color:#E4D2A0;opacity:.75;position:absolute;right:64px;bottom:12px;z-index:2}
"""


def page(note, ctx, body, bg=None):
    photo = f"<div class=photo style=\"background-image:url('{bg}')\"></div><div class=shade></div>" if bg else ""
    credit = "<div class=credit>Photo: Wikimedia Commons</div>" if bg else ""
    return (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>"
            f"<div class=top><img src=../assets/logo.png><div class=pill><i>✈</i> Flights from {html.escape(ctx)}</div></div>"
            f"{photo}<div class=main>{body}</div>"
            f"<div class=foot><b>{SITE}</b><span>{html.escape(note)}</span></div>{credit}</body>")


def e(s):
    return html.escape(str(s))


DESIGNS = ("classic", "ivory", "bright")
DESIGN_LABEL = {"classic": "Classic navy", "ivory": "Ivory", "bright": "Bright photo"}


def posters_hero(c, note):
    import poster_v2 as P, poster_classic as C
    o = ORIGIN[c["ap"]]
    how = "direct" if c["stops"] == 0 else f"{c['stops']} stop"
    label = "Weekend break" if c["kind"] == "weekend" else "A week away"
    ph = bg_url(c["code"], c["city"]); dates = fmt_range(c["dep"], c["ret"])
    out = {}
    for f in ("feed", "story"):
        out[("classic", f)] = C.hero(f, "navy", c, o, ph, note, dates, how)
        out[("ivory", f)] = C.hero(f, "ivory", c, o, ph, note, dates, how)
        out[("bright", f)] = P.hero(f, c, o, ph, note, dates, how, label)
    return out


def posters_cards(sub, cs, note):
    import poster_v2 as P, poster_classic as C
    cs2 = [dict(c, dates=fmt_range(c["dep"], c["ret"])) for c in cs]
    photos = [bg_url(c["code"], c["city"]) for c in cs]
    o = ORIGIN[cs[0]["ap"]]
    out = {}
    for f in ("feed", "story"):
        out[("classic", f)] = C.cards(f, "navy", cs2, o, photos, note, sub)
        out[("ivory", f)] = C.cards(f, "ivory", cs2, o, photos, note, sub)
        out[("bright", f)] = P.cards(f, cs2, o, photos, note, sub)
    return out


# ── main ────────────────────────────────────────────────────────────────────
def build(today=None):
    cache = json.load(open(CACHE, encoding="utf-8"))
    today = today or dt.date.today()
    scanned = cache.get("updated_utc", "")[:10]
    note = "Return flights only · per person · scanned " + (d(scanned).strftime("%-d %b") if scanned else "recently")
    cands = candidates(cache, today)

    posts, pages = [], {}

    def add(slot, kind, cs, caption, html_):
        posters = {}
        for (des, f), h in html_.items():
            name = f"{slot}_{des}" + ("_story" if f == "story" else "")
            pages[name] = h
            posters.setdefault(des, {})[f] = f"social/out/{name}.png"
        posts.append(dict(id=slot, type=kind, airport=cs[0]["ap"], caption=caption, link=link(cs[0]),
                          poster=posters["classic"]["feed"], story=posters["classic"]["story"], posters=posters, deals=cs,
                          expires=min(c["dep"] for c in cs)))

    used = set()
    for ap in ("ORK", "DUB"):
        h = pick(cands, ap, ("weekend", "week"), 1, no_uk=True, direct=True)
        if h:
            c = h[0]; used.add((ap, c["code"]))
            add(f"hero_{ap.lower()}", "hero", h, caption_hero(c, today), posters_hero(c, note))

    for ap, slot, kinds, sun, label, eyebrow, headline in (
        ("ORK", "sun_ork", ("weekend", "week"), True, "Winter sun", "Cork winter sun", "Warm escapes,"),
        ("ORK", "week_ork", ("week",), False, "A week away", "A week away from Cork", "Seven nights,"),
        ("DUB", "sun_dub", ("weekend", "week"), True, "Winter sun", "Dublin winter sun", "Warm escapes,"),
        ("DUB", "week_dub", ("week",), False, "A week away", "A week away from Dublin", "Seven nights,"),
    ):
        ex = {code for (a, code) in used if a == ap}
        cs = pick(cands, ap, kinds, 2, exclude=ex, sun=sun, direct=True)
        if len(cs) < 2:
            cs = pick(cands, ap, kinds, 2, sun=sun, direct=True)
        if len(cs) == 2:
            add(slot, "cards", cs, caption_cards(label, cs, today), posters_cards(label, cs, note))

    os.makedirs(OUT, exist_ok=True); shutil.rmtree(BUILD, ignore_errors=True); os.makedirs(BUILD)
    for slot, h in pages.items():
        open(os.path.join(BUILD, slot + ".html"), "w", encoding="utf-8").write(h)
    render(list(pages))
    shutil.rmtree(BUILD, ignore_errors=True)

    # evergreen posts (no prices, never go stale)
    ev = [
        dict(id="how_it_works", type="evergreen", airport=None, poster="social/evergreen/how_it_works.png",
             caption=f"We check real fares every few days for Cork and Dublin. We show per-person return prices and send you to the airline to book. No sign-up. Prices are indicative and confirmed when you book. {SITE}",
             link=SITE, deals=[], expires=None),
        dict(id="question", type="evergreen", airport=None, poster="social/evergreen/question.png",
             caption="Where would you fly this winter: sun or a city break? Tell us and we will check the fares.",
             link=None, deals=[], expires=None),
    ]
    json.dump(dict(generated=today.isoformat(), fares_scanned=scanned, posts=posts + ev),
              open(os.path.join(ROOT, "posts.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"{len(posts)} deal posts + {len(ev)} evergreen -> social/posts.json")
    for p in posts:
        print(" ", p["id"], "|", p["caption"][:100])


def render(slots):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("PW_CHROMIUM")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        for s in slots:
            pg = b.new_page(viewport={"width": 1080, "height": 1920 if s.endswith("_story") else 1080})
            pg.goto("file://" + os.path.join(BUILD, s + ".html"))
            pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(OUT, s + ".png"))
            pg.close()
        b.close()


if __name__ == "__main__":
    build()
