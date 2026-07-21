#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import html
from datetime import datetime

# GitHub User and Authentication
USER = sys.argv[1] if len(sys.argv) > 1 else "mahesh2-lab"
TOKEN = os.environ.get("GH_TOKEN")

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(HERE, "..", "card-template.svg")
OUTPUT_PATH = os.path.join(HERE, "..", "card.svg")
CONTRIBS_PATH = os.path.join(HERE, "..", "data", "contributions.json")

# Fallback transparent 1x1 image for missing organization logos
TRANSPARENT_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Default dummy fallback data for local / unauthenticated generation
DUMMY_DATA = {
    "name": "Mahesh",
    "username": "mahesh2-lab",
    "bio_line1": "Full Stack Developer & Backend Engineer",
    "bio_line2": "Building Caïssa Monitoring Platform",
    "company": "Caïssa",
    "location": "Buldhana, India",
    "website": "mahesh2-lab.github.io",
    "joined_date": "Jul 2025",
    "followers": "42",
    "following": "28",
    "stars": "128",
    "org_avatar1": TRANSPARENT_IMAGE,
    "org_avatar2": TRANSPARENT_IMAGE,
    "org_avatar3": TRANSPARENT_IMAGE,
    "views": "1,250",
    "commits": "1450",
    "prs": "32",
    "issues": "18",
    "reviews": "5",
    "rank": "A+",
    "rank_percentile": "1.0",
    "streak_current": "12",
    "streak_longest": "24",
    "repo1_name": "caissa-monitoring",
    "repo1_desc_line1": "AI Infrastructure Monitoring Platform",
    "repo1_stars": "84",
    "repo1_forks": "12",
    "repo2_name": "vercel-clone",
    "repo2_desc_line1": "Deployment Platform with real-time logs",
    "repo2_stars": "44",
    "repo2_forks": "6",
    "total_year_contributions": "1,532"
}


def calculate_rank(commits, prs, issues, reviews, stars, followers):
    score = commits * 0.5 + prs * 1.0 + issues * 1.0 + reviews * 1.0 + stars * 10.0 + followers * 2.0
    if score >= 10000:
        return "S+", "0.01"
    elif score >= 5000:
        return "S", "0.1"
    elif score >= 2000:
        return "A+", "1.0"
    elif score >= 1000:
        return "A", "5.0"
    elif score >= 500:
        return "A-", "10.0"
    elif score >= 250:
        return "B+", "25.0"
    elif score >= 100:
        return "B", "50.0"
    else:
        return "B-", "75.0"


def format_desc(desc):
    if not desc:
        return ""
    if len(desc) > 42:
        return desc[:39] + "..."
    return desc


