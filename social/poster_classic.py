"""Classic poster layouts (navy/gold, matches the site) in two themes: 'navy' and 'ivory'.
Feed 1080x1080, Story 1080x1920. Every poster has: slogan strip, price hook, 'Plan the rest' row, Visit button."""
from parts import e, BTN, SITE, plan_row, slogan_fs

FONTS = """
@font-face{font-family:Fraunces;font-weight:700;src:url(../assets/fonts/fraunces-latin-700-normal.woff2)}
@font-face{font-family:Fraunces;font-weight:900;font-style:italic;src:url(../assets/fonts/fraunces-latin-900-italic.woff2)}
@font-face{font-family:Inter;font-weight:400;src:url(../assets/fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:Inter;font-weight:600;src:url(../assets/fonts/inter-latin-600-normal.woff2)}
@font-face{font-family:Inter;font-weight:800;src:url(../assets/fonts/inter-latin-800-normal.woff2)}
"""
V = {
    "feed": dict(H=1080, top=210, logo=132, pillf=26, pad=64, strip=70, slogan=38, eb=22, route=84, price=230, small=36,
                 dates=46, cardc=56, cardp=110, h=62, btn=34, note=21, foot=44, plan=26, ico=50, plan_bot=176, card_min=140),
    "story": dict(H=1920, top=430, logo=170, pillf=34, pad=64, strip=110, slogan=54, eb=34, route=100, price=290, small=44,
                  dates=64, cardc=74, cardp=140, h=80, btn=50, note=24, foot=250, plan=30, ico=70, plan_bot=500, card_min=280),
}
INK, GOLD, GOLD2 = "#0A1B2E", "#C9A24B", "#E4D2A0"


def css(fmt, theme):
    v = V[fmt]; st = fmt == "story"; ivory = theme == "ivory"
    bg = "#FBF8F1" if ivory else INK
    ph_h = 960
    return FONTS + f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:{v['H']}px;background:{bg};font-family:Inter,sans-serif;color:#FBF8F1;position:relative;overflow:hidden}}
