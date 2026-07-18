#!/usr/bin/env python3
import sys, json, os, urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "mahesh2-lab"
TOKEN = os.environ.get("GH_TOKEN")

# Fallback dummy data if no token is provided for local generation
dummy_data = {
    "stars": 128,
    "commits": 1450,
    "prs": 32,
    "issues": 18,
    "langs": [
        {"name": "TypeScript", "color": "#3178c6", "size": 150000},
        {"name": "Python", "color": "#3572A5", "size": 120000},
        {"name": "JavaScript", "color": "#f1e05a", "size": 80000},
        {"name": "HTML", "color": "#e34c26", "size": 40000},
        {"name": "CSS", "color": "#563d7c", "size": 30000}
    ]
}

def fetch_data():
    if not TOKEN:
        print("No GH_TOKEN found, using dummy data.")
        return dummy_data
        
    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
        issues { totalCount }
        pullRequests { totalCount }
        contributionsCollection {
          totalCommitContributions
        }
      }
    }
    """
    
    req = urllib.request.Request("https://api.github.com/graphql", 
                                 data=json.dumps({"query": query, "variables": {"login": USER}}).encode("utf-8"),
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            u = res["data"]["user"]
            
            stars = 0
            lang_stats = {}
            for repo in u["repositories"]["nodes"]:
                stars += repo["stargazerCount"]
                for lang in repo["languages"]["edges"]:
                    name = lang["node"]["name"]
                    color = lang["node"]["color"]
                    size = lang["size"]
                    if name not in lang_stats:
                        lang_stats[name] = {"name": name, "color": color, "size": 0}
                    lang_stats[name]["size"] += size
            
            sorted_langs = sorted(lang_stats.values(), key=lambda x: x["size"], reverse=True)
            
            return {
                "stars": stars,
                "commits": u["contributionsCollection"]["totalCommitContributions"],
                "prs": u["pullRequests"]["totalCount"],
                "issues": u["issues"]["totalCount"],
                "langs": sorted_langs[:5]
            }
    except Exception as e:
        print("Error fetching GraphQL data:", e)
        return dummy_data

def generate_stats_svg(data, out="github-stats.svg"):
    # Tokyonight colors with bg_color=0d1117
    BG = "#0d1117"
    TITLE_COLOR = "#70a5fd"
    TEXT_COLOR = "#38bdae"
    ICON_COLOR = "#bf91f3"
    VALUE_COLOR = "#c0caf5"

    # SVG icon paths
    star_icon = '<path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path>'
    commit_icon = '<path fill-rule="evenodd" d="M10.5 7.75a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm1.43.75a4.002 4.002 0 01-7.86 0H.75a.75.75 0 110-1.5h3.32a4.001 4.001 0 017.86 0h3.32a.75.75 0 110 1.5h-3.32z"></path>'
    pr_icon = '<path fill-rule="evenodd" d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113.598 1.8l3.598 3.598A2.25 2.25 0 117.25 10.25l-3.6-3.6A2.25 2.25 0 011.5 3.25zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 114.5 0 2.25 2.25 0 01-4.5 0z"></path>'
    issue_icon = '<path fill-rule="evenodd" d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z"></path>'

    items = [
        (star_icon, "Total Stars Earned", data["stars"]),
        (commit_icon, "Total Commits (2026)", data["commits"]),
        (pr_icon, "Total PRs", data["prs"]),
        (issue_icon, "Total Issues", data["issues"])
    ]

    svg_items = ""
    y_start = 55
    spacing = 33
    for i, (icon, label, value) in enumerate(items):
        y = y_start + i * spacing
        svg_items += f'''
        <g transform="translate(25, {y})">
            <svg x="0" y="-12" viewBox="0 0 16 16" width="16" height="16" fill="{ICON_COLOR}">
                {icon}
            </svg>
            <text class="stat-label" x="25" y="0">{label}</text>
            <text class="stat-value" x="420" y="0" text-anchor="end" data-testid="{label.lower().split()[1]}">{value}</text>
        </g>
        '''

    svg = f'''<svg width="452" height="195" viewBox="0 0 452 195" fill="none" xmlns="http://www.w3.org/2000/svg">
    <style>
        .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE_COLOR}; }}
        .stat-label {{ font: 400 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT_COLOR}; }}
        .stat-value {{ font: 600 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: {VALUE_COLOR}; }}
    </style>
    <rect x="0.5" y="0.5" width="451" height="194" rx="4.5" fill="{BG}" stroke="#e4e2e2" stroke-opacity="0"/>
    <text x="25" y="35" class="header">{USER}'s GitHub Stats</text>
    {svg_items}
</svg>'''

    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)

def generate_langs_svg(data, out="top-langs.svg"):
    BG = "#0d1117"
    TITLE_COLOR = "#70a5fd"
    TEXT_COLOR = "#38bdae"
    
    langs = data["langs"]
    total_size = sum(l["size"] for l in langs) if langs else 1

    svg_items = ""
    y_start = 65
    spacing = 32
    
    for i, l in enumerate(langs):
        y = y_start + i * spacing
        pct = (l["size"] / total_size) * 100
        # Progress bar
        bar_w = 250
        bar_fill = (pct / 100) * bar_w
        
        svg_items += f'''
        <g transform="translate(25, {y})">
            <text class="lang-name" x="0" y="0">{l["name"]}</text>
            <text class="lang-pct" x="250" y="0" text-anchor="end">{pct:.1f}%</text>
            <rect x="0" y="8" width="{bar_w}" height="8" rx="4" fill="#30363d"/>
            <rect x="0" y="8" width="{bar_fill}" height="8" rx="4" fill="{l["color"]}"/>
        </g>
        '''

    svg = f'''<svg width="300" height="235" viewBox="0 0 300 235" fill="none" xmlns="http://www.w3.org/2000/svg">
    <style>
        .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE_COLOR}; }}
        .lang-name {{ font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT_COLOR}; }}
        .lang-pct {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #8b949e; }}
    </style>
    <rect x="0.5" y="0.5" width="299" height="234" rx="4.5" fill="{BG}" stroke="#e4e2e2" stroke-opacity="0"/>
    <text x="25" y="35" class="header">Most Used Languages</text>
    {svg_items}
</svg>'''

    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)

if __name__ == "__main__":
    d = fetch_data()
    generate_stats_svg(d)
    generate_langs_svg(d)
    print("Generated github-stats.svg and top-langs.svg")
