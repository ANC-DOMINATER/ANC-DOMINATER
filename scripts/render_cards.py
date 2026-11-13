#!/usr/bin/env python3
"""Render the profile README cards (animated SVG) into cards/.

Cards are shown through <img>, so everything is self-contained: an inline <style>
block (CSS keyframes), SMIL <animate> on decorative elements only, and Space Grotesk
subset with fontTools and embedded as a base64 WOFF data URI.

Env:
  STATIC=1   no animation at all: every card shows its final frame (for screenshots)
  DATA=path  contributions JSON (default data/contributions.json)
  OUT=dir    output dir (default cards/)
  BRAND=#hex colour used for the contribution graph (default site accent)
"""
import base64
import calendar
import datetime as dt
import io
import json
import os
import re
import string
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA", ROOT / "data" / "contributions.json"))
OUT = Path(os.environ.get("OUT", ROOT / "cards"))
README = Path(os.environ.get("README", ROOT / "README.md"))
STATIC = os.environ.get("STATIC") == "1"
FONT = ROOT / "fonts" / "SpaceGrotesk[wght].ttf"

# ---- profile ---------------------------------------------------------------
NAME = "G Shashank"
EYEBROW = "AI ENGINEER  ·  FULL-STACK DEVELOPER"
TAGLINE = "I build AI-driven apps, LLM pipelines and automation with Python and Next.js."
LOCATION = "Bangalore, Karnataka"
MONOGRAM = "GS."
PORTRAIT = next((p for p in (ROOT / "assets").glob("portrait.*")
                 if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")), None) \
    if (ROOT / "assets").exists() else None
TILES = [  # file, title, subtitle, url, colour
    ("tile-portfolio", "Portfolio", "Projects and case studies",
     "https://portfolio-8gllllu08-ancdominater-gmailcoms-projects.vercel.app", "ACCENT"),
    ("tile-linkedin", "LinkedIn", "in/g-shashank",
     "https://www.linkedin.com/in/g-shashank", "GREEN"),
    ("tile-github", "GitHub", "All repositories",
     "https://github.com/ANC-DOMINATER?tab=repositories", "TEXT"),
]
MAX_REPOS = int(os.environ.get("MAX_REPOS", "6"))

# ---- palette (from the portfolio site) ---------------------------------------
BG, PANEL, BORDER = "#0A0A0A", "#110F22", "#434887"
ACCENT, GREEN = "#7C86FF", "#00D492"
TEXT, MUTED = "#EEF2FF", "#A1A1A1"
BRAND = os.environ.get("BRAND", ACCENT)
EMPTY = "#1C1A33"
COL = {"ACCENT": ACCENT, "GREEN": GREEN, "TEXT": TEXT}

W = 800  # card width; README scales with width="100%"


# ---- fonts -------------------------------------------------------------------
_M = {}


def _metrics(weight):
    if weight not in _M:
        inst = instancer.instantiateVariableFont(TTFont(FONT), {"wght": weight})
        _M[weight] = (inst.getBestCmap(), inst["hmtx"], inst["head"].unitsPerEm)
    return _M[weight]


def tw(s, size, weight=400):
    """Approximate rendered width (no kerning, +4% safety)."""
    cmap, hmtx, upem = _metrics(weight)
    total = sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in s)
    return total * size / upem * 1.04


def wrap(text, size, maxw, weight=400, lines=2):
    words, out, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if tw(t, size, weight) <= maxw:
            cur = t
            continue
        out.append(cur)
        cur = w
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        last = out[-1]
        while last and tw(last + "…", size, weight) > maxw:
            last = last[:-1]
        out[-1] = last.rstrip() + "…"
    return out


def font_face(text):
    chars = "".join(sorted(set(string.printable[:95]) | set(text) | set("·…—–↗→•")))
    f = TTFont(FONT)
    opt = subset.Options()
    opt.layout_features = ["kern", "liga", "calt"]
    opt.notdef_outline = True
    opt.name_IDs = [1, 2]
    opt.flavor = "woff"
    sub = subset.Subsetter(opt)
    sub.populate(text=chars)
    sub.subset(f)
    f.flavor = "woff"
    buf = io.BytesIO()
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return ("@font-face{font-family:'Space Grotesk';font-weight:300 700;"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}")


# ---- svg scaffolding -----------------------------------------------------------
ANIM_CSS = """
.fu{animation:fu .7s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
.fi{animation:fi .9s ease both;animation-delay:var(--d,0s)}
.gr{transform-box:fill-box;transform-origin:50% 100%;animation:gr .8s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
.gx{transform-box:fill-box;transform-origin:0 50%;animation:gx .8s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
.pop{transform-box:fill-box;transform-origin:50% 50%;animation:pop .35s ease-out both;animation-delay:var(--d,0s)}
@keyframes fu{from{opacity:0;transform:translateY(10px)}}
@keyframes fi{from{opacity:0}}
@keyframes gr{from{transform:scaleY(0)}}
@keyframes gx{from{transform:scaleX(0)}}
@keyframes pop{from{opacity:0;transform:scale(.2)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.deco{display:none}}
"""


def dly(t):
    return "" if STATIC else f' style="--d:{t:.2f}s"'


def deco(markup):
    """Decorative SMIL element: dropped in STATIC, hidden under reduced motion."""
    return "" if STATIC else f'<g class="deco">{markup}</g>'


def card(name, h, title, desc, body, extra_text="", defs=""):
    css = font_face(extra_text or body) + "text{font-family:'Space Grotesk',ui-sans-serif,system-ui,sans-serif}"
    if not STATIC:
        css += ANIM_CSS
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
           f'role="img" aria-labelledby="t d"><title id="t">{escape(title)}</title>'
           f'<desc id="d">{escape(desc)}</desc><style>{css}</style>'
           f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0" stop-color="{PANEL}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
           f'<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0" stop-color="{ACCENT}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>'
           f'{defs}</defs>'
           f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="14" fill="url(#bg)" '
           f'stroke="{BORDER}" stroke-opacity=".55"/>{body}</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    return len(svg)


def T(x, y, s, size, fill, weight=400, anchor="start", cls="", d=None, extra=""):
    c = f' class="{cls}"' if cls and not STATIC else ""
    st = dly(d) if (cls and d is not None) else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{extra}{c}{st}>{escape(s)}</text>')


# ---- data ----------------------------------------------------------------------
def load():
    if not DATA.exists():
        raise SystemExit(f"{DATA} not found: run scripts/fetch_data.py (or the Action) first")
    j = json.loads(DATA.read_text())
    j["days"] = sorted(({"date": dt.date.fromisoformat(d["date"]), "count": int(d["count"])}
                        for d in j["days"]), key=lambda d: d["date"])
    return j


def stats(days):
    cnt = {d["date"]: d["count"] for d in days}
    last = days[-1]["date"]
    run, longest = 0, 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    cur, day = 0, last if cnt.get(last, 0) > 0 else last - dt.timedelta(days=1)
    while cnt.get(day, 0) > 0:
        cur += 1
        day -= dt.timedelta(days=1)
    year = [d for d in days if d["date"] > last - dt.timedelta(days=365)]
    active = sum(1 for d in year if d["count"] > 0)
    busiest = max(year, key=lambda d: d["count"])
    return dict(cur=cur, longest=longest, active=active, span=len(year),
                busiest=busiest, total=sum(d["count"] for d in year), last=last)


def fmt(n):
    return f"{n:,}"


# ---- cards ---------------------------------------------------------------------
def hero(t0):
    cx, cy = 668, 130
    inner = ""
    if PORTRAIT:
        mime = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}[PORTRAIT.suffix[1:].lower()]
        b64 = base64.b64encode(PORTRAIT.read_bytes()).decode()
        inner = (f'<clipPath id="pc"><circle cx="{cx}" cy="{cy}" r="74"/></clipPath>'
                 f'<image href="data:image/{mime};base64,{b64}" x="{cx - 74}" y="{cy - 74}" width="148" '
                 f'height="148" preserveAspectRatio="xMidYMid slice" clip-path="url(#pc)"/>')
    else:
        inner = (f'<circle cx="{cx}" cy="{cy}" r="74" fill="{PANEL}"/>'
                 + T(cx, cy + 22, MONOGRAM, 64, ACCENT, 700, "middle"))
    lines = wrap(TAGLINE, 18, 500)
    blob = deco(
        f'<circle cx="610" cy="40" r="150" fill="{ACCENT}" opacity=".10">'
        '<animate attributeName="cx" values="610;650;610" dur="14s" repeatCount="indefinite"/></circle>'
        f'<circle cx="120" cy="250" r="120" fill="{GREEN}" opacity=".06">'
        '<animate attributeName="cy" values="250;215;250" dur="11s" repeatCount="indefinite"/></circle>')
    ring = deco(
        f'<circle cx="{cx}" cy="{cy}" r="92" fill="none" stroke="{ACCENT}" stroke-opacity=".55" '
        'stroke-width="1.5" stroke-dasharray="3 9" stroke-linecap="round">'
        f'<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
        f'to="360 {cx} {cy}" dur="40s" repeatCount="indefinite"/></circle>')
    dot = deco(f'<circle cx="52" cy="226" r="4" fill="none" stroke="{GREEN}">'
               '<animate attributeName="r" values="4;11" dur="2.4s" repeatCount="indefinite"/>'
               '<animate attributeName="opacity" values=".8;0" dur="2.4s" repeatCount="indefinite"/></circle>')
    body = (blob + ring
            + f'<g{dly(t0 + .3)}{"" if STATIC else " class=" + chr(34) + "fi" + chr(34)}>'
            f'<circle cx="{cx}" cy="{cy}" r="78" fill="none" stroke="url(#ring)" stroke-width="3"/>{inner}</g>'
            + T(48, 62, EYEBROW, 13, GREEN, 500, cls="fu", d=t0 + .1, extra=' letter-spacing="2"')
            + T(46, 134, NAME, 58, TEXT, 700, cls="fu", d=t0 + .25)
            + "".join(T(48, 172 + i * 27, ln, 18, MUTED, 400, cls="fu", d=t0 + .45 + i * .1)
                      for i, ln in enumerate(lines))
            + dot + f'<circle cx="52" cy="226" r="4" fill="{GREEN}"/>'
            + T(66, 231, LOCATION, 14, MUTED, cls="fu", d=t0 + .7))
    card("hero", 260, f"{NAME}: {EYEBROW.replace('  ', ' ')}", TAGLINE, body,
         extra_text=NAME + EYEBROW + TAGLINE + LOCATION + MONOGRAM)


