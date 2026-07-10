"""
Convert a portrait photo into a colorful, animated ASCII-art SVG suitable
for embedding in a GitHub profile README (SMIL animations survive GitHub's
image rendering since they're native SVG, not JS).
"""
from PIL import Image, ImageEnhance
import colorsys
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "avi-ascii.svg")

COLS = 90
ROWS = 45
CELL_W = 8
CELL_H = 16
RAMP = " .:-=+*#%@"  # low density -> high density

PAD = 18
TITLEBAR_H = 30
STATUS_H = 26
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0d1117"
BG2 = "#161b22"
FRAME = "#30363d"
TITLE_TEXT = "#8b949e"

# ---- 1. sample the image into a COLS x ROWS grid --------------------------
im = Image.open(SRC).convert("RGB")
im = ImageEnhance.Color(im).enhance(1.35)     # punch up saturation a bit
im = ImageEnhance.Contrast(im).enhance(1.15)
im = im.resize((COLS, ROWS), Image.LANCZOS)
px = im.load()

cells = []  # rows of (char, "#rrggbb")
for y in range(ROWS):
    row = []
    for x in range(COLS):
        r, g, b = px[x, y]
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        idx = min(len(RAMP) - 1, int((1.0 - lum) * (len(RAMP) - 1) + 0.5))
        ch = RAMP[idx]
        if ch == " ":
            ch = "."  # keep a faint mark instead of a true blank
        # lift shadows so dark hair/frames don't vanish into the dark bg,
        # while keeping hue -- only the "value" channel is floored.
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        v = 0.30 + v * 0.70
        s = min(1.0, s * 1.15)
        r2, g2, b2 = (int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
        row.append((ch, f"#{r2:02x}{g2:02x}{b2:02x}"))
    cells.append(row)

# ---- 2. build SVG ----------------------------------------------------------
REVEAL = 2.6   # seconds for the wave to sweep top -> bottom
HOLD = 3.2     # seconds fully visible
FADE = 1.0     # seconds to fade out together
TOTAL = REVEAL + HOLD + FADE

parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)

# background + frame
parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="10" fill="{BG}">'
              f'<animate attributeName="fill" values="{BG};{BG2};{BG}" dur="{TOTAL*1.6:.2f}s" '
              f'repeatCount="indefinite"/></rect>')
parts.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="10" '
              f'fill="none" stroke="{FRAME}" stroke-width="1"/>')

# title bar
parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-width="1"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
              f'text-anchor="middle">avi@github: ~/ascii-cam.sh</text>')

# ascii rows, each in its own <g> with a staggered opacity wave
art_top = TITLEBAR_H + PAD * 0.4
for ry, row in enumerate(cells):
    t_show = (ry / ROWS) * REVEAL + 0.25
    a = t_show / TOTAL
    b = (REVEAL + HOLD) / TOTAL
    key_times = f"0;{a:.4f};{b:.4f};1"
    y = art_top + ry * CELL_H + CELL_H * 0.72
    tspans = []
    for cx, (ch, color) in enumerate(row):
        x = PAD + cx * CELL_W
        safe = html.escape(ch)
        tspans.append(
            f'<tspan x="{x}" textLength="{CELL_W}" lengthAdjust="spacingAndGlyphs" '
            f'fill="{color}">{safe}</tspan>'
        )
    parts.append(
        f'<g opacity="0"><animate attributeName="opacity" values="0;1;1;0" '
        f'keyTimes="{key_times}" dur="{TOTAL:.2f}s" repeatCount="indefinite"/>'
        f'<text font-size="{CELL_H*0.82:.1f}" y="{y:.1f}">{"".join(tspans)}</text></g>'
    )

# status bar with blinking cursor
status_y = TITLEBAR_H + ART_H + PAD * 0.4 + 16
parts.append(f'<line x1="0" y1="{TITLEBAR_H + ART_H + PAD*0.4}" x2="{CANVAS_W}" '
              f'y2="{TITLEBAR_H + ART_H + PAD*0.4}" stroke="{FRAME}" stroke-width="1"/>')
parts.append(f'<text x="{PAD}" y="{status_y}" fill="#58a6ff" font-size="13">'
              f'avi@github:~$ whoami <tspan fill="#e6edf3">Avi Vashishta</tspan></text>')
parts.append(f'<rect x="{PAD+195}" y="{status_y-12}" width="8" height="14" fill="#58a6ff">'
              f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
              f'dur="1s" repeatCount="indefinite"/></rect>')

parts.append("</svg>")
svg = "".join(parts)

with open(OUT, "w") as f:
    f.write(svg)

print("wrote", OUT, len(svg), "bytes")
print("canvas", CANVAS_W, "x", CANVAS_H)
