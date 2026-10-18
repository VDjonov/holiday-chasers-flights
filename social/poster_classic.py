"""Classic poster layouts (navy/gold, matches the site) in two themes: 'navy' and 'ivory'. Feed 1080x1080, Story 1080x1920."""
import html

SITE = "holidaychasers.ie"
FONTS = """
@font-face{font-family:Fraunces;font-weight:700;src:url(../assets/fonts/fraunces-latin-700-normal.woff2)}
@font-face{font-family:Inter;font-weight:400;src:url(../assets/fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:Inter;font-weight:600;src:url(../assets/fonts/inter-latin-600-normal.woff2)}
@font-face{font-family:Inter;font-weight:800;src:url(../assets/fonts/inter-latin-800-normal.woff2)}
"""
V = {
    "feed": dict(H=1080, top=210, logo=132, pillf=26, pad=64, main_top=250, main_bot=200, eb=26, route=92, price=290, small=40,
                 dates=52, badge=28, cardc=58, cardp=120, h=70, btn=34, note=22, foot=44, cta_w=470),
    "story": dict(H=1920, top=430, logo=170, pillf=34, pad=64, main_top=480, main_bot=560, eb=34, route=120, price=290, small=44,
                  dates=66, badge=38, cardc=76, cardp=150, h=92, btn=50, note=28, foot=250, cta_w=952),
}


def e(s):
    return html.escape(str(s))


def css(fmt, theme):
    v = V[fmt]; ivory = theme == "ivory"
    ink, gold, gold2, bg = "#0A1B2E", "#C9A24B", "#E4D2A0", ("#FBF8F1" if ivory else "#0A1B2E")
    txt = ink if ivory else "#FBF8F1"
    price = "#9a7424" if ivory else gold2
    st = fmt == "story"
    return FONTS + f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:{v['H']}px;background:{bg};font-family:Inter,sans-serif;color:{txt};position:relative;overflow:hidden}}
