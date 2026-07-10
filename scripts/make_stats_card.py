"""
Build a self-hosted, animated stats card SVG for the profile README.

This exists to REPLACE github-readme-stats.vercel.app, which is chronically
rate-limited and renders as a broken image. This card lives in the repo, so it
never 404s. It's animated (SMIL): numbers wipe in, language bars grow, and a
neon underline sweeps across the header.

Data sources, in order of preference:
  - live totals passed via env (STARS / REPOS / FOLLOWERS / LANGS), which the
    daily workflow fills from the authenticated GitHub API
  - otherwise the baked-in fallbacks below (current as of the last manual run)
Contribution figures (commits / streaks / best day) always come from
data/contributions.json, which the workflow refreshes with no auth.
"""
import collections
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "AVIVASHISHTA29"


def fetch_live_stats():
    """Query the GitHub GraphQL API for repos/stars/followers/languages.

    Uses GITHUB_TOKEN when present (the daily Actions run provides one). Any
    failure returns None so the caller falls back to the baked-in numbers --
    the card must never break just because the API is unreachable.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None
    query = """{ user(login: "%s") {
      followers { totalCount }
      repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                   orderBy: {field: STARGAZERS, direction: DESC}) {
        totalCount
        nodes {
          stargazerCount
          languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
            edges { size node { name color } } }
        } } } }""" % USER
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={"Authorization": f"bearer {token}",
                     "Content-Type": "application/json",
                     "User-Agent": USER},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            u = json.load(r)["data"]["user"]
        nodes = u["repositories"]["nodes"]
        lang = collections.Counter()
        for n in nodes:
            for e in n["languages"]["edges"]:
                lang[(e["node"]["name"], e["node"]["color"] or "#8b949e")] += e["size"]
        tot = sum(lang.values()) or 1
        langs = [(name, 100 * size / tot, color)
                 for (name, color), size in lang.most_common(6)]
        return {
            "stars": sum(n["stargazerCount"] for n in nodes),
            "repos": u["repositories"]["totalCount"],
            "followers": u["followers"]["totalCount"],
            "langs": langs,
        }
    except Exception as e:  # noqa: BLE001 -- never let a fetch error break the card
        print("live stats fetch failed, using fallback:", e)
        return None


CONTRIB = os.path.join(HERE, "..", "data", "contributions.json")
OUT = os.path.join(HERE, "..", "stats-card.svg")

with open(CONTRIB) as f:
    c = json.load(f)

# --- gather numbers --------------------------------------------------------
total_commits = c["total_contributions"]
cur_streak = c["current_streak"]["length"]
long_streak = c["longest_streak"]["length"]
best_day = c["best_day"]["count"]
active_days = c["active_days"]

live = fetch_live_stats()

stars = live["stars"] if live else int(os.environ.get("STARS", 117))
repos = live["repos"] if live else int(os.environ.get("REPOS", 164))
followers = live["followers"] if live else int(os.environ.get("FOLLOWERS", 314))

if live and live["langs"]:
    langs = live["langs"]
else:
    langs = [
        ("TypeScript", 47.6, "#3178c6"),
        ("JavaScript", 21.6, "#f1e05a"),
        ("HTML",       20.3, "#e34c26"),
        ("Haskell",     5.1, "#5e5086"),
        ("CSS",         2.8, "#663399"),
        ("Python",      1.5, "#3572A5"),
    ]

def commafy(n):
    return f"{n:,}"

# STATIC=1 emits the frozen final state (no animation) so a Quick Look thumbnail
# shows the real composed layout; the README always uses the animated build.
STATIC = bool(os.environ.get("STATIC"))

# --- layout ----------------------------------------------------------------
W, H = 480, 512
PAD = 22
BG = "#0a0e14"
BG2 = "#0d1420"
FRAME = "#1f6feb"
MUTED = "#7d8590"
TEXT = "#e6edf3"
ACCENT = "#22d3ee"
GOLD = "#f2cc60"

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
]

# defs
parts.append('<defs>')
parts.append(f'<linearGradient id="cbg" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>')
parts.append(f'<linearGradient id="hl" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{ACCENT}"/><stop offset="1" stop-color="{FRAME}"/></linearGradient>')
parts.append('</defs>')

# frame + title bar
parts.append(f'<rect width="{W}" height="{H}" rx="12" fill="url(#cbg)"/>')
parts.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="none" '
             f'stroke="{FRAME}" stroke-width="1" stroke-opacity="0.55"/>')
parts.append(f'<line x1="0" y1="30" x2="{W}" y2="30" stroke="{FRAME}" stroke-opacity="0.35"/>')
for i, dotcol in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD + i*16}" cy="15" r="5" fill="{dotcol}"/>')
parts.append(f'<text x="{W/2}" y="19" fill="{MUTED}" font-size="12" text-anchor="middle">'
             f'avi@github: ~/stats --live</text>')

# animation helper: fade+rise in with a per-element delay
def rise(x, y, inner, delay, dur=0.5):
    if STATIC:
        return f'<g>{inner}</g>'
    return (f'<g opacity="0" transform="translate(0,6)">{inner}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur="{dur}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="0 6" to="0 0" '
            f'begin="{delay}s" dur="{dur}s" fill="freeze" calcMode="spline" '
            f'keySplines="0.2 0.8 0.2 1"/></g>')

y = 62
parts.append(rise(0, 0, f'<text x="{PAD}" y="{y}" fill="{TEXT}" font-size="19" font-weight="700">'
                        f'Avi Vashishta</text>', 0.05))
parts.append(rise(0, 0, f'<text x="{PAD}" y="{y+20}" fill="{ACCENT}" font-size="12.5">'
                        f'Fullstack &#183; AI Builder &#183; Instructor</text>', 0.12))
# animated underline sweep
if STATIC:
    parts.append(f'<rect x="{PAD}" y="{y+30}" height="2.5" rx="1.5" width="220" fill="url(#hl)"/>')
else:
    parts.append(f'<rect x="{PAD}" y="{y+30}" height="2.5" rx="1.5" width="0" fill="url(#hl)">'
                 f'<animate attributeName="width" from="0" to="220" begin="0.2s" dur="0.7s" '
                 f'fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/></rect>')

# --- 2x3 stat grid ---------------------------------------------------------
stats = [
    (commafy(total_commits), "contributions / yr", ACCENT),
    (commafy(repos),         "public repos",       TEXT),
    (str(stars),             "stars earned",       GOLD),
    (str(followers),         "followers",          TEXT),
    (f"{cur_streak}d",       "current streak",     "#27c93f"),
    (f"{long_streak}d",      "longest streak",     ACCENT),
]
gx0, gy0 = PAD, y + 52
col_w = (W - PAD * 2) / 3
row_h = 62
for i, (big, label, col) in enumerate(stats):
    r, cc = divmod(i, 3)
    cx = gx0 + cc * col_w
    cy = gy0 + r * row_h
    delay = 0.35 + i * 0.09
    cell = (f'<text x="{cx:.0f}" y="{cy+22:.0f}" fill="{col}" font-size="26" font-weight="800">{big}</text>'
            f'<text x="{cx:.0f}" y="{cy+40:.0f}" fill="{MUTED}" font-size="11">{label}</text>')
    parts.append(rise(0, 0, cell, delay))

# divider
dy = gy0 + 2 * row_h + 6
parts.append(f'<line x1="{PAD}" y1="{dy}" x2="{W-PAD}" y2="{dy}" stroke="{FRAME}" stroke-opacity="0.25"/>')

# best-day callout
parts.append(rise(0, 0,
    f'<text x="{PAD}" y="{dy+24}" fill="{MUTED}" font-size="12">best day '
    f'<tspan fill="{GOLD}" font-weight="700">{best_day} commits</tspan>'
    f'<tspan fill="{MUTED}">  &#183;  {active_days} active days</tspan></text>', 0.9))

# --- language bars ---------------------------------------------------------
ly = dy + 46
parts.append(rise(0, 0, f'<text x="{PAD}" y="{ly}" fill="{TEXT}" font-size="13" font-weight="700">'
                        f'Most used languages</text>', 1.0))
bar_x = PAD
bar_w_full = W - PAD * 2
by = ly + 14
# single stacked proportion bar
parts.append(f'<clipPath id="barclip"><rect x="{bar_x}" y="{by}" width="{bar_w_full}" height="12" rx="6"/></clipPath>')
parts.append(f'<g clip-path="url(#barclip)">')
parts.append(f'<rect x="{bar_x}" y="{by}" width="{bar_w_full}" height="12" fill="#161b22"/>')
run = 0.0
seg_total = sum(p for _, p, _ in langs) or 1
for name, pct, color in langs:
    seg_w = bar_w_full * (pct / seg_total)
    if STATIC:
        parts.append(f'<rect x="{bar_x+run:.1f}" y="{by}" width="{seg_w:.1f}" height="12" fill="{color}"/>')
    else:
        parts.append(f'<rect x="{bar_x+run:.1f}" y="{by}" width="0" height="12" fill="{color}">'
                     f'<animate attributeName="width" from="0" to="{seg_w:.1f}" begin="1.15s" dur="0.8s" '
                     f'fill="freeze" calcMode="spline" keySplines="0.2 0.8 0.2 1"/></rect>')
    run += seg_w
parts.append('</g>')

# language legend (two columns)
leg_y = by + 30
for i, (name, pct, color) in enumerate(langs):
    r, cc = divmod(i, 2)
    lx = PAD + cc * (bar_w_full / 2)
    lyy = leg_y + r * 20
    parts.append(rise(0, 0,
        f'<circle cx="{lx+5:.0f}" cy="{lyy-4:.0f}" r="5" fill="{color}"/>'
        f'<text x="{lx+16:.0f}" y="{lyy:.0f}" fill="{TEXT}" font-size="12">{name} '
        f'<tspan fill="{MUTED}">{pct:.1f}%</tspan></text>', 1.3 + i * 0.05))

parts.append("</svg>")
svg = "".join(parts)
with open(OUT, "w") as f:
    f.write(svg)
print("wrote", OUT, len(svg), "bytes;", W, "x", H)