def tile(t0, i, spec):
    name, title, sub, _, ck = spec
    c = COL[ck]
    d0 = t0 + i * .15
    body = (f'<rect x="24" y="24" width="30" height="4" rx="2" fill="{c}"{dly(d0 + .05)}'
            f'{"" if STATIC else " class=" + chr(34) + "gx" + chr(34)}/>'
            + T(24, 70, title, 26, TEXT, 700, cls="fu", d=d0 + .1)
            + T(24, 94, sub, 14, MUTED, cls="fu", d=d0 + .2)
            + T(236, 52, "↗", 26, c, 500, "end", cls="fu", d=d0 + .3))
    # tile uses its own 260x116 canvas
    css = font_face(title + sub) + "text{font-family:'Space Grotesk',ui-sans-serif,system-ui,sans-serif}"
    if not STATIC:
        css += ANIM_CSS
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="260" height="116" viewBox="0 0 260 116" '
           f'role="img" aria-labelledby="t"><title id="t">{escape(title)}: {escape(sub)}</title>'
           f'<style>{css}</style><defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0" stop-color="{PANEL}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>'
           f'<rect x=".5" y=".5" width="259" height="115" rx="14" fill="url(#bg)" stroke="{BORDER}" '
           f'stroke-opacity=".55"/>{body}</svg>')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")


