#!/usr/bin/env python3
"""
Render data/contributions.json (produced by fetch_contributions.py) as a proper
GitHub-style contribution heatmap SVG: a grid of rounded, colored BOXES in the
classic 53-week x 7-day calendar, revealed once with a diagonal line-after-line
slide-down (CSS keyframes, plays on load then freezes -- no looping "glow"), a
Less->More legend, and a real stats footer.

Run by .github/workflows/update-profile-art.yml after fetch_contributions.py.
"""
import datetime
import json
import os

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "..", "data", "contributions.json")
OUT_PATH = os.path.join(HERE, "..", "contrib-heatmap.svg")

# GitHub-ish green ramp (Light Theme)
PALETTE = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39", "#000000"] # 5 levels (0-4), 5th is fallback

CELL = 12
GAP = 3
STEP = CELL + GAP
PAD = 22
LEFT_LABEL_W = 30
TOP_LABEL_H = 20
TITLEBAR_H = 30

BG = "#ffffff"
BG2 = "#ffffff"
FRAME = "#d0d7de"
MUTED = "#57606a"
TEXT = "#24292f"
ACCENT = "#0969da"
GREEN = "#2da44e"
GOLD = "#bf8700"

# reveal timing (one-shot) - made slower
COL_T = 0.045   # per-column delay contribution (left -> right sweep)
ROW_T = 0.090   # per-row delay contribution (top -> bottom cascade)
CELL_DUR = 0.85


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
    stats_h = 88
    canvas_h = TOP_LABEL_H + art_h + stats_h + PAD

    css = f"""
@keyframes cell {{
  0%   {{ opacity: 0; transform: translateY(-6px); }}
  100% {{ opacity: 1; transform: translateY(0); }}
}}
.c {{ opacity: 0; animation: cell {CELL_DUR:.2f}s cubic-bezier(.2,.8,.2,1) both; }}
""".strip()

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}" '
        f'viewBox="0 0 {canvas_w} {canvas_h}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        f'<style>{css}\n'
        f'@keyframes fadeOutView {{\n'
        f'  0%, 90% {{ opacity: 1; }}\n'
        f'  100% {{ opacity: 0; visibility: hidden; }}\n'
        f'}}\n'
        f'@keyframes fadeInView {{\n'
        f'  0%, 90% {{ opacity: 0; }}\n'
        f'  100% {{ opacity: 1; visibility: visible; }}\n'
        f'}}\n'
        f'#heatmap-view {{ animation: fadeOutView 5.5s forwards; }}\n'
        f'#bomberman-view {{ animation: fadeInView 5.5s forwards; opacity: 0; }}\n'
        f'</style>',
    ]

    grid_top = TOP_LABEL_H + 10
    grid_left = PAD + LEFT_LABEL_W

    parts.append('<g id="heatmap-view">')

    for ci, label in month_labels:
        x = grid_left + ci * STEP
        parts.append(f'<text x="{x}" y="{grid_top - 8}" fill="{MUTED}" font-size="10">{label}</text>')

    for wi, wname in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = grid_top + wi * STEP + CELL * 0.78
        parts.append(f'<text x="{PAD}" y="{y:.1f}" fill="{MUTED}" font-size="9">{wname}</text>')

    # the boxes -- each a rounded rect, diagonal slide-down reveal (once, freeze)
    for ci, column in enumerate(grid):
        gx = grid_left + ci * STEP
        for ri, cell in enumerate(column):
            if cell is None:
                continue
            date_s, count, lvl = cell
            gy = grid_top + ri * STEP
            delay = ci * COL_T + ri * ROW_T
            plural = "s" if count != 1 else ""
            parts.append(
                f'<rect class="c" x="{gx}" y="{gy}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{PALETTE[lvl]}" style="animation-delay:{delay:.3f}s">'
                f'<title>{date_s}: {count} contribution{plural}</title></rect>'
            )

    # legend: Less [][][][][] More (bottom-right of the grid)
    leg_y = grid_top + art_h + 6
    leg_x = canvas_w - PAD - (len(PALETTE) * (CELL - 1) + 70)
    parts.append(f'<text x="{leg_x}" y="{leg_y + CELL*0.8:.1f}" fill="{MUTED}" font-size="10" text-anchor="end">Less</text>')
    lx = leg_x + 8
    for lvl, color in enumerate(PALETTE):
        parts.append(f'<rect x="{lx}" y="{leg_y}" width="{CELL-1}" height="{CELL-1}" rx="2.2" fill="{color}"/>')
        lx += CELL
    parts.append(f'<text x="{lx + 4}" y="{leg_y + CELL*0.8:.1f}" fill="{MUTED}" font-size="10">More</text>')
    
    parts.append('</g>')
    
    import re
    game_name = os.environ.get("CHOSEN_GAME", "bomberman")
    bm_path = os.path.join(HERE, "..", "dist", f"{game_name}-contribution-graph-dark.svg")
    if os.path.exists(bm_path):
        with open(bm_path, "r", encoding="utf-8") as f:
            bm_content = f.read()
            match = re.search(r'<svg[^>]*>(.*)</svg>', bm_content, re.DOTALL | re.IGNORECASE)
            if match:
                inner_bm = match.group(1)
                # Remove the opaque background rect of the action's SVG
                inner_bm = re.sub(r'<rect width="100%" height="100%" fill="[^"]*"/>', '', inner_bm)
                
                scale = STEP / 22.0
                # Align centers: bomberman cells are slightly larger (13.6x13.6 scaled) vs our 12x12
                # Also bomberman has an internal y=15 offset for its first cell.
                x_offset = grid_left - 0.818
                y_offset = grid_top - (15 * scale) - 0.818
                
                parts.append(f'<g id="bomberman-view" transform="translate({x_offset:.3f}, {y_offset:.3f}) scale({scale:.4f})">')
                parts.append(inner_bm)
                parts.append('</g>')

    sep_y = leg_y + CELL + 14
    parts.append(f'<line x1="0" y1="{sep_y}" x2="{canvas_w}" y2="{sep_y}" stroke="{FRAME}" stroke-opacity="0.25"/>')

    cs = data["current_streak"]["length"]
    ls = data["longest_streak"]["length"]
    total = data["total_contributions"]
    best = data["best_day"]
    rng = data["range"]

    ly = sep_y + 24
    # left column: big highlighted numbers; right column: context in muted
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{GREEN}">'
                 f'<tspan font-weight="700">{total:,}</tspan>'
                 f'<tspan fill="{MUTED}"> contributions in the last year</tspan></text>')
    parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'{rng["start"]} &#8594; {rng["end"]}</text>')
    ly += 24
    parts.append(f'<text x="{PAD}" y="{ly}" font-size="13" fill="{MUTED}">current streak '
                 f'<tspan fill="{ACCENT}" font-weight="700">{cs} days</tspan>'
                 f'<tspan fill="{MUTED}">   &#183;   longest </tspan>'
                 f'<tspan fill="{ACCENT}" font-weight="700">{ls} days</tspan></text>')
    parts.append(f'<text x="{canvas_w - PAD}" y="{ly}" font-size="12" fill="{MUTED}" text-anchor="end">'
                 f'best day <tspan fill="{GOLD}" font-weight="700">{best["count"]}</tspan> on {best["date"]}</text>')

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    data = json.load(open(IN_PATH))
    svg = render(data)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({len(svg)} bytes)")
