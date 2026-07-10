#!/usr/bin/env python3
"""
Render data/contributions.json (produced by fetch_contributions.py) as a
terminal-styled ASCII contribution heatmap SVG -- one monospace character
per day, colored by intensity, laid out in the classic 53-week x 7-day
calendar grid, with a SMIL column-wipe reveal animation and a real stats
footer (streaks / total / best day).

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import datetime
import json
import os

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "..", "data", "contributions.json")
OUT_PATH = os.path.join(HERE, "..", "contrib-heatmap.svg")

RAMP = " .:-*#@"
PALETTE = ["#1c2128", "#0e4429", "#146c37", "#26a648", "#39d353", "#7cf2a0"]

CELL = 11
GAP = 2
STEP = CELL + GAP
PAD = 20
LEFT_LABEL_W = 26
TOP_LABEL_H = 18
BG = "#0d1117"
BG2 = "#161b22"
FRAME = "#30363d"
TITLE_TEXT = "#8b949e"
TITLEBAR_H = 30


def level_for(count):
    if count == 0:
        return 0
    if count <= 5:
        return 1
    if count <= 15:
        return 2
    if count <= 30:
        return 3
    if count <= 50:
        return 4
    return 5


def build_grid(days):
    first = datetime.date.fromisoformat(days[0]["date"])
    lead_pad = (first.weekday() + 1) % 7  # sunday=0
    grid = []
    col = [None] * lead_pad
    for d in days:
        date = datetime.date.fromisoformat(d["date"])
        weekday = (date.weekday() + 1) % 7
        while len(col) < weekday:
            col.append(None)
        col.append((d["date"], d["count"], level_for(d["count"])))
        if len(col) == 7:
            grid.append(col)
            col = []
    if col:
        while len(col) < 7:
            col.append(None)
        grid.append(col)
    return grid


def render(data):
    days = data["days"]
    grid = build_grid(days)
    n_cols = len(grid)
    art_w = n_cols * STEP
    art_h = 7 * STEP

    month_labels = []
    seen_months = set()
    for ci, column in enumerate(grid):
        for cell in column:
            if cell is None:
                continue
            date = datetime.date.fromisoformat(cell[0])
            key = (date.year, date.month)
            if key not in seen_months and date.day <= 7:
                seen_months.add(key)
                month_labels.append((ci, date.strftime("%b")))
            break

    canvas_w = PAD + LEFT_LABEL_W + art_w + PAD
    stats_h = 92
    canvas_h = TITLEBAR_H + TOP_LABEL_H + art_h + stats_h + PAD

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        f'<rect width="{canvas_w}" height="{canvas_h}" rx="10" fill="{BG}">'
        f'<animate attributeName="fill" values="{BG};{BG2};{BG}" dur="9s" repeatCount="indefinite"/></rect>',
        f'<rect x="0.5" y="0.5" width="{canvas_w-1}" height="{canvas_h-1}" rx="10" '
        f'fill="none" stroke="{FRAME}" stroke-width="1"/>',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-width="1"/>',
    ]
    for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
    parts.append(f'<text x="{canvas_w/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
                  f'text-anchor="middle">avi@github: ~/contrib-heatmap.sh</text>')

    grid_top = TITLEBAR_H + TOP_LABEL_H
    grid_left = PAD + LEFT_LABEL_W

    for ci, label in month_labels:
        x = grid_left + ci * STEP
        parts.append(f'<text x="{x}" y="{TITLEBAR_H + 13}" fill="{TITLE_TEXT}" font-size="11">{label}</text>')

    for wi, wname in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = grid_top + wi * STEP + CELL * 0.8
        parts.append(f'<text x="{PAD}" y="{y:.1f}" fill="{TITLE_TEXT}" font-size="10">{wname}</text>')

    total_anim = n_cols * 0.045 + 1.2

    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        t0 = (ci / n_cols) * (n_cols * 0.045)
        a = (t0 + 0.35) / (total_anim + 2.5)
        hold_end = (total_anim + 1.8) / (total_anim + 2.5)
        key_times = f"0;{a:.4f};{hold_end:.4f};1"
        g_parts = []
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            date_s, count, lvl = cell
            gy = grid_top + ri * STEP
            ch = RAMP[min(lvl, len(RAMP) - 1)]
            color = PALETTE[lvl]
            g_parts.append(
                f'<text x="{gx}" y="{gy + CELL*0.85:.1f}" font-size="{CELL:.0f}" fill="{color}" '
                f'textLength="{CELL}" lengthAdjust="spacingAndGlyphs">{ch}'
                f'<title>{date_s}: {count} contribution{"s" if count != 1 else ""}</title></text>'
            )
        parts.append(
            f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" keyTimes="{key_times}" '
            f'dur="{total_anim+2.5:.2f}s" repeatCount="indefinite"/>{"".join(g_parts)}</g>'
        )

    sep_y = grid_top + art_h + 14
    parts.append(f'<line x1="0" y1="{sep_y}" x2="{canvas_w}" y2="{sep_y}" stroke="{FRAME}" stroke-width="1"/>')

    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    total = data["total_contributions"]
    best = data["best_day"]
    rng = data["range"]

    rows = [
        (f'{total:,} contributions', f'{rng["start"]} → {rng["end"]}'),
        (f'current streak: {cs} days', f'longest streak: {ls} days'),
        (f'best day: {best["count"]} contributions', f'on {best["date"]}'),
    ]
    ly = sep_y + 22
    for left, right in rows:
        parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="#39d353">{left}</text>')
        parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="13" fill="#8b949e" text-anchor="end">{right}</text>')
        ly += 22

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    data = json.load(open(IN_PATH))
    svg = render(data)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes)")
