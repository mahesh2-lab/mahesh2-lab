"""
Convert a portrait photo into a cinematic, glitch-decode ASCII-art SVG for a
GitHub profile README.

GitHub renders SVGs embedded via <img>, and both SMIL (<animate>) and CSS
@keyframes inside the SVG run in that context (JS does not). We lean on CSS
keyframes for the per-row decode flicker (cheap, one <style> block) and SMIL
for the big moving pieces (scan bar, RGB-split glitch, CRT flicker).

Effect stack, back to front:
  1. terminal chrome (title bar, traffic lights, status bar w/ cursor)
  2. CRT vignette + faint scanline texture
  3. the ASCII art, revealed on a diagonal wavefront; each row decodes in
     (fade + blur -> settle)
  4. two low-opacity red/cyan ghost copies that jitter -> chromatic aberration
  5. a bright cyan scan bar sweeping top -> bottom, with glow
"""
from PIL import Image, ImageEnhance
import colorsys
import html
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "avi-ascii.svg")

COLS = 88
ROWS = 44
CELL_W = 8
CELL_H = 15
RAMP = " .:-=+*#%@"  # low density -> high density

PAD = 18
TITLEBAR_H = 30
STATUS_H = 28
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
CANVAS_W = ART_W + PAD * 2
CANVAS_H = TITLEBAR_H + ART_H + STATUS_H + PAD

BG = "#0a0e14"
BG2 = "#0d1420"
FRAME = "#1f6feb"
TITLE_TEXT = "#7d8590"
ACCENT = "#22d3ee"  # neon cyan scan bar / cursor

# ---- 1. sample the image into a COLS x ROWS grid --------------------------
im = Image.open(SRC).convert("RGB")
im = ImageEnhance.Color(im).enhance(1.45)      # punch up saturation
im = ImageEnhance.Contrast(im).enhance(1.18)
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
        # keep hue, floor only the value channel, punch saturation a touch.
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        v = 0.32 + v * 0.68
        s = min(1.0, s * 1.20)
        r2, g2, b2 = (int(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))
        row.append((ch, f"#{r2:02x}{g2:02x}{b2:02x}"))
    cells.append(row)

# ---- timing ---------------------------------------------------------------
REVEAL = 2.4     # seconds for the diagonal wavefront to cross the frame
HOLD = 4.6       # seconds fully visible
LOOP = REVEAL + HOLD  # single cycle length for the art

art_top = TITLEBAR_H + PAD * 0.35

# ---- 2. build the ascii <text> once; reused for the ghost copies ----------
def build_art_text():
    lines = []
    for ry, row in enumerate(cells):
        y = art_top + ry * CELL_H + CELL_H * 0.74
        tspans = []
        for cx, (ch, color) in enumerate(row):
            x = PAD + cx * CELL_W
            tspans.append(f'<tspan x="{x}" fill="{color}">{html.escape(ch)}</tspan>')
        lines.append(
            f'<text font-size="{CELL_H*0.86:.1f}" y="{y:.1f}" '
            f'textLength="{ART_W}" lengthAdjust="spacing">{"".join(tspans)}</text>'
        )
    return "".join(lines)

# Per-row reveal: each row is its own <g> so the wavefront can stagger it.
def build_reveal_rows():
    out = []
    for ry, row in enumerate(cells):
        y = art_top + ry * CELL_H + CELL_H * 0.74
        delay = (ry / ROWS) * REVEAL   # rows deeper down start later
        tspans = []
        for cx, (ch, color) in enumerate(row):
            x = PAD + cx * CELL_W
            tspans.append(f'<tspan x="{x}" fill="{color}">{html.escape(ch)}</tspan>')
        out.append(
            f'<g class="row" style="animation-delay:{delay:.3f}s">'
            f'<text font-size="{CELL_H*0.86:.1f}" y="{y:.1f}" '
            f'textLength="{ART_W}" lengthAdjust="spacing">{"".join(tspans)}</text></g>'
        )
    return "".join(out)

ART_TEXT = build_art_text()

# ---- 3. assemble SVG ------------------------------------------------------
css = f"""
@keyframes decode {{
  0%   {{ opacity: 0; filter: blur(1.4px); }}
  50%  {{ opacity: 0.5; }}
  60%  {{ opacity: 1; filter: blur(0); }}
  100% {{ opacity: 1; filter: blur(0); }}
}}
.row {{ opacity: 0; animation: decode {LOOP:.2f}s cubic-bezier(.2,.8,.2,1) infinite; }}
@keyframes flick {{
  0%,96%,100% {{ opacity: 1; }}
  97% {{ opacity: 0.82; }}
  98.5% {{ opacity: 0.95; }}
}}
.art {{ animation: flick 5.5s steps(1,end) infinite; }}
""".strip()

parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{CANVAS_H}" '
    f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" font-family="ui-monospace, SFMono-Regular, '
    f'Menlo, Consolas, monospace">'
)
parts.append(f'<style>{css}</style>')

parts.append('<defs>')
parts.append(
    f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>'
)
parts.append(
    '<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
    '<rect width="4" height="1" fill="#000000" opacity="0.18"/></pattern>'
)
parts.append(
    '<radialGradient id="vig" cx="50%" cy="42%" r="75%">'
    '<stop offset="55%" stop-color="#000000" stop-opacity="0"/>'
    '<stop offset="100%" stop-color="#000000" stop-opacity="0.55"/></radialGradient>'
)
parts.append(
    f'<linearGradient id="scanbar" x1="0" y1="0" x2="0" y2="1">'
    f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/>'
    f'<stop offset="0.5" stop-color="{ACCENT}" stop-opacity="0.9"/>'
    f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>'
)
parts.append('<filter id="soft"><feGaussianBlur stdDeviation="1.1"/></filter>')
parts.append('</defs>')

parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" rx="12" fill="url(#bg)"/>')
parts.append(f'<rect x="0.5" y="0.5" width="{CANVAS_W-1}" height="{CANVAS_H-1}" rx="12" '
             f'fill="none" stroke="{FRAME}" stroke-width="1" stroke-opacity="0.55"/>')

parts.append(f'<line x1="0" y1="{TITLEBAR_H}" x2="{CANVAS_W}" y2="{TITLEBAR_H}" stroke="{FRAME}" stroke-opacity="0.35" stroke-width="1"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{CANVAS_W/2}" y="{TITLEBAR_H/2 + 4}" fill="{TITLE_TEXT}" font-size="12" '
             f'text-anchor="middle">avi@github: ~/ascii-cam.sh --decode</text>')

clip_y = TITLEBAR_H + 1
clip_h = ART_H + PAD * 0.7
parts.append(f'<clipPath id="artclip"><rect x="1" y="{clip_y}" width="{CANVAS_W-2}" height="{clip_h:.1f}"/></clipPath>')
parts.append('<g clip-path="url(#artclip)">')

# chromatic-aberration ghosts (whole-art copies, jittering x)
parts.append(
    f'<g opacity="0.32" style="mix-blend-mode:screen"><g fill="#ff2d55">{ART_TEXT}'
    f'<animateTransform attributeName="transform" type="translate" '
    f'values="0 0; 1.6 0; 0 0; -1.3 0; 0 0" keyTimes="0;0.25;0.5;0.75;1" '
    f'dur="4.3s" repeatCount="indefinite"/></g></g>'
)
parts.append(
    f'<g opacity="0.32" style="mix-blend-mode:screen"><g fill="#22d3ee">{ART_TEXT}'
    f'<animateTransform attributeName="transform" type="translate" '
    f'values="0 0; -1.6 0; 0 0; 1.3 0; 0 0" keyTimes="0;0.25;0.5;0.75;1" '
    f'dur="4.3s" repeatCount="indefinite"/></g></g>'
)

# the real, colored art with the per-row decode reveal + CRT flicker
parts.append(f'<g class="art">{build_reveal_rows()}</g>')

parts.append(f'<rect x="1" y="{clip_y}" width="{CANVAS_W-2}" height="{clip_h:.1f}" fill="url(#scan)"/>')

bar_h = 26
parts.append(
    f'<rect x="1" width="{CANVAS_W-2}" height="{bar_h}" y="{clip_y}" fill="url(#scanbar)" '
    f'filter="url(#soft)" opacity="0.75">'
    f'<animate attributeName="y" values="{clip_y};{clip_y+clip_h:.1f};{clip_y}" '
    f'keyTimes="0;0.85;1" dur="{LOOP:.2f}s" repeatCount="indefinite"/></rect>'
)
parts.append('</g>')  # end artclip

parts.append(f'<rect x="1" y="{clip_y}" width="{CANVAS_W-2}" height="{clip_h:.1f}" fill="url(#vig)"/>')

status_line_y = TITLEBAR_H + ART_H + PAD * 0.35
status_y = status_line_y + 18
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{CANVAS_W}" y2="{status_line_y:.1f}" '
             f'stroke="{FRAME}" stroke-opacity="0.35" stroke-width="1"/>')
parts.append(f'<text x="{PAD}" y="{status_y:.1f}" fill="{ACCENT}" font-size="13">'
             f'avi@github:~$ whoami <tspan fill="#e6edf3">Avi Vashishta</tspan></text>')
parts.append(f'<rect x="{PAD+196}" y="{status_y-12:.1f}" width="8" height="14" fill="{ACCENT}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" '
             f'dur="1s" repeatCount="indefinite"/></rect>')

parts.append("</svg>")
svg = "".join(parts)

with open(OUT, "w") as f:
    f.write(svg)

print("wrote", OUT, len(svg), "bytes;", CANVAS_W, "x", CANVAS_H)
