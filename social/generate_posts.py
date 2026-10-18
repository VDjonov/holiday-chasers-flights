"""
Build ready-to-post Facebook posts from the live fare cache.

Reads  deals_cache.json  (written by refresh_deals.py)
Writes social/out/<slot>.png   one 1080x1080 poster per post
       social/posts.json       captions + deep links + poster paths

Run after refresh_deals.py. Needs Playwright + Chromium to render posters
(pip install playwright && playwright install chromium).
Nothing is posted automatically: the Chrome extension (or you) posts.
"""
import sys, glob
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
            f"The price is for the flight. {tag} Plan the rest on {SITE}: {link(c)}")


def caption_cards(label, cs, today):
    a, b = cs[0], cs[1]
    o = ORIGIN[a["ap"]]
    return (f"✈️ {label}, return flights from {o}: {a['city']} from €{a['price']} per person, {fmt_range(a['dep'], a['ret'])}. "
            f"Or {b['city']} from €{b['price']} ({fmt_range(b['dep'], b['ret'])}). "
            f"Prices are for the flights. Fares change, so check the live deal and plan the rest: {link(a)}")


# ── posters ─────────────────────────────────────────────────────────────────
DESIGNS = ("classic", "ivory", "bright")
DESIGN_LABEL = {"classic": "Classic navy", "ivory": "Ivory", "bright": "Bright photo"}
SHARE_BASE = "https://" + SITE + "/social/"


def load_slogans():
    try:
        return json.load(open(os.path.join(ROOT, "slogans.json"), encoding="utf-8"))["slogans"]
    except Exception:
        return ["Your whole trip, at a glance."]


THEME = {"classic": "navy", "ivory": "ivory", "bright": "bright"}


def posters_hero(c, note, slogan):
    import poster_v2 as P, poster_classic as C, poster_card as K
    o = ORIGIN[c["ap"]]
    how = "direct" if c["stops"] == 0 else f"{c['stops']} stop"
    label = "Weekend break" if c["kind"] == "weekend" else "A week away"
    ph = bg_url(c["code"], c["city"]); dates = fmt_range(c["dep"], c["ret"])
    out = {}
    for f in ("feed", "story"):
        out[("classic", f)] = C.hero(f, "navy", c, o, ph, note, dates, how, slogan)
        out[("ivory", f)] = C.hero(f, "ivory", c, o, ph, note, dates, how, slogan)
        out[("bright", f)] = P.hero(f, c, o, ph, note, dates, how, label, slogan)
    for des, th in THEME.items():
        out[(des, "card")] = K.hero(th, c, o, ph, dates, slogan)
    return out


def posters_cards(sub, cs, note, slogan):
    import poster_v2 as P, poster_classic as C, poster_card as K
    cs2 = [dict(c, dates=fmt_range(c["dep"], c["ret"])) for c in cs]
    photos = [bg_url(c["code"], c["city"]) for c in cs]
    o = ORIGIN[cs[0]["ap"]]
    out = {}
    for f in ("feed", "story"):
        out[("classic", f)] = C.cards(f, "navy", cs2, o, photos, note, sub, slogan)
        out[("ivory", f)] = C.cards(f, "ivory", cs2, o, photos, note, sub, slogan)
        out[("bright", f)] = P.cards(f, cs2, o, photos, note, sub, slogan)
    for des, th in THEME.items():
        out[(des, "card")] = K.cards(th, cs2, o, photos, sub, slogan)
    return out


FEATURES = {
    "trip_glance": dict(
        title=("Your whole trip,", "at a glance."),
        items=[("Flights", "Fares scanned every few days"), ("Stays", "Find somewhere to sleep near your flight"),
               ("Car hire", "Pick up at the airport"), ("Events", "Tickets for what\u2019s on while you\u2019re there")],
        caption=f"Your whole trip, at a glance. Flights, stays, car hire and event tickets, all in one place. Find the fare, then plan the rest on {SITE}",
    ),
}


def posters_feature(key, note, slogan):
    import poster_classic as C, poster_card as K
    F = FEATURES[key]
    out = {}
    for f in ("feed", "story"):
        for des, theme in (("classic", "navy"), ("ivory", "ivory"), ("bright", "bright")):
            out[(des, f)] = C.feature(f, theme, F["items"], note, slogan, F["title"])
    for des, th in THEME.items():
        out[(des, "card")] = K.feature(th, F["items"], slogan, F["title"])
    return out


def make_card(png_path, jpg_path):
    """1200x630 link-preview image: the square poster centred on a blurred copy of itself."""
    from PIL import Image, ImageFilter, ImageEnhance
    im = Image.open(png_path).convert("RGB")
    bg = im.resize((1200, 1200)).crop((0, 285, 1200, 915)).filter(ImageFilter.GaussianBlur(26))
    bg = ImageEnhance.Brightness(bg).enhance(.7)
    fg = im.resize((630, 630))
    bg.paste(fg, (285, 0))
    bg.save(jpg_path, quality=88, optimize=True)


def share_page(path, title, desc, image_url, target):
    """Tiny page Facebook scrapes for a clickable preview card (poster image + title). People are sent on to the site."""
    t = html.escape(title, quote=True); dsc = html.escape(desc, quote=True)
    target_js = json.dumps(target)
    open(path, "w", encoding="utf-8").write(
        f"<!doctype html><html lang=en><head><meta charset=utf-8><title>{t}</title>"
        f"<meta name=robots content=noindex><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<meta property=og:type content=website><meta property=og:site_name content='Holiday Chasers'>"
        f"<meta property=og:title content=\"{t}\"><meta property=og:description content=\"{dsc}\">"
        f"<meta property=og:image content=\"{image_url}\"><meta property=og:image:width content=1200><meta property=og:image:height content=630>"
        f"<meta name=twitter:card content=summary_large_image></head><body style='font-family:sans-serif;text-align:center;padding:40px'>"
        f"<script>location.replace({target_js})</script><p>Taking you to <a href={target_js}>holidaychasers.ie</a>…</p></body></html>")


