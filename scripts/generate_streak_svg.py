#!/usr/bin/env python3
"""Generate an animated GitHub-streak SVG with a terminal UI (Mac-style)."""
import sys, json, os, datetime, urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "mahesh2-lab"
OUT  = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"

def get_data(user):
    url = f"https://github-contributions-api.jogruber.de/v4/{user}?y=last"
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contrib.json")
        if os.path.exists(here):
            print("API failed (%s); using local contrib.json" % e)
            return json.load(open(here))
        raise

data = get_data(USER)
contribs = data["contributions"]
total = data["total"]["lastYear"]

current_streak = 0
longest_streak = 0
temp_streak = 0
best_day_count = 0
best_day_date = ""

for c in contribs:
    count = c.get("count", 0)
    if count > 0:
        temp_streak += 1
        longest_streak = max(longest_streak, temp_streak)
    else:
        temp_streak = 0
        
    if count > best_day_count:
        best_day_count = count
        best_day_date = c.get("date", "")

current_streak = 0
c_reversed = list(reversed(contribs))
if len(c_reversed) > 0 and c_reversed[0].get("count", 0) == 0:
    c_reversed = c_reversed[1:]

for c in c_reversed:
    if c.get("count", 0) > 0:
        current_streak += 1
    else:
        break

start_date = contribs[0]["date"]
end_date = contribs[-1]["date"]

# ---- layout ----
CELL, GAP, RAD = 13, 3, 2.5
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
GRAY = "#7d8590"
CYAN = "#22d3ee"
GREEN = "#3fb950"
YELLOW = "#ffbd2e"
BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

n = len(contribs)
NW = (n + 6) // 7

PAD = 20
TITLEBAR_H = 30
# Calculate the required width
W = max(860, PAD + 30 + NW*(CELL+GAP) + PAD)
TOP = TITLEBAR_H + PAD + 15
LEFT = (W - (NW*(CELL+GAP))) // 2 + 10
H = TOP + 7*(CELL+GAP) + 15 + 80

REVEAL, DUR = 3.6, 0.55
maxorder = (NW-1) + 6*0.55

rects, labels = [], []
sd = datetime.date.fromisoformat(start_date)
last_m = None
for wk in range(NW):
    d = sd + datetime.timedelta(days=wk*7)
    if d.month != last_m:
        last_m = d.month
        labels.append(f'<text class="lbl" x="{LEFT+wk*(CELL+GAP)}" y="{TOP-8}">{MONTHS[d.month-1]}</text>')
for name, r in [("Mon",1),("Wed",3),("Fri",5)]:
    labels.append(f'<text class="lbl" x="{LEFT-30}" y="{TOP+r*(CELL+GAP)+CELL-2}">{name}</text>')

for i, c in enumerate(contribs):
    wk, row, lvl = i//7, i%7, c["level"]
    x = LEFT + wk*(CELL+GAP); y = TOP + row*(CELL+GAP)
    delay = round((wk + row*0.55)/maxorder * REVEAL, 3)
    cls = "c g" if lvl >= 1 else "c e"
    rects.append(
        f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RAD}" '
        f'fill="{COLORS[lvl]}" style="animation-delay:{delay}s"/>'
    )

# Less / More legend
LEGEND_X = LEFT + NW*(CELL+GAP) - 5*(CELL+GAP) - 40
LEGEND_Y = TOP + 7*(CELL+GAP) + 10
labels.append(f'<text class="lbl" x="{LEGEND_X-35}" y="{LEGEND_Y+10}">Less</text>')
for i, col in enumerate(COLORS):
    labels.append(f'<rect x="{LEGEND_X + i*(CELL+GAP)}" y="{LEGEND_Y}" width="{CELL}" height="{CELL}" rx="{RAD}" fill="{col}"/>')
labels.append(f'<text class="lbl" x="{LEGEND_X + 5*(CELL+GAP) + 5}" y="{LEGEND_Y+10}">More</text>')

# Footer
LINE_Y = TOP + 7*(CELL+GAP) + 35
labels.append(f'<line x1="0" y1="{LINE_Y}" x2="{W}" y2="{LINE_Y}" stroke="{FRAME}" stroke-width="1"/>')

footer_y1 = LINE_Y + 30
footer_y2 = footer_y1 + 25

# Left footer
labels.append(f'<text class="stat-text" x="{PAD}" y="{footer_y1}"><tspan fill="{GREEN}" font-weight="700">{total:,}</tspan> contributions in the last year</text>')
labels.append(f'<text class="stat-text" x="{PAD}" y="{footer_y2}">current streak <tspan fill="{CYAN}" font-weight="700">{current_streak} days</tspan> · longest <tspan fill="{CYAN}" font-weight="700">{longest_streak} days</tspan></text>')

# Right footer
labels.append(f'<text class="stat-text" x="{W-PAD}" y="{footer_y1}" text-anchor="end">{start_date} → {end_date}</text>')
labels.append(f'<text class="stat-text" x="{W-PAD}" y="{footer_y2}" text-anchor="end">best day <tspan fill="{YELLOW}" font-weight="700">{best_day_count}</tspan> on {best_day_date}</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">
<style>
  text.lbl {{ fill:{GRAY}; font-size:12px; font-weight:600; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif; }}
  text.stat-text {{ fill:#8b949e; font-size:13px; font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop {DUR}s ease-out both; }}
  .g {{ animation:pop {DUR}s ease-out both, flash {DUR+0.15}s ease-out both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} 60%{{opacity:1;transform:scale(1.1)}} 100%{{opacity:1;transform:scale(1)}} }}
  @keyframes flash {{ 0%{{filter:brightness(2.4)}} 45%{{filter:brightness(2.4)}} 100%{{filter:brightness(1)}} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ opacity:1 !important; animation:none !important; }} }}
</style>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>
<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>
<line x1="0" y1="{TITLEBAR_H}" x2="{W}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-width="1"/>
<circle cx="{PAD}" cy="{TITLEBAR_H/2}" r="5" fill="#ff5f56"/>
<circle cx="{PAD+16}" cy="{TITLEBAR_H/2}" r="5" fill="#ffbd2e"/>
<circle cx="{PAD+32}" cy="{TITLEBAR_H/2}" r="5" fill="#27c93f"/>
<text x="{W/2}" y="{TITLEBAR_H/2 + 4}" fill="{GRAY}" font-size="12" text-anchor="middle">mahesh@github: ~/contributions --graph</text>
{''.join(labels)}
{''.join(rects)}
</svg>'''

open(OUT, "w", encoding="utf-8").write(svg)
print(f"Wrote {OUT}: {n} days, {total:,} contributions, {len(svg)//1024} KB")