.top{{position:absolute;left:0;top:0;right:0;height:{v['top']}px;background:#FBF8F1;display:flex;{'flex-direction:column;justify-content:flex-end;gap:22px;padding-bottom:34px;' if st else 'justify-content:space-between;'}align-items:center;{'' if st else 'padding:0 64px;'}}}
.top img{{height:{v['logo']}px}}
.pill{{font:600 {v['pillf']}px Inter;letter-spacing:.14em;text-transform:uppercase;color:{ink};border:3px solid {gold};border-radius:60px;padding:{16 if st else 14}px 30px}}
.pill i{{font-style:normal;color:{gold}}}
.photo{{position:absolute;left:0;right:0;top:{v['top']}px;{'height:960px' if st else 'bottom:0'};background-size:cover;background-position:center}}
.shade{{position:absolute;left:0;right:0;top:{v['top']}px;{'height:960px' if st else 'bottom:0'};background:linear-gradient(180deg,rgba(10,27,46,.55) 0%,rgba(10,27,46,.35) 35%,rgba(10,27,46,{.9 if st else .88}) {100 if st else 78}%,rgba(10,27,46,.96) 100%)}}
.main{{position:absolute;left:{v['pad']}px;right:{v['pad']}px;top:{v['main_top']}px;bottom:{v['main_bot']}px;display:flex;flex-direction:column;z-index:2;color:#FBF8F1}}
.eyebrow{{font:600 {v['eb']}px Inter;letter-spacing:.16em;text-transform:uppercase;color:{gold}}}
.route{{font:700 {v['route']}px/1.05 Fraunces,serif;margin-top:18px}}.route span,.h span{{color:{gold}}}
.price{{font:700 {v['price']}px/1 Fraunces,serif;color:{gold2};margin-top:{40 if st else 30}px;letter-spacing:-.02em;display:flex;align-items:flex-end;gap:28px}}
.price small{{font:400 {v['small']}px/1.25 Inter;color:#FBF8F1;letter-spacing:0;padding-bottom:{60 if st else 42}px;white-space:nowrap}}
.dates{{font:600 {v['dates']}px Inter;margin-top:{34 if st else 26}px}}
.badge{{display:inline-block;align-self:flex-start;margin-top:{26 if st else 18}px;font:600 {v['badge']}px Inter;letter-spacing:.1em;text-transform:uppercase;background:{gold};color:{ink};border-radius:50px;padding:12px 28px}}
.h{{font:700 {v['h']}px/1.08 Fraunces,serif;margin-top:16px}}
.card{{position:relative;overflow:hidden;background-size:cover;background-position:center;min-height:{250 if st else 150}px;border-radius:26px;padding:{18}px 40px;display:flex;justify-content:space-between;align-items:center;margin-top:{26 if st else 22}px;background-color:#1C3148}}
.card:before{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,27,46,.92) 0%,rgba(10,27,46,.72) 38%,rgba(10,27,46,.18) 78%,rgba(10,27,46,.3) 100%)}}
.card>*{{position:relative}}
.card .c{{font:700 {v['cardc']}px/1.1 Fraunces,serif;color:#FBF8F1}}.card .c div{{font:400 {30 if not st else 38}px Inter;color:{gold2};margin-top:8px}}
.card .p{{font:700 {v['cardp']}px/1 Fraunces,serif;color:{gold2};text-align:right;text-shadow:0 2px 14px rgba(10,27,46,.85)}}.card .p div{{font:400 {24 if not st else 30}px Inter;color:#FBF8F1;margin-top:4px}}
.foot{{position:absolute;left:{v['pad']}px;right:{v['pad']}px;bottom:{v['foot']}px;z-index:3;display:flex;{'flex-direction:column;align-items:center;gap:22px' if st else 'justify-content:space-between;align-items:center;border-top:3px solid '+gold+';padding-top:20px'}}}
.note{{font:400 {v['note']}px/1.35 Inter;color:{'#4a5d73' if ivory else gold2};{'max-width:420px' if not st else 'text-align:center'}}}
.btn{{background:linear-gradient(180deg,#E4C26A,{gold});color:{ink};font:700 {v['btn']}px Fraunces,serif;border-radius:60px;padding:{16 if not st else 26}px {38 if not st else 0}px;box-shadow:0 5px 0 #8a6a1c;white-space:nowrap;{'width:100%;text-align:center' if st else ''}}}
"""


def _shell(fmt, theme, ctx, body, note, bg, credit):
    v = V[fmt]
    photo = f"<div class=photo style=\"background-image:url('{bg}')\"></div><div class=shade></div>" if bg else ""
    return (f"<!doctype html><meta charset=utf-8><style>{css(fmt, theme)}</style><body>"
            f"<div class=top><img src=../assets/logo.png><div class=pill><i>✈</i> Flights from {e(ctx)}</div></div>"
            f"{photo}<div class=main>{body}</div>"
            f"<div class=foot><span class=note>{e(note + (' · ' + credit if credit else ''))}</span><div class=btn>Visit {SITE} →</div></div></body>")


def hero(fmt, theme, c, origin, photo, note, dates, how):
    airline = f" · {c['airline']} {how}" if c.get("airline") else f" · {how}"
    if theme == "ivory":
        return hero_ivory(fmt, c, origin, photo, note, dates, airline)
    body = (f"<div class=eyebrow>Return flight{e(airline)}</div><div class=route>{e(origin)} <span>→</span> {e(c['city'])}</div>"
            f"<div class=price>€{c['price']}<small>per person<br>return flight</small></div>"
            f"<div class=dates>{e(dates)}</div><div class=badge>✈ Flights only</div>")
    return _shell(fmt, theme, origin, body, note, photo, "Photo: Wikimedia Commons" if photo else "")


def cards(fmt, theme, cs, origin, photos, note, sub):
    out = ""
    for c, ph in zip(cs, photos):
        st = f" style=\"background-image:url('{ph}')\"" if ph else ""
        out += (f"<div class=card{st}><div class=c>{e(c['city'])}<div>{e(c['dates'])}</div></div>"
                f"<div class=p>€{c['price']}<div>per person · return flight</div></div></div>")
    body = (f"<div class=h>{e(sub)}<br><span>flights from €{cs[0]['price']}</span></div>"
            f"{out}<div class=badge>✈ Flights only · no hotel</div>")
    credit = "Photos: Wikimedia Commons" if any(photos) else ""
    h = _shell(fmt, theme, origin, body, note, None, credit)
    if theme == "ivory":
        h = h.replace("</style>", ".main{color:#0A1B2E}</style>")
    return h


def hero_ivory(fmt, c, origin, photo, note, dates, airline):
    """Ivory page, framed photo on top, navy text below."""
    st = fmt == "story"
    ph_top, ph_h = (440, 500) if st else (200, 330)
    t_top = ph_top + ph_h + (30 if st else 18)
    body = (f"<div class=eyebrow style='color:#9a7424'>Return flight{e(airline)}</div>"
            f"<div class=route style='color:#0A1B2E;font-size:{84 if st else 76}px;margin-top:8px'>{e(origin)} <span>→</span> {e(c['city'])}</div>"
            f"<div class=price style='color:#9a7424;font-size:{235 if st else 200}px;margin-top:{10 if st else 0}px'>€{c['price']}<small style='color:#0A1B2E;padding-bottom:{50 if st else 30}px'>per person<br>return flight</small></div>"
            f"<div class=dates style='font-size:{58 if st else 40}px;margin-top:6px'>{e(dates)}</div>")
    h = _shell(fmt, "ivory", origin, body, note, None, "")
    frame = (f"<div style=\"position:absolute;left:48px;right:48px;top:{ph_top}px;height:{ph_h}px;border-radius:28px;"
             f"background:url('{photo}') center/cover,#1C3148;box-shadow:0 10px 30px rgba(10,27,46,.28)\"></div>"
             f"<div style='position:absolute;left:72px;top:{ph_top+ph_h-64}px;background:#C9A24B;color:#0A1B2E;font:600 {32 if st else 24}px Inter;letter-spacing:.1em;"
             f"text-transform:uppace;border-radius:40px;padding:10px 24px'>✈ FLIGHTS ONLY</div>").replace("uppace", "uppercase")
    h = h.replace("<div class=main>", frame + "<div class=main>")
    h = h.replace("</style>", f".main{{top:{t_top}px!important;bottom:{200 if not st else 330}px!important;color:#0A1B2E}}"
                  f".note{{color:#4a5d73}}</style>")
    return h