def activity(t0, days, st):
    x0, x1, base, top = 32, 536, 262, 108
    last = st["last"]
    months = []
    y, m = last.year, last.month
    for _ in range(12):
        months.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    months.reverse()
    sums = {k: 0 for k in months}
    for d in days:
        k = (d["date"].year, d["date"].month)
        if k in sums:
            sums[k] += d["count"]
    vals = [sums[k] for k in months]
    vmax = max(vals) or 1
    slot = (x1 - x0) / 12
    bw = 26
    grid = "".join(f'<line x1="{x0}" x2="{x1}" y1="{base - (base - top) * f:.1f}" '
                   f'y2="{base - (base - top) * f:.1f}" stroke="{BORDER}" stroke-opacity="{.5 if f == 0 else .18}"/>'
                   for f in (0, .5, 1))
    bars, labels = "", ""
    pk = vals.index(max(vals))
    for i, (k, v) in enumerate(zip(months, vals)):
        h = max(2, (base - top) * v / vmax)
        bx = x0 + slot * i + (slot - bw) / 2
        d0 = t0 + .35 + i * .06
        fill = GREEN if i == pk else ACCENT
        bars += (f'<rect x="{bx:.1f}" y="{base - h:.1f}" width="{bw}" height="{h:.1f}" rx="5" '
                 f'fill="{fill}" fill-opacity="{1 if i == pk else .8}"{dly(d0)}'
                 f'{"" if STATIC else " class=" + chr(34) + "gr" + chr(34)}/>')
        labels += (T(bx + bw / 2, base - h - 8, fmt(v), 11, TEXT if i == pk else MUTED,
                     700 if i == pk else 400, "middle", cls="fi", d=d0 + .5)
                   + T(bx + bw / 2, base + 22, calendar.month_abbr[k[1]], 11, MUTED, 400, "middle"))
    sx = 584
    blocks = [
        ("STREAK", f"{st['cur']} days", f"longest {st['longest']} days", GREEN),
        ("ACTIVE DAYS", fmt(st["active"]), f"of the last {st['span']} · {round(100 * st['active'] / st['span'])}%", ACCENT),
        ("BUSIEST DAY", fmt(st["busiest"]["count"]), st["busiest"]["date"].strftime("%b %-d, %Y"), TEXT),
    ]
    side = ""
    for i, (lab, val, sub, c) in enumerate(blocks):
        y0 = 112 + i * 68
        d0 = t0 + .5 + i * .18
        side += (T(sx, y0, lab, 11, MUTED, 500, cls="fu", d=d0, extra=' letter-spacing="1.5"')
                 + T(sx, y0 + 30, val, 30, c, 700, cls="fu", d=d0 + .08)
                 + T(sx, y0 + 49, sub, 12, MUTED, cls="fu", d=d0 + .16))
    pulse = deco(f'<circle cx="{sx - 14}" cy="106" r="3" fill="{GREEN}" opacity="0"><animate attributeName="opacity" '
                 f'values="1;.25;1" dur="2.4s" begin="{t0 + .8:.2f}s" repeatCount="indefinite"/></circle>') if st["cur"] else ""
    body = (T(32, 50, "Contributions per month", 22, TEXT, 700, cls="fu", d=t0)
            + T(32, 74, f"{fmt(st['total'])} in the last 12 months", 13, MUTED, cls="fu", d=t0 + .1)
            + grid + bars + labels
            + f'<line x1="560" x2="560" y1="96" y2="290" stroke="{BORDER}" stroke-opacity=".35"/>'
            + side + pulse)
    txt = "Contributions per month in the last 12 months STREAK ACTIVE DAYS BUSIEST DAY days longest of the last " \
          + "".join(b[1] + b[2] for b in blocks) + "".join(calendar.month_abbr)
    card("activity", 316, "Contributions per month",
         f"{fmt(st['total'])} contributions in 12 months; current streak {st['cur']} days; "
         f"{st['active']} active days; busiest day {st['busiest']['date']} with {st['busiest']['count']}.",
         body, extra_text=txt)


