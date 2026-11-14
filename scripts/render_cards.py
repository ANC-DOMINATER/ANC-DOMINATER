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

from PIL import Image, ImageOps
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DATA", ROOT / "data" / "contributions.json"))
OUT = Path(os.environ.get("OUT", ROOT / "cards"))
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

# ---- palette (paper, ink and cobalt) ---------------------------------------
BG, PANEL, BORDER = "#F5F5F1", "#F5F5F1", "#E5E5DF"
ACCENT, GREEN = "#3450FF", "#3450FF"
TEXT, MUTED = "#171817", "#777981"
BRAND = os.environ.get("BRAND", ACCENT)
EMPTY = "#E5E6EB"
COL = {"ACCENT": ACCENT, "GREEN": "#F33B2E", "TEXT": "#FFCE18"}

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
    serif_css = ""
    for style in ("Regular", "Italic"):
        sf = TTFont(ROOT / "fonts" / f"InstrumentSerif-{style}.ttf")
        ss = subset.Subsetter(opt)
        ss.populate(text=chars)
        ss.subset(sf)
        sf.flavor = "woff"
        sb = io.BytesIO()
        sf.save(sb)
        enc = base64.b64encode(sb.getvalue()).decode()
        serif_css += "@font-face{font-family:Serif; font-style:" + ("italic" if style == "Italic" else "normal") + ";src:url(data:font/woff;base64," + enc + ") format('woff')}"
    return serif_css + ("@font-face{font-family:'Space Grotesk';font-weight:300 700;"
            f"src:url(data:font/woff;base64,{b64}) format('woff')}}")


# ---- svg scaffolding -----------------------------------------------------------
ANIM_CSS = """
.fu{animation:fu .7s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
.fi{animation:fi .9s ease both;animation-delay:var(--d,0s)}
.gr{transform-box:fill-box;transform-origin:50% 100%;animation:gr 8s ease-in-out infinite both;animation-delay:var(--d,0s)}
.gx{transform-box:fill-box;transform-origin:0 50%;animation:gx .8s cubic-bezier(.2,.7,.2,1) both;animation-delay:var(--d,0s)}
.pop{transform-box:fill-box;transform-origin:50% 50%;animation:pop 7s ease-in-out infinite both;animation-delay:var(--d,0s)}
@keyframes fu{from{opacity:0;transform:translateY(10px)}}
@keyframes fi{from{opacity:0}}
@keyframes gr{0%{transform:scaleY(.1)}12%,85%{transform:scaleY(1)}100%{transform:scaleY(.1)}}
@keyframes gx{from{transform:scaleX(0)}}
@keyframes pop{0%,100%{opacity:.35;transform:scale(.8)}15%,85%{opacity:1;transform:scale(1)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.deco{display:none}.name-shine{fill:#171817!important}}
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
    inline = re.search(r' style="([^"]*)"', extra)
    if inline and st:
        st = st[:-1] + ";" + inline.group(1) + '"'
        extra = extra[:inline.start()] + extra[inline.end():]
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
    # A square raster sampled into glyphs with square physical pixel spacing.
    rows = ""
    if PORTRAIT:
        image = Image.open(PORTRAIT).convert("L").resize((90, 45), Image.Resampling.LANCZOS)
        image = ImageOps.autocontrast(image)
        ramp = " .:-=+*#%@"
        for y in range(image.height):
            line = "".join(ramp[min(9, (255-image.getpixel((x,y)))*10//256)] for x in range(image.width))
            rows += T(542, 64+y*4.8, line, 4, "#676963", cls="fi", d=.2+y*.025,
                      extra=' xml:space="preserve" textLength="216" lengthAdjust="spacingAndGlyphs" style="font-family:monospace"')
    pulse = deco(f'<circle cx="43" cy="48" r="5" fill="{ACCENT}"><animate attributeName="opacity" values="1;.15;1" dur="2s" repeatCount="indefinite"/></circle>')
    # Move a narrow cobalt highlight through the name, rather than drawing an underline.
    defs = ""
    name_fill = TEXT
    if not STATIC:
        name_fill = "url(#name-shine)"
        defs = f'''<linearGradient id="name-shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="420" y2="0">
          <stop offset="0" stop-color="{TEXT}"/><stop offset=".38" stop-color="{TEXT}"/>
          <stop offset=".5" stop-color="{ACCENT}"/><stop offset=".62" stop-color="{TEXT}"/>
          <stop offset="1" stop-color="{TEXT}"/>
          <animateTransform attributeName="gradientTransform" type="translate"
            values="-420 0;420 0;420 0" keyTimes="0;.5;1" dur="7s" begin="1.2s" repeatCount="indefinite"/>
        </linearGradient>'''
    body = (f'<rect x="40" y="45" width="6" height="6" rx="1" fill="{ACCENT}"/>' + pulse
        + T(56, 51, EYEBROW, 10, MUTED, extra=' letter-spacing="1.4"')
        + T(38, 154, NAME, 72, name_fill, cls="fu name-shine", d=.15, extra=' style="font-family:Serif;font-style:italic"')
        + T(42, 224, "I build AI-driven apps, LLM pipelines", 16, "#494B4A", cls="fu", d=.4)
        + T(42, 248, "and automation with Python and Next.js.", 16, "#494B4A", cls="fu", d=.5)
        + T(42, 302, "BANGALORE, INDIA     /     ANC-DOMINATER", 10, MUTED, cls="fi", d=.65,
            extra=' letter-spacing="1"') + rows)
    card("hero", 338, NAME + " | AI engineer and full-stack developer", TAGLINE, body, defs=defs)


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
        fill = ACCENT if i == pk else TEXT
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
        ("BUSIEST DAY", fmt(st["busiest"]["count"]), st["busiest"]["date"].strftime("%b %d, %Y"), TEXT),
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
    body = (T(32, 50, "A year of building", 34, TEXT, 400, cls="fu", d=t0, extra=' style="font-family:Serif"')
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
    body = (T(32, 50, "Every day, in blue", 34, TEXT, 400, cls="fu", d=t0, extra=' style="font-family:Serif;font-style:italic"')
            + T(W - 32, 50, f"{fmt(st['total'])} contributions in the last year", 13, MUTED, 400, "end", cls="fu", d=t0 + .1)
            + months + wd + cells + ring + legend)
    card("graph", 248, "Contribution graph",
         f"{fmt(st['total'])} contributions in the last year, one square per day.", body,
         extra_text="Contribution graph contributions in the last year Less More Mon Wed Fri" + "".join(calendar.month_abbr) + "0123456789,")


def main():
    data = load()
    days, st = data["days"], stats(data["days"])
    # No project panels: the profile stays focused on the person and activity.
    for old in OUT.glob("repo-*.svg"):
        old.unlink()
    hero(0)
    graph(.5, days, st)
    activity(1.1, days, st)
    for old in OUT.glob("tile-*.svg"):
        old.unlink()
    mode = "STATIC (final frame)" if STATIC else "animated"
    sizes = {p.name: p.stat().st_size for p in sorted(OUT.glob("*.svg"))}
    print(f"rendered {len(sizes)} cards [{mode}] -> {OUT}")
    for n, s in sizes.items():
        print(f"  {n:22s}{s / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
