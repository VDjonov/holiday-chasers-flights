"""Shared bits for all poster designs: slogan sizing, 'Plan the rest' row, icons."""
import html

SITE = "holidaychasers.ie"
BTN = f"Visit {SITE} →"
PLAN = ["Flights", "Stays", "Car hire", "Events"]
ICONS = {
    "Flights": '<path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z" fill="currentColor" stroke="none"/>',
    "Stays": '<path d="M3 18V7M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5"/><circle cx="7" cy="11" r="1.6"/>',
    "Car hire": '<path d="M5 16l1.5-5h11L19 16M4 16h16v3H4zM7 19v1.5M17 19v1.5"/>',
    "Events": '<path d="M3 9a2 2 0 0 0 0 6v3h18v-3a2 2 0 0 0 0-6V6H3z"/><path d="M14 6v12" stroke-dasharray="2 2"/>',
}


def e(s):
    return html.escape(str(s))


def slogan_fs(text, max_px, width=1000):
    return int(max(24, min(max_px, width / (len(text) * 0.52))))


def icon(name, color):
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" style="color:{color}">{ICONS[name]}</svg>')


def plan_row(color, fs, ico, label=True, gap=18, label_color=None):
    """Row of four 'Flights / Stays / Car hire / Events' chips. Returns inner HTML (put it in a flex container)."""
    out = ""
    for n in PLAN:
        out += (f'<div style="display:flex;align-items:center;gap:10px;color:{color};font:800 {fs}px Inter;white-space:nowrap">'
                f'<span style="width:{ico}px;height:{ico}px;border:2.5px solid {color};border-radius:50%;display:flex;align-items:center;justify-content:center;flex:none">'
                f'<span style="width:56%;height:56%;display:block">{icon(n, color)}</span></span>{n}</div>')
    return out
