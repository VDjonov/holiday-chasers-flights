"""1200x630 landscape link-preview cards (what Facebook shows for a link post). Photo left, price and button right."""
from parts import e, BTN, plan_row, slogan_fs
from poster_classic import FONTS, INK, GOLD, GOLD2

T = {
    "navy":   dict(bg=INK, fg="#FBF8F1", price=GOLD2, sub="#E4D2A0", plan="#FBF8F1", fade="10,27,46"),
    "ivory":  dict(bg="#FBF8F1", fg=INK, price="#9a7424", sub="#4a5d73", plan=INK, fade="251,248,241"),
    "bright": dict(bg="linear-gradient(180deg,#4fb0ee,#bfe6fb 70%,#f6dca6)", fg=INK, price="#F2B722", sub=INK, plan=INK, fade="120,190,240"),
}


def _base(theme, slogan, left, right):
    t = T[theme]; fs = slogan_fs(slogan, 30, 1100)
    price_stroke = "-webkit-text-stroke:5px #0A1B2E;paint-order:stroke fill;" if theme == "bright" else ""
    return f"""<!doctype html><meta charset=utf-8><style>{FONTS}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1200px;height:630px;background:{t['bg']};color:{t['fg']};font-family:Inter,sans-serif;position:relative;overflow:hidden}}
.strip{{position:absolute;left:0;right:0;top:0;height:56px;background:{GOLD};color:{INK};display:flex;align-items:center;justify-content:center;font:900 italic {fs}px Fraunces,serif;z-index:5}}
.left{{position:absolute;left:0;top:56px;bottom:0;width:520px;background-size:cover;background-position:center;background-color:#1C3148}}
.left:after{{content:"";position:absolute;right:0;top:0;bottom:0;width:140px;background:linear-gradient(90deg,rgba({t['fade']},0),rgba({t['fade']},{1 if theme!='bright' else .0}))}}
.logo{{position:absolute;left:22px;top:76px;background:#FBF8F1;border-radius:16px;padding:6px 12px;z-index:3}}.logo img{{height:60px;display:block}}
.right{{position:absolute;left:520px;right:0;top:56px;bottom:0;padding:26px 40px 26px 30px;display:flex;flex-direction:column;z-index:3}}
.pill{{font:600 20px Inter;letter-spacing:.14em;text-transform:uppercase;color:{GOLD if theme=='navy' else '#7a5d18'}}}
.route{{font:700 48px/1.08 Fraunces,serif;margin-top:8px}}
.price{{font:700 180px/1 Fraunces,serif;color:{t['price']};margin-top:6px;letter-spacing:-.02em;display:flex;align-items:flex-end;gap:18px;{price_stroke}}}
.price small{{font:600 30px/1.25 Inter;color:{t['fg']};letter-spacing:0;padding-bottom:32px;white-space:nowrap;-webkit-text-stroke:0}}
.dates{{font:600 32px Inter;margin-top:2px}}
.plan{{display:flex;gap:14px;margin-top:auto;margin-bottom:14px}}
.btn{{background:linear-gradient(180deg,{'#FFD84D,#F5B800' if theme=='bright' else '#E4C26A,'+GOLD});color:{INK};font:700 34px Fraunces,serif;border-radius:60px;padding:14px 0;text-align:center;box-shadow:0 4px 0 {'#b98700' if theme=='bright' else '#8a6a1c'}}}
</style><body><div class=strip>{e(slogan)}</div>{left}{right}</body>"""


def hero(theme, c, origin, photo, dates, slogan):
    t = T[theme]
    left = f"<div class=left style=\"background-image:url('{photo}')\"></div><div class=logo><img src=../assets/logo.png></div>" if photo else \
           "<div class=left></div><div class=logo><img src=../assets/logo.png></div>"
    plan = plan_row(t["plan"], 20, 34)
    right = (f"<div class=right><div class=pill>Flights from {e(origin)} · return</div>"
             f"<div class=route>{e(origin)} → {e(c['city'])}</div>"
             f"<div class=price>€{c['price']}<small>per person<br>return flight</small></div>"
             f"<div class=dates>{e(dates)}</div><div class=plan>{plan}</div><div class=btn>{BTN}</div></div>")
    return _base(theme, slogan, left, right)


def cards(theme, cs, origin, photos, sub, slogan):
    t = T[theme]
    h = 285
    left = ""
    for i, (c, ph) in enumerate(zip(cs, photos)):
        top = 56 + i * (h + 4)
        bg = f"background-image:linear-gradient(180deg,rgba(10,27,46,0) 45%,rgba(10,27,46,.75)),url('{ph}');" if ph else "background:#1C3148;"
        left += (f"<div style=\"position:absolute;left:0;top:{top}px;width:520px;height:{h}px;background-size:cover;background-position:center;{bg}\">"
                 f"<div style='position:absolute;left:24px;bottom:16px;font:700 40px Fraunces,serif;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.7)'>{e(c['city'])}"
                 f"<div style='font:600 22px Inter'>{e(c['dates'])}</div></div></div>")
    left += "<div class=logo><img src=../assets/logo.png></div>"
    rows = "".join(f"<div style='display:flex;justify-content:space-between;align-items:flex-end;margin-top:6px'>"
                   f"<div style='font:700 40px Fraunces,serif'>{e(c['city'])}</div>"
                   f"<div style='font:700 96px/1 Fraunces,serif;color:{t['price']};{'-webkit-text-stroke:4px #0A1B2E;paint-order:stroke fill;' if theme=='bright' else ''}'>€{c['price']}</div></div>" for c in cs)
    plan = plan_row(t["plan"], 20, 34)
    right = (f"<div class=right><div class=pill>{e(sub)} · from {e(origin)}</div>{rows}"
             f"<div style='font:600 24px Inter;margin-top:4px'>per person · return flight</div>"
             f"<div class=plan>{plan}</div><div class=btn>{BTN}</div></div>")
    return _base(theme, slogan, left, right)


def feature(theme, items, slogan, title=("Your whole trip,", "at a glance.")):
    from parts import icon
    t = T[theme]
    rows = "".join(f"<div style='display:flex;align-items:center;gap:14px;margin-top:12px'><span style='width:52px;height:52px;border:3px solid {t['fg']};border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none'>"
                   f"<span style='width:54%;height:54%;display:block'>{icon(n, t['fg'])}</span></span><span style='font:800 30px Inter'>{e(n)}</span></div>" for n, _ in items)
    left = "<div class=left style='background:#FBF8F1;display:flex;align-items:center;justify-content:center'><img src=../assets/logo.png style='width:400px'></div>"
    right = (f"<div class=right><div class=route style='font-size:56px'>{e(title[0])}<br><span style='color:{GOLD}'>{e(title[1])}</span></div>{rows}"
             f"<div class=btn style='margin-top:auto'>{BTN}</div></div>")
    return _base(theme, slogan, left, right)