def repo_card(t0, i, r):
    name = r["name"]
    desc = wrap(r.get("description") or "", 14, 690, lines=2) if r.get("description") else []
    lang, lc = r.get("language"), r.get("language_color") or MUTED
    body = (f'<rect x="0" y="22" width="4" height="40" rx="2" fill="{ACCENT}"{dly(t0)}'
            f'{"" if STATIC else " class=" + chr(34) + "gx" + chr(34)}/>'
            + T(32, 48, name, 22, TEXT, 700, cls="fu", d=t0 + .05)
            + T(W - 32, 48, "↗", 22, ACCENT, 500, "end", cls="fu", d=t0 + .15)
            + "".join(T(32, 76 + k * 20, ln, 14, MUTED, cls="fu", d=t0 + .15 + k * .08) for k, ln in enumerate(desc)))
    y, x = (118 if desc else 84), 32
    meta = ""
    if lang:
        meta += (f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{lc}"/>'
                 + T(x + 18, y, lang, 13, MUTED))
        x += 18 + tw(lang, 13) + 24
    star = "M0,-6 L1.8,-1.9 6.4,-1.7 2.8,1.2 4,5.7 0,3.2 -4,5.7 -2.8,1.2 -6.4,-1.7 -1.8,-1.9Z"
    meta += (f'<path d="{star}" transform="translate({x + 6} {y - 5})" fill="none" stroke="{MUTED}" stroke-width="1.3" stroke-linejoin="round"/>'
             + T(x + 18, y, fmt(r.get("stars", 0)), 13, MUTED))
    x += 18 + tw(fmt(r.get("stars", 0)), 13) + 24
    fork = (f'<g transform="translate({x + 4} {y - 11})" fill="none" stroke="{MUTED}" stroke-width="1.3">'
            '<circle cx="0" cy="0" r="2.2"/><circle cx="8" cy="0" r="2.2"/><circle cx="4" cy="12" r="2.2"/>'
            '<path d="M0,2.2 V5 Q0,7 4,7 Q8,7 8,5 V2.2 M4,7 V9.8"/></g>')
    meta += fork + T(x + 22, y, fmt(r.get("forks", 0)), 13, MUTED)
    body += f'<g{dly(t0 + .3)}{"" if STATIC else " class=" + chr(34) + "fi" + chr(34)}>{meta}</g>'
    card(f"repo-{i + 1}", 142 if desc else 108, f"{name}: featured repository",
         r.get("description") or name, body,
         extra_text=name + (r.get("description") or "") + (lang or "") + "0123456789,")