# ── main ────────────────────────────────────────────────────────────────────
def build(today=None):
    cache = json.load(open(CACHE, encoding="utf-8"))
    today = today or dt.date.today()
    scanned = cache.get("updated_utc", "")[:10]
    note = "Price is for the flight only · per person · scanned " + (d(scanned).strftime("%-d %b") if scanned else "recently")
    cands = candidates(cache, today)
    import random
    sl = load_slogans(); random.Random(today.toordinal()).shuffle(sl)
    nxt = iter(sl * 3)

    posts, pages = [], {}
    SHARES = []

    def add(slot, kind, cs, caption, html_, link_url, title, desc):
        posters = {}
        for (des, f), h in html_.items():
            name = f"{slot}_{des}" + {"story": "_story", "card": "_card", "feed": ""}[f]
            pages[name] = h
            if f != "card":
                posters.setdefault(des, {})[f] = f"social/out/{name}.png"
        for des in posters:
            posters[des]["card"] = f"social/card/{slot}_{des}.jpg"
            posters[des]["share"] = f"{SHARE_BASE}p/{slot}_{des}.html?v={today.strftime('%m%d')}"
            SHARES.append((slot, des, title, desc, link_url))
        posts.append(dict(id=slot, type=kind, airport=cs[0]["ap"] if cs else None, caption=caption, link=link_url.replace("https://", ""),
                          poster=posters["classic"]["feed"], story=posters["classic"]["story"], posters=posters, deals=cs,
                          expires=min(c["dep"] for c in cs) if cs else None))

    used = set()
    DESC = "Flights, stays, car hire and events: plan your whole trip on holidaychasers.ie"
    for ap in ("ORK", "DUB"):
        h = pick(cands, ap, ("weekend", "week"), 1, no_uk=True, direct=True)
        if h:
            c = h[0]; used.add((ap, c["code"]))
            add(f"hero_{ap.lower()}", "hero", h, caption_hero(c, today), posters_hero(c, note, next(nxt)),
                "https://" + link(c), f"{ORIGIN[ap]} to {c['city']} from €{c['price']} return per person", DESC)

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
            add(slot, "cards", cs, caption_cards(label, cs, today), posters_cards(label, cs, note, next(nxt)),
                "https://" + link(cs[0]), f"{label} from {ORIGIN[ap]}: {cs[0]['city']} from €{cs[0]['price']}, {cs[1]['city']} from €{cs[1]['price']}", DESC)

    for key, F in FEATURES.items():
        add(key, "feature", [], F["caption"], posters_feature(key, "Plan the rest on " + SITE, next(nxt)),
            "https://" + SITE + "/?utm_source=facebook&utm_medium=social", "Holiday Chasers: your whole trip, at a glance", DESC)

    os.makedirs(OUT, exist_ok=True); shutil.rmtree(BUILD, ignore_errors=True); os.makedirs(BUILD)
    for f in glob.glob(os.path.join(OUT, "*.png")):
        os.remove(f)
    shutil.rmtree(os.path.join(ROOT, "card"), ignore_errors=True)
    for slot, h in pages.items():
        open(os.path.join(BUILD, slot + ".html"), "w", encoding="utf-8").write(h)
    render(list(pages))
    shutil.rmtree(BUILD, ignore_errors=True)

    # link-preview cards + share pages (clickable poster when posted as a link)
    pdir = os.path.join(ROOT, "p")
    shutil.rmtree(pdir, ignore_errors=True); os.makedirs(pdir)
    for slot, des, title, desc, target in SHARES:
        share_page(os.path.join(pdir, f"{slot}_{des}.html"), title, desc, f"{SHARE_BASE}card/{slot}_{des}.jpg", target)

    # evergreen posts (no prices, never go stale)
    ev = [
        dict(id="how_it_works", type="evergreen", airport=None, poster="social/evergreen/how_it_works.png",
             caption=f"We check real fares every few days for Cork and Dublin. We show per-person return prices and send you to the airline to book. No sign-up. Prices are indicative and confirmed when you book. {SITE}",
             link=SITE, deals=[], expires=None),
        dict(id="question", type="evergreen", airport=None, poster="social/evergreen/question.png",
             caption="Where would you fly this winter: sun or a city break? Tell us and we will check the fares.",
             link=None, deals=[], expires=None),
    ]
    json.dump(dict(generated=today.isoformat(), fares_scanned=scanned, designs=DESIGN_LABEL, posts=posts + ev),
              open(os.path.join(ROOT, "posts.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"{len(posts)} posts + {len(ev)} evergreen -> social/posts.json")
    for p in posts:
        print(" ", p["id"], "|", p["caption"][:100])


def render(slots):
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("PW_CHROMIUM")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        os.makedirs(os.path.join(ROOT, "card"), exist_ok=True)
        for s in slots:
            card = s.endswith("_card")
            pg = b.new_page(viewport={"width": 1200, "height": 630} if card else {"width": 1080, "height": 1920 if s.endswith("_story") else 1080})
            pg.goto("file://" + os.path.join(BUILD, s + ".html"))
            pg.wait_for_timeout(500)
            if card:
                pg.screenshot(path=os.path.join(ROOT, "card", s[:-5] + ".jpg"), type="jpeg", quality=90)
            else:
                pg.screenshot(path=os.path.join(OUT, s + ".png"))
            pg.close()
        b.close()


if __name__ == "__main__":
    build()