def fetch_github_data():
    if not TOKEN:
        print("No GH_TOKEN environment variable found. Using dummy fallback values.")
        return DUMMY_DATA

    query = """
    query($login: String!) {
      user(login: $login) {
        name
        login
        bio
        company
        location
        websiteUrl
        createdAt
        followers { totalCount }
        following { totalCount }
        starredRepositories { totalCount }
        organizations(first: 3) {
          nodes {
            avatarUrl
          }
        }
        issues { totalCount }
        pullRequests { totalCount }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestReviewContributions
        }
        repositories(first: 6, orderBy: {field: STARGAZERS, direction: DESC}, ownerAffiliations: OWNER, isFork: false) {
          nodes {
            name
            description
            stargazerCount
            forkCount
          }
        }
      }
    }
    """

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "python-github-card-generator"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if "errors" in res:
                print("GraphQL Errors:", res["errors"])
                return DUMMY_DATA

            u = res["data"]["user"]
            
            # Format Bio into 2 lines
            bio = u.get("bio") or ""
            words = bio.split()
            line1, line2 = "", ""
            for word in words:
                if len(line1) + len(word) + 1 <= 45:
                    line1 = f"{line1} {word}".strip()
                elif len(line2) + len(word) + 1 <= 45:
                    line2 = f"{line2} {word}".strip()
                else:
                    break

            # Format joined date
            created_at = u.get("createdAt")
            joined_date = "Jul 2025"
            if created_at:
                try:
                    dt = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                    joined_date = dt.strftime("%b %Y")
                except Exception:
                    pass

            # Parse organizations
            org_nodes = u.get("organizations", {}).get("nodes", [])
            org_avatar1 = org_nodes[0]["avatarUrl"] if len(org_nodes) > 0 else TRANSPARENT_IMAGE
            org_avatar2 = org_nodes[1]["avatarUrl"] if len(org_nodes) > 1 else TRANSPARENT_IMAGE
            org_avatar3 = org_nodes[2]["avatarUrl"] if len(org_nodes) > 2 else TRANSPARENT_IMAGE

            # Parse repositories (top 2 by stars)
            repos = u.get("repositories", {}).get("nodes", [])
            repo1_name, repo1_desc, repo1_stars, repo1_forks = "", "", "0", "0"
            repo2_name, repo2_desc, repo2_stars, repo2_forks = "", "", "0", "0"

            if len(repos) > 0:
                repo1_name = repos[0]["name"]
                repo1_desc = format_desc(repos[0]["description"])
                repo1_stars = str(repos[0]["stargazerCount"])
                repo1_forks = str(repos[0]["forkCount"])
            if len(repos) > 1:
                repo2_name = repos[1]["name"]
                repo2_desc = format_desc(repos[1]["description"])
                repo2_stars = str(repos[1]["stargazerCount"])
                repo2_forks = str(repos[1]["forkCount"])

            # Compute stars sum
            total_stars = sum(r["stargazerCount"] for r in repos)

            # Core stats
            commits = u["contributionsCollection"]["totalCommitContributions"]
            prs = u["pullRequests"]["totalCount"]
            issues = u["issues"]["totalCount"]
            reviews = u["contributionsCollection"]["totalPullRequestReviewContributions"]
            followers = u["followers"]["totalCount"]
            following = u["following"]["totalCount"]

            # Ranks
            rank, percentile = calculate_rank(commits, prs, issues, reviews, total_stars, followers)

            return {
                "name": u.get("name") or u.get("login") or USER,
                "username": u.get("login") or USER,
                "bio_line1": line1,
                "bio_line2": line2,
                "company": u.get("company") or "Freelance",
                "location": u.get("location") or "Worldwide",
                "website": u.get("websiteUrl") or "github.com",
                "joined_date": joined_date,
                "followers": f"{followers:,}",
                "following": f"{following:,}",
                "stars": f"{total_stars:,}",
                "org_avatar1": org_avatar1,
                "org_avatar2": org_avatar2,
                "org_avatar3": org_avatar3,
                "views": "1,250",  # Default placeholder for profile views
                "commits": f"{commits:,}",
                "prs": f"{prs:,}",
                "issues": f"{issues:,}",
                "reviews": f"{reviews:,}",
                "rank": rank,
                "rank_percentile": percentile,
                "streak_current": "0",  # Populated via contributions.json below
                "streak_longest": "0",  # Populated via contributions.json below
                "repo1_name": repo1_name,
                "repo1_desc_line1": repo1_desc,
                "repo1_stars": repo1_stars,
                "repo1_forks": repo1_forks,
                "repo2_name": repo2_name,
                "repo2_desc_line1": repo2_desc,
                "repo2_stars": repo2_stars,
                "repo2_forks": repo2_forks,
                "total_year_contributions": "0"  # Populated via contributions.json below
            }
    except Exception as e:
        print("Error calling GraphQL API, using fallback data:", e)
        return DUMMY_DATA


def enrich_from_contributions(data):
    if not os.path.exists(CONTRIBS_PATH):
        print(f"No contributions JSON found at {CONTRIBS_PATH}. Using fallback streak values.")
        return

    try:
        with open(CONTRIBS_PATH, "r", encoding="utf-8") as f:
            c = json.load(f)
            data["streak_current"] = str(c.get("current_streak", {}).get("length", 0))
            data["streak_longest"] = str(c.get("longest_streak", {}).get("length", 0))
            data["total_year_contributions"] = f"{c.get('total_contributions', 0):,}"
            print("Successfully enriched stats using contributions.json data.")
    except Exception as e:
        print("Error parsing contributions.json:", e)


def main():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: Template file {TEMPLATE_PATH} does not exist. Run Copy-Item card.svg card-template.svg first.")
        sys.exit(1)

    data = fetch_github_data()
    enrich_from_contributions(data)

    # Read template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        svg_content = f.read()

    # Replacements
    for key, value in data.items():
        placeholder = "{{" + key + "}}"
        escaped_value = html.escape(str(value))
        svg_content = svg_content.replace(placeholder, escaped_value)

    # Write output SVG
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"Successfully generated custom GitHub card at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