def graph(t0, days, st):
    cell, gap = 10, 3
    step = cell + gap
    last = st["last"]
    start = last - dt.timedelta(days=(last.weekday() + 1) % 7 + 52 * 7)
    cnt = {d["date"]: d["count"] for d in days}
    nz = sorted(c for c in cnt.values() if c > 0)
    q = [nz[int(len(nz) * p)] for p in (.25, .5, .75)] if nz else [1, 2, 3]

    def level(c):
        return 0 if c == 0 else 1 + sum(c > t for t in q)

    def mix(a, b, f):
        pa, pb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{round(x + (y - x) * f):02x}" for x, y in zip(pa, pb))

    shades = [EMPTY] + [mix(EMPTY, BRAND, f) for f in (.35, .6, .82, 1)]
    gx0, gy0 = 76, 92
    cells, months = "", ""
    seen = None
    peak = None
    for col in range(53):
        for row in range(7):
            day = start + dt.timedelta(days=col * 7 + row)
            if day > last:
                break
            c = cnt.get(day, 0)
            x, y = gx0 + col * step, gy0 + row * step
            cells += (f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{shades[level(c)]}"'
                      f'{dly(t0 + .3 + col * .018 + row * .008)}{"" if STATIC else " class=" + chr(34) + "pop" + chr(34)}/>')
            if day == st["busiest"]["date"]:
                peak = (x, y)
        mday = start + dt.timedelta(days=col * 7)
        if mday.month != seen and col < 51:
            months += T(gx0 + col * step, 80, calendar.month_abbr[mday.month], 11, MUTED)
            seen = mday.month
    wd = "".join(T(32, gy0 + r * step + 9, n, 11, MUTED) for r, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    ring = ""
    if peak:
        ring = deco(f'<rect x="{peak[0] - 2}" y="{peak[1] - 2}" width="{cell + 4}" height="{cell + 4}" rx="4" '
                    f'fill="none" stroke="{TEXT}" stroke-width="1.5" opacity="0"><animate attributeName="opacity" '
                    f'values="1;.2;1" dur="2.6s" begin="{t0 + 1.6:.2f}s" repeatCount="indefinite"/></rect>')
    lx = W - 32 - 5 * (cell + 4) - 70
    legend = (T(lx, 226, "Less", 11, MUTED, anchor="end")
              + "".join(f'<rect x="{lx + 8 + i * (cell + 4)}" y="{226 - cell}" width="{cell}" height="{cell}" rx="2.5" fill="{s}"/>'
                        for i, s in enumerate(shades))
              + T(lx + 8 + 5 * (cell + 4) + 4, 226, "More", 11, MUTED))
    body = (T(32, 50, "Contribution graph", 22, TEXT, 700, cls="fu", d=t0)
            + T(W - 32, 50, f"{fmt(st['total'])} contributions in the last year", 13, MUTED, 400, "end", cls="fu", d=t0 + .1)
            + months + wd + cells + ring + legend)
    card("graph", 248, "Contribution graph",
         f"{fmt(st['total'])} contributions in the last year, one square per day.", body,
         extra_text="Contribution graph contributions in the last year Less More Mon Wed Fri" + "".join(calendar.month_abbr) + "0123456789,")


# ---- readme ----------------------------------------------------------------------
def update_readme(repos, login):
    if not README.exists():
        return
    block = "\n".join(
        f'<a href="{r["url"]}"><img src="cards/repo-{i + 1}.svg" width="100%" alt="{escape(r["name"])}: '
        f'{escape(r.get("description") or "repository")}"/></a>' for i, r in enumerate(repos))
    txt = README.read_text(encoding="utf-8")
    new = re.sub(r"(<!-- repos:start -->).*?(<!-- repos:end -->)",
                 lambda m: f"{m.group(1)}\n{block}\n{m.group(2)}", txt, flags=re.S)
    if new != txt:
        README.write_text(new, encoding="utf-8")


def main():
    data = load()
    days, st = data["days"], stats(data["days"])
    repos = data.get("repos", [])[:MAX_REPOS]
    for old in OUT.glob("repo-*.svg"):
        old.unlink()
    t = 0.0
    hero(t)
    t += .6
    for i, spec in enumerate(TILES):
        tile(t, i, spec)
    t += .8
    activity(t, days, st)
    t += 1.4
    for i, r in enumerate(repos):
        repo_card(t + i * .3, i, r)
    t += .3 * len(repos) + .3
    graph(t, days, st)
    update_readme(repos, data.get("login", "ANC-DOMINATER"))
    mode = "STATIC (final frame)" if STATIC else "animated"
    sizes = {p.name: p.stat().st_size for p in sorted(OUT.glob("*.svg"))}
    print(f"rendered {len(sizes)} cards [{mode}] -> {OUT}")
    for n, s in sizes.items():
        print(f"  {n:22s}{s / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
