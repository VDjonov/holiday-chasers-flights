"""Poster layouts v2: bright full-bleed photo, brush banner, torn white price card, navy footer panel.
Two formats: feed (1080x1080) and story (1080x1920, key content kept clear of the top/bottom UI zones)."""
import html

NAVY, GOLD, GOLD2, IVORY = "#0A1B2E", "#C9A24B", "#E4D2A0", "#FBF8F1"
SITE = "holidaychasers.ie"

FONTS = """
@font-face{font-family:Fraunces;font-weight:900;font-style:normal;src:url(../assets/fonts/fraunces-latin-900-normal.woff2)}
@font-face{font-family:Fraunces;font-weight:900;font-style:italic;src:url(../assets/fonts/fraunces-latin-900-italic.woff2)}
@font-face{font-family:Inter;font-weight:400;src:url(../assets/fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:Inter;font-weight:600;src:url(../assets/fonts/inter-latin-600-normal.woff2)}
@font-face{font-family:Inter;font-weight:700;src:url(../assets/fonts/inter-latin-700-normal.woff2)}
@font-face{font-family:Inter;font-weight:800;src:url(../assets/fonts/inter-latin-800-normal.woff2)}
"""

ICON = {
    "plane": '<svg viewBox="0 0 24 24" fill="#fff"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg>',
    "cal": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
    "tag": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"><path d="M3 12V4h8l10 10-8 8L3 12z"/><circle cx="7.5" cy="8.5" r="1.4" fill="#fff"/></svg>',
}

LAY = {
    "feed": dict(H=1080, photo_h=1080, logo_y=14, logo_h=150, ban_y=186, ban_h=150, ban_font=104,
                 card_y=470, card_h=350, card_w=780, panel_y=852, feat_y=886, cta_y=968, cta_h=84, small_y=1056),
    "story": dict(H=1920, photo_h=1500, logo_y=190, logo_h=190, ban_y=420, ban_h=190, ban_font=130,
                  card_y=870, card_h=450, card_w=880, panel_y=1400, feat_y=1458, cta_y=1560, cta_h=104, small_y=1700),
}


def e(s):
    return html.escape(str(s))


def torn(w, h, fill, uid, scale=14, freq=.035, seed=3):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="position:absolute;left:0;top:0;overflow:visible">'
            f'<defs><filter id="{uid}" x="-8%" y="-12%" width="116%" height="124%"><feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="3" seed="{seed}"/>'
            f'<feDisplacementMap in="SourceGraphic" scale="{scale}"/></filter></defs>'
            f'<rect x="{scale}" y="{scale}" width="{w-2*scale}" height="{h-2*scale}" rx="10" fill="{fill}" filter="url(#{uid})"/></svg>')