.top{{position:absolute;left:0;top:0;right:0;height:{v['top']}px;background:#FBF8F1;display:flex;{'flex-direction:column;justify-content:flex-end;gap:22px;padding-bottom:34px;' if st else 'justify-content:space-between;'}align-items:center;{'' if st else 'padding:0 64px;'}}}
.top img{{height:{v['logo']}px}}
.pill{{font:600 {v['pillf']}px Inter;letter-spacing:.14em;text-transform:uppercase;color:{INK};border:3px solid {GOLD};border-radius:60px;padding:{16 if st else 14}px 30px}}
.pill i{{font-style:normal;color:{GOLD}}}
.photo,.shade{{position:absolute;left:0;right:0;top:{v['top']}px;{f'height:{ph_h}px' if st else 'bottom:0'}}}
.photo{{background-size:cover;background-position:center}}
.shade{{background:linear-gradient(180deg,rgba(10,27,46,.5) 0%,rgba(10,27,46,.35) 35%,rgba(10,27,46,.88) {100 if st else 80}%,rgba(10,27,46,.96) 100%)}}
.strip{{position:absolute;left:0;right:0;top:{v['top']}px;height:{v['strip']}px;background:{GOLD};color:{INK};display:flex;align-items:center;justify-content:center;
  font:900 italic {v['slogan']}px Fraunces,serif;z-index:6;text-align:center;padding:0 30px;line-height:1.05}}
.main{{position:absolute;left:{v['pad']}px;right:{v['pad']}px;top:{v['top']+v['strip']+(26 if st else 18)}px;bottom:{v['foot']+(v['H']-v['plan_bot']-v['foot']-v['ico']) - v['foot'] + 0 if False else (v['plan_bot']+v['ico']+16)}px;display:flex;flex-direction:column;z-index:2;color:#FBF8F1;overflow:visible}}
.eyebrow{{font:600 {v['eb']}px Inter;letter-spacing:.16em;text-transform:uppercase;color:{GOLD}}}
.route{{font:700 {v['route']}px/1.05 Fraunces,serif;margin-top:{14}px}}.route span,.h span{{color:{GOLD}}}
.price{{font:700 {v['price']}px/1 Fraunces,serif;color:{GOLD2};margin-top:{16 if not st else 30}px;letter-spacing:-.02em;display:flex;align-items:flex-end;gap:24px}}
.price small{{font:400 {v['small']}px/1.25 Inter;color:#FBF8F1;letter-spacing:0;padding-bottom:{30 if not st else 50}px;white-space:nowrap}}
.dates{{font:600 {v['dates']}px Inter;margin-top:{12 if not st else 28}px}}
.h{{font:700 {v['h']}px/1.08 Fraunces,serif;margin-top:6px}}
.card{{position:relative;overflow:hidden;background-size:cover;background-position:center;min-height:{v['card_min']}px;border-radius:26px;padding:16px 40px;display:flex;justify-content:space-between;align-items:center;margin-top:{18 if not st else 24}px;background-color:#1C3148}}
.card:before{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,27,46,.92) 0%,rgba(10,27,46,.72) 38%,rgba(10,27,46,.18) 78%,rgba(10,27,46,.3) 100%)}}
.card>*{{position:relative}}
.card .c{{font:700 {v['cardc']}px/1.1 Fraunces,serif;color:#FBF8F1}}.card .c div{{font:400 {28 if not st else 36}px Inter;color:{GOLD2};margin-top:6px}}
.card .p{{font:700 {v['cardp']}px/1 Fraunces,serif;color:{GOLD2};text-align:right;text-shadow:0 2px 14px rgba(10,27,46,.85)}}.card .p div{{font:400 {22 if not st else 30}px Inter;color:#FBF8F1;margin-top:4px}}
.plan{{position:absolute;left:{v['pad']}px;right:{v['pad']}px;bottom:{v['plan_bot']}px;z-index:5;display:flex;justify-content:{'space-between' if st else 'space-between'};align-items:center}}
.plan .lbl{{font:600 {20 if not st else 26}px Inter;letter-spacing:.12em;color:{'#7a5d18' if ivory else GOLD2};text-transform:uppercase;{'display:none' if st else ''}}}
.foot{{position:absolute;left:{v['pad']}px;right:{v['pad']}px;bottom:{v['foot']}px;z-index:3;display:flex;{'flex-direction:column;align-items:center;gap:22px' if st else 'justify-content:space-between;align-items:center;border-top:3px solid '+GOLD+';padding-top:20px'}}}
.note{{font:400 {v['note']}px/1.35 Inter;color:{'#4a5d73' if ivory else GOLD2};{'max-width:430px' if not st else 'text-align:center'}}}
.btn{{background:linear-gradient(180deg,#E4C26A,{GOLD});color:{INK};font:700 {v['btn']}px Fraunces,serif;border-radius:60px;padding:{16 if not st else 26}px {34 if not st else 0}px;box-shadow:0 5px 0 #8a6a1c;white-space:nowrap;{'width:100%;text-align:center' if st else ''}}}
"""


def _shell(fmt, theme, ctx, body, note, slogan, bg, credit, extra=""):
    v = V[fmt]
    ivory = theme == "ivory"
    photo = f"<div class=photo style=\"background-image:url('{bg}')\"></div><div class=shade></div>" if bg else ""
    fs = slogan_fs(slogan, v["slogan"], 1000)
    plan = plan_row("#0A1B2E" if ivory else "#FBF8F1", v["plan"], v["ico"])
    return (f"<!doctype html><meta charset=utf-8><style>{css(fmt, theme)}.strip{{font-size:{fs}px}}</style><body>"
            f"<div class=top><img src=../assets/logo.png><div class=pill><i>✈</i> Flights from {e(ctx)}</div></div>"
            f"{photo}{extra}<div class=strip>{e(slogan)}</div><div class=main>{body}</div>"
            f"<div class=plan><span class=lbl>Plan the rest</span>{plan}</div>"
            f"<div class=foot><span class=note>{e(note + (' · ' + credit if credit else ''))}</span><div class=btn>{BTN}</div></div></body>")


def hero(fmt, theme, c, origin, photo, note, dates, how, slogan):
    airline = f" · {c['airline']} {how}" if c.get("airline") else f" · {how}"
    if theme == "ivory":
        return hero_ivory(fmt, c, origin, photo, note, dates, airline, slogan)
    body = (f"<div class=eyebrow>Return flight{e(airline)}</div><div class=route>{e(origin)} <span>→</span> {e(c['city'])}</div>"
            f"<div class=price>€{c['price']}<small>per person<br>return flight</small></div><div class=dates>{e(dates)}</div>")
    return _shell(fmt, theme, origin, body, note, slogan, photo, "Photo: Wikimedia Commons" if photo else "")


def cards(fmt, theme, cs, origin, photos, note, sub, slogan):
    out = ""
    for c, ph in zip(cs, photos):
        st = f" style=\"background-image:url('{ph}')\"" if ph else ""
        out += (f"<div class=card{st}><div class=c>{e(c['city'])}<div>{e(c['dates'])}</div></div>"
                f"<div class=p>€{c['price']}<div>per person · return flight</div></div></div>")
    body = f"<div class=h>{e(sub)}<br><span>flights from €{cs[0]['price']}</span></div>{out}"
    credit = "Photos: Wikimedia Commons" if any(photos) else ""
    h = _shell(fmt, theme, origin, body, note, slogan, None, credit)
    if theme == "ivory":
        h = h.replace("</style>", ".main{color:#0A1B2E}.main .card{color:#FBF8F1}</style>", 1)
    return h


def hero_ivory(fmt, c, origin, photo, note, dates, airline, slogan):
    """Ivory page, framed photo on top, navy text below."""
    st = fmt == "story"; v = V[fmt]
    ph_top = v["top"] + v["strip"] + (24 if st else 14)
    ph_h = 340 if st else 230
    t_top = ph_top + ph_h + (24 if st else 12)
    body = (f"<div class=eyebrow style='color:#9a7424'>Return flight{e(airline)}</div>"
            f"<div class=route style='color:#0A1B2E;font-size:{76 if st else 60}px;margin-top:6px'>{e(origin)} <span>→</span> {e(c['city'])}</div>"
            f"<div class=price style='color:#9a7424;font-size:{170 if st else 150}px;margin-top:0'>€{c['price']}<small style='color:#0A1B2E;font-size:{40 if st else 32}px;padding-bottom:{36 if st else 22}px'>per person<br>return flight</small></div>"
            f"<div class=dates style='color:#0A1B2E;font-size:{54 if st else 38}px;margin-top:4px'>{e(dates)}</div>")
    frame = (f"<div style=\"position:absolute;left:48px;right:48px;top:{ph_top}px;height:{ph_h}px;border-radius:28px;"
             f"background:url('{photo}') center/cover,#1C3148;box-shadow:0 10px 30px rgba(10,27,46,.28)\"></div>")
    h = _shell(fmt, "ivory", origin, body, note, slogan, None, "", extra=frame)
    return h.replace("</style>", f".main{{top:{t_top}px!important;color:#0A1B2E}}</style>", 1)


def feature(fmt, theme, items, note, slogan, title=("Your whole trip,", "at a glance.")):
    """No-price 'what the site does' post. items = [(name, text)]"""
    from parts import icon
    st = fmt == "story"; ivory = theme != "navy"
    fg = INK if ivory else "#FBF8F1"; sub = "#4a5d73" if ivory else GOLD2
    bg = ("linear-gradient(180deg,#4fb0ee 0%,#bfe6fb 55%,#f6dca6 100%)" if theme == "bright" else ("#FBF8F1" if ivory else INK))
    rows = "".join(
        f"<div style='display:flex;align-items:center;gap:{30 if st else 22}px;margin-top:{40 if st else 14}px'>"
        f"<span style='width:{110 if st else 72}px;height:{110 if st else 72}px;border:3px solid {fg};border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none'>"
        f"<span style='width:54%;height:54%;display:block'>{icon(n, fg)}</span></span>"
        f"<div><div style='font:800 {54 if st else 36}px Inter;color:{fg}'>{e(n)}</div>"
        f"<div style='font:400 {32 if st else 24}px/1.3 Inter;color:{sub}'>{e(t)}</div></div></div>" for n, t in items)
    H = 1920 if st else 1080
    fs = slogan_fs(slogan, 54 if st else 38, 1000)
    return f"""<!doctype html><meta charset=utf-8><style>{FONTS}@font-face{{font-family:Fraunces;font-weight:700;src:url(../assets/fonts/fraunces-latin-700-normal.woff2)}}
*{{margin:0;padding:0;box-sizing:border-box}}body{{width:1080px;height:{H}px;background:{bg};position:relative;font-family:Inter;overflow:hidden}}
.btn{{position:absolute;left:64px;right:64px;bottom:{250 if st else 44}px;background:linear-gradient(180deg,#E4C26A,{GOLD});color:{INK};font:700 {50 if st else 40}px Fraunces,serif;border-radius:60px;padding:{26 if st else 22}px;text-align:center;box-shadow:0 5px 0 #8a6a1c}}
.strip{{position:absolute;left:0;right:0;top:{430 if st else 200}px;height:{110 if st else 70}px;background:{GOLD};color:{INK};display:flex;align-items:center;justify-content:center;font:900 italic {fs}px Fraunces,serif;text-align:center;padding:0 30px}}
</style><body>
<div style="position:absolute;left:0;right:0;top:0;height:{430 if st else 200}px;background:#FBF8F1;display:flex;align-items:{'flex-end' if st else 'center'};justify-content:center;padding-bottom:{40 if st else 0}px"><img src=../assets/logo.png style="height:{190 if st else 130}px"></div>
<div class=strip>{e(slogan)}</div>
<div style="position:absolute;left:64px;right:64px;top:{600 if st else 296}px;color:{fg}">
<div style="font:700 {104 if st else 64}px/1.05 Fraunces,serif">{e(title[0])}<br><span style="color:{GOLD}">{e(title[1])}</span></div>{rows}</div>
<div class=btn>{BTN}</div>
<div style="position:absolute;left:64px;right:64px;bottom:{(250 if st else 44)+(130 if st else 92)}px;text-align:center;font:400 {26 if st else 20}px Inter;color:{sub}">{e(note)}</div></body>"""