def css(fmt):
    L = LAY[fmt]
    return FONTS + f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:{L['H']}px;position:relative;overflow:hidden;font-family:Inter,sans-serif;color:{NAVY};
  background:linear-gradient(180deg,#4fb0ee 0%,#bfe6fb 55%,#f6dca6 100%)}}
.bg{{position:absolute;left:0;top:0;width:1080px;height:{L['photo_h']}px;background-size:cover;background-position:center;
  filter:saturate(1.2) brightness(1.1) contrast(1.05)}}
.warm{{position:absolute;left:0;top:0;width:1080px;height:{L['photo_h']}px;
  background:linear-gradient(180deg,rgba(255,255,255,.28) 0%,rgba(255,255,255,0) 30%,rgba(255,196,120,.14) 100%)}}
.logo{{position:absolute;left:0;right:0;top:{L['logo_y']}px;text-align:center}}
.logo img{{height:{L['logo_h']}px;filter:drop-shadow(0 0 10px #fff) drop-shadow(0 0 26px rgba(255,255,255,.9))}}
.ban{{position:absolute;left:100px;top:{L['ban_y']}px;width:880px;height:{L['ban_h']}px}}
.ban .t{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:.28em;font:900 {L['ban_font']}px/1 Fraunces,serif;font-style:italic;color:#fff;letter-spacing:-.01em;padding-bottom:6px}}
.ban .t b{{color:#F5C542;font-weight:900;position:relative}}
.ban .t b:after{{content:"";position:absolute;left:-2%;right:-2%;bottom:-.06em;height:.07em;background:#F5C542;border-radius:6px;transform:rotate(-1.5deg)}}
.sub{{position:absolute;left:0;right:0;text-align:center}}
.sub span{{display:inline-block;background:#fff;color:{NAVY};font:800 28px Inter;letter-spacing:.14em;text-transform:uppercase;padding:10px 28px;border-radius:40px;box-shadow:0 4px 14px rgba(10,27,46,.25)}}
.card{{position:absolute;left:{(1080-L['card_w'])//2}px;top:{L['card_y']}px;width:{L['card_w']}px;height:{L['card_h']}px}}
.card .in{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:22px 0 40px}}
.eb{{font:800 24px Inter;letter-spacing:.16em;text-transform:uppercase;color:#7a5d18}}
.city{{font:900 {96 if fmt=='story' else 84}px/1.05 Fraunces,serif;color:{NAVY};margin-top:6px;letter-spacing:-.01em}}
.pr{{display:flex;align-items:center;gap:18px;margin-top:4px}}
.pr .f{{font:800 {44 if fmt=='story' else 38}px Inter;color:{NAVY}}}
.pr .n{{font:900 {215 if fmt=='story' else 176}px/.95 Fraunces,serif;color:#F2B722;
  -webkit-text-stroke:{7 if fmt=='story' else 5}px {NAVY};paint-order:stroke fill;text-shadow:0 8px 0 {NAVY}}}
.pr .r{{font:800 {38 if fmt=='story' else 36}px/1.12 Inter;color:{NAVY};white-space:nowrap}}
.date{{z-index:5;position:absolute;left:0;right:0;text-align:center}}
.date span{{display:inline-flex;align-items:center;gap:16px;background:{NAVY};color:#fff;font:800 {50 if fmt=='story' else 44}px Inter;padding:14px 38px;border-radius:60px;box-shadow:0 6px 18px rgba(10,27,46,.45)}}
.date svg{{width:{50 if fmt=='story' else 44}px;height:{50 if fmt=='story' else 44}px}}
.panel{{position:absolute;left:-60px;right:-60px;top:{L['panel_y']}px;bottom:0;background:linear-gradient(180deg,#123a73 0%,{NAVY} 70%);
  border-top-left-radius:50% 70px;border-top-right-radius:50% 70px;box-shadow:0 -10px 30px rgba(10,27,46,.35)}}
.feats{{position:absolute;left:0;right:0;top:{L['feat_y']}px;display:flex;justify-content:center;gap:0}}
.feat{{display:flex;align-items:center;gap:16px;color:#fff;font:800 {32 if fmt=='story' else 28}px Inter;padding:0 {30 if fmt=='story' else 26}px;border-left:2px solid rgba(255,255,255,.28)}}
.feat:first-child{{border-left:0}}
.feat i{{width:{84 if fmt=='story' else 74}px;height:{84 if fmt=='story' else 74}px;border:3px solid #fff;border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none}}
.feat i svg{{width:52%;height:52%}}
.cta{{position:absolute;left:150px;right:150px;top:{L['cta_y']}px;height:{L['cta_h']}px;border-radius:60px;background:linear-gradient(180deg,#FFD84D,#F5B800);
  display:flex;align-items:center;justify-content:center;gap:16px;font:900 {50 if fmt=='story' else 40}px Fraunces,serif;color:{NAVY};box-shadow:0 6px 0 #b98700,0 10px 22px rgba(0,0,0,.35)}}
.small{{position:absolute;left:40px;right:40px;top:{L['small_y']}px;text-align:center;font:400 {22 if fmt=='story' else 19}px Inter;color:#cfe0f3}}
"""


def _bg(photo):
    return f'<div class=bg style="background-image:url(\'{photo}\')"></div><div class=warm></div>' if photo else \
           '<div class=bg style="filter:none"></div>'


def _shell(fmt, photo, inner, note):
    credit = " · Photo: Wikimedia Commons" if photo else ""
    L = LAY[fmt]
    return (f"<!doctype html><meta charset=utf-8><style>{css(fmt)}</style><body>{_bg(photo)}"
            f"<div class=logo><img src=../assets/logo.png></div>{inner}</body>"), credit


def _banner(fmt, origin):
    L = LAY[fmt]
    return (f'<div class=ban>{torn(880, L["ban_h"], NAVY, "b"+fmt, scale=16, freq=.03, seed=7)}'
            f'<div class=t>From <b>{e(origin)}</b></div></div>')


def _panel(fmt, feats, note, credit):
    L = LAY[fmt]
    fs = "".join(f"<div class=feat><i>{ICON[i]}</i>{e(t)}</div>" for i, t in feats)
    return (f'<div class=panel></div><div class=feats>{fs}</div>'
            f'<div class=cta>Visit {SITE} <span>→</span></div><div class=small>{e(note)}{credit}</div>')


def hero(fmt, c, origin, photo, note, dates, how, kind_label):
    L = LAY[fmt]
    eb = f"Return flight · {c['airline']} {how}" if c.get("airline") else f"Return flight · {how}"
    card = (f'<div class=card>{torn(L["card_w"], L["card_h"], "#fff", "c"+fmt, scale=14, freq=.03, seed=11)}'
            f'<div class=in><div class=eb>{e(eb)}</div><div class=city>{e(c["city"])}</div>'
            f'<div class=pr><span class=f>from</span><span class=n>€{c["price"]}</span><span class=r>return<br>per person</span></div></div></div>')
    date = f'<div class=date style="top:{L["card_y"]+L["card_h"]-34}px"><span>{ICON["cal"]}{e(dates)}</span></div>'
    n = note + (" · Photo: Wikimedia Commons" if photo else "")
    html_, _ = _shell(fmt, photo, _banner(fmt, origin) + card + date +
                      _panel(fmt, [("plane", "Flights only"), ("cal", kind_label), ("tag", f"More {origin} deals")], n, ""), n)
    return html_


def cards(fmt, cs, origin, photos, note, sub):
    L = LAY[fmt]
    story = fmt == "story"
    ch = 380 if story else 250
    y0 = 740 if story else 405
    gap = 30 if story else 22
    out = ""
    for i, (c, ph) in enumerate(zip(cs, photos)):
        top = y0 + i * (ch + gap)
        bgs = f"background-image:url('{ph}')," if ph else ""
        bgstyle = (f"background:linear-gradient(180deg,rgba(10,27,46,0) 40%,rgba(10,27,46,.7) 100%),url('{ph}') center/cover;" if ph else
                   "background:linear-gradient(180deg,#59b6f0,#f6dca6);")
        out += (f'<div style="position:absolute;left:60px;right:60px;top:{top}px;height:{ch}px;border-radius:30px;border:6px solid #fff;overflow:hidden;'
                f'box-shadow:0 8px 24px rgba(10,27,46,.4);{bgstyle}filter:saturate(1.15)">'
                f'<div style="position:absolute;left:30px;bottom:24px;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.7)">'
                f'<div style="font:900 {74 if story else 58}px/1 Fraunces,serif">{e(c["city"])}</div>'
                f'<div style="font:700 {36 if story else 28}px Inter;margin-top:8px">{e(c["dates"])}</div></div></div>'
                f'<div style="position:absolute;right:{40}px;top:{top+ch-(250 if story else 168)}px;width:{360 if story else 300}px;height:{220 if story else 150}px">'
                f'{torn(360 if story else 300, 220 if story else 150, "#fff", f"p{fmt}{i}", scale=10, freq=.04, seed=5+i)}'
                f'<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                f'<div style="font:800 {26 if story else 21}px Inter;color:{NAVY}">from</div>'
                f'<div style="font:900 {120 if story else 88}px/.95 Fraunces,serif;color:#F2B722;-webkit-text-stroke:{5 if story else 4}px {NAVY};paint-order:stroke fill">€{c["price"]}</div>'
                f'<div style="font:800 {24 if story else 19}px Inter;color:{NAVY}">return · per person</div></div></div>')
    subpos = (650 if story else 345)
    subhtml = f'<div class=sub style="top:{subpos}px"><span>{e(sub)} · Flights only</span></div>'
    if story:
        panel_y, cta_y = 1560, 1620
    else:
        panel_y, cta_y = 950, 964
    extra = (f".panel{{top:{panel_y}px!important}}.cta{{top:{cta_y}px!important;height:{104 if story else 76}px!important}}"
             f".small{{top:{cta_y+(130 if story else 90)}px!important}}.feats{{display:none}}")
    photo = photos[0]
    n = note + (" · Photos: Wikimedia Commons" if any(photos) else "")
    inner = _banner(fmt, origin) + subhtml + out + _panel(fmt, [], n, "")
    # sky backdrop (no full-bleed photo for the two-card layout)
    h, credit = _shell(fmt, None, inner, note)
    h = h.replace("</style>", extra + ".logo img{filter:drop-shadow(0 0 10px #fff) drop-shadow(0 0 26px #fff)}</style>")
    return h
