#!/usr/bin/env python3
"""
Fetch live GitHub telemetry for Elvinoacer and render the calm, light/dark adaptive
SVG visual suite plus dynamic README sections.

Zero external dependencies (Python 3 standard library only) so GitHub Actions stays
fast, reliable, and maintenance-free.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
README_PATH = ROOT / "README.md"

USERNAME = os.environ.get("GITHUB_USERNAME", "Elvinoacer")
EAT_TZ = timezone(timedelta(hours=3))

# Calm, harmonized themes — "Highland Morning" (Light) & "Still Dusk" (Dark)
THEMES: dict[str, dict[str, Any]] = {
    "light": {
        "canvas": "#F7FAF8",
        "canvas_alt": "#EEF4F1",
        "surface": "#FFFFFF",
        "subtle": "#EFF5F2",
        "border": "#DCE6E1",
        "divider": "#E5EDE9",
        "ink": "#182924",
        "ink_sec": "#4C625B",
        "ink_muted": "#7A9089",
        "pine": "#2C6E5B",
        "lake": "#477A96",
        "moss": "#6C9A7F",
        "ochre": "#A8844E",
        "sky_top": "#F4F8F6",
        "sky_mid": "#E7F0EC",
        "sky_bot": "#DCE9E3",
        "orb": "#F2DFB6",
        "orb_glow": "#E8CE96",
        "ridge_far": "#7DA3B5",
        "ridge_far_stroke": "#58869C",
        "ridge_near": "#2E6D5B",
        "ridge_near_stroke": "#1E5243",
        "water_top": "#D4E3DD",
        "water_bot": "#EFF5F2",
        "ripple": "#FFFFFF",
        "ramp": ["#E8F0EC", "#C2DDD1", "#86BFA7", "#4D967B", "#276954"],
        "lang_colors": {
            "TypeScript": "#46769E",
            "JavaScript": "#C2A152",
            "HTML": "#B57862",
            "CSS": "#7270A3",
            "Python": "#4D8A70",
            "PLpgSQL": "#4A8789",
            "Shell": "#6D8C6E",
            "PowerShell": "#5E7F94",
            "Kotlin": "#866E9E",
            "Dockerfile": "#5887A1",
            "Other": "#90A39C",
        },
    },
    "dark": {
        "canvas": "#0D1117",
        "canvas_alt": "#11181E",
        "surface": "#121920",
        "subtle": "#172129",
        "border": "#22303A",
        "divider": "#1D2A33",
        "ink": "#E6EFEA",
        "ink_sec": "#95AAA3",
        "ink_muted": "#667D76",
        "pine": "#63B59B",
        "lake": "#72A6C4",
        "moss": "#88BFA0",
        "ochre": "#D1B077",
        "sky_top": "#0E141A",
        "sky_mid": "#121D24",
        "sky_bot": "#17272E",
        "orb": "#E9D9B5",
        "orb_glow": "#A5C4B6",
        "ridge_far": "#3F677D",
        "ridge_far_stroke": "#72A6C4",
        "ridge_near": "#2B6655",
        "ridge_near_stroke": "#63B59B",
        "water_top": "#122127",
        "water_bot": "#0D1419",
        "ripple": "#8EC2B0",
        "ramp": ["#172227", "#1F443A", "#2D6A59", "#47967E", "#6EC4A8"],
        "lang_colors": {
            "TypeScript": "#6498C4",
            "JavaScript": "#D1B46A",
            "HTML": "#C78B74",
            "CSS": "#8D8BC0",
            "Python": "#67AA8E",
            "PLpgSQL": "#62A3A6",
            "Shell": "#84A886",
            "PowerShell": "#789BB0",
            "Kotlin": "#A189B8",
            "Dockerfile": "#6FA2BF",
            "Other": "#6E827C",
        },
    },
}

SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', Palatino, serif"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def get_token() -> str:
    for key in ("PROFILE_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except Exception as exc:
        raise RuntimeError("No GitHub token found in env (GITHUB_TOKEN / GH_TOKEN) or gh CLI.") from exc


def graphql(token: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{USERNAME}-profile-telemetry",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def fmt_num(n: int) -> str:
    return f"{n:,}"


def fmt_short_date(iso_date: str) -> str:
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%b %-d") if os.name != "nt" else dt.strftime("%b %d").replace(" 0", " ")


def fmt_bytes(b: int) -> str:
    if b >= 1_000_000:
        return f"{b / 1_000_000:.1f} MB"
    if b >= 1_000:
        return f"{b / 1_000:.0f} KB"
    return f"{b} B"


def fmt_relative(iso_ts: str, now_utc: datetime) -> str:
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    diff = max(timedelta(0), now_utc - dt)
    hours = diff.total_seconds() / 3600.0
    if hours < 1:
        return "just now"
    if hours < 24:
        h = int(hours)
        return f"{h}h ago"
    days = int(hours // 24)
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"{days}d ago"
    if days < 60:
        return f"{days // 7}w ago"
    return dt.strftime("%b %Y")


def truncate(text: str, max_len: int) -> str:
    clean = re.sub(r"\s+", " ", (text or "").strip())
    if len(clean) <= max_len:
        return clean
    cut = clean[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-—–") + "…"


def clean_repo_description(repo_name: str, desc: str) -> str:
    text = re.sub(r"\s+", " ", (desc or "").strip())
    if not text:
        return ""
    # Strip redundant leading "Repo Name — " prefix when repo name is already in column 1
    normalized_repo = re.sub(r"[_\-\s]+", " ", repo_name).strip().lower()
    for sep in (" — ", " – ", " - ", ": "):
        if sep in text:
            head, rest = text.split(sep, 1)
            norm_head = re.sub(r"[_\-\s]+", " ", head).strip().lower()
            if norm_head == normalized_repo or normalized_repo in norm_head:
                text = rest.strip()
                if text:
                    text = text[0].upper() + text[1:]
                break
    return text


def fetch_all_github_data(token: str) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    now_eat = now_utc.astimezone(EAT_TZ)

    # 1. Core profile + rolling 365-day calendar + pinned items
    core_query = """
    query($login: String!) {
      user(login: $login) {
        id
        name
        login
        bio
        company
        location
        websiteUrl
        twitterUsername
        createdAt
        followers { totalCount }
        following { totalCount }
        pinnedItems(first: 6, types: REPOSITORY) {
          nodes {
            ... on Repository {
              name
              description
              url
              homepageUrl
              stargazerCount
              forkCount
              primaryLanguage { name }
            }
          }
        }
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
            weeks {
              firstDay
              contributionDays {
                date
                contributionCount
                weekday
              }
            }
          }
        }
      }
    }
    """
    user = graphql(token, core_query, {"login": USERNAME})["user"]
    user_id = user["id"]
    start_year = int(user["createdAt"][:4])
    current_year = now_utc.year

    # 2. Fetch EVERY year since account creation for all-time totals & all-time longest streak
    year_blocks = []
    for y in range(start_year, current_year + 1):
        year_blocks.append(
            f"""
            y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") {{
              totalCommitContributions
              totalPullRequestContributions
              totalIssueContributions
              totalPullRequestReviewContributions
              restrictedContributionsCount
              contributionCalendar {{
                totalContributions
                weeks {{
                  contributionDays {{
                    date
                    contributionCount
                    weekday
                  }}
                }}
              }}
            }}
            """
        )
    years_query = f'query($login: String!) {{ user(login: $login) {{ {" ".join(year_blocks)} }} }}'
    years_data = graphql(token, years_query, {"login": USERNAME})["user"]

    yearly_totals: list[tuple[int, int]] = []
    all_time_contributions = 0
    all_time_commits = 0
    all_time_prs = 0
    all_time_issues = 0
    all_time_reviews = 0
    all_time_restricted = 0
    all_days_map: dict[str, int] = {}

    for y in range(start_year, current_year + 1):
        yc = years_data[f"y{y}"]
        cal_total = yc["contributionCalendar"]["totalContributions"]
        yearly_totals.append((y, cal_total))
        all_time_contributions += cal_total
        all_time_commits += yc["totalCommitContributions"]
        all_time_prs += yc["totalPullRequestContributions"]
        all_time_issues += yc["totalIssueContributions"]
        all_time_reviews += yc["totalPullRequestReviewContributions"]
        all_time_restricted += yc["restrictedContributionsCount"]
        for w in yc["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                # Ignore future days in current year
                if d["date"] <= now_utc.strftime("%Y-%m-%d"):
                    all_days_map[d["date"]] = max(all_days_map.get(d["date"], 0), d["contributionCount"])

    # Sort all-time days chronologically for true all-time longest streak & current streak
    all_days_sorted = sorted(all_days_map.items(), key=lambda kv: kv[0])
    longest_streak = 0
    longest_range = ("", "")
    cur = 0
    cur_start = ""
    for dt_str, cnt in all_days_sorted:
        if cnt > 0:
            if cur == 0:
                cur_start = dt_str
            cur += 1
            if cur > longest_streak:
                longest_streak = cur
                longest_range = (cur_start, dt_str)
        else:
            cur = 0

    # Rolling 365-day calendar
    rolling_cal = user["contributionsCollection"]["contributionCalendar"]
    rolling_weeks = rolling_cal["weeks"]
    rolling_days = [d for w in rolling_weeks for d in w["contributionDays"]]
    today_str = now_utc.strftime("%Y-%m-%d")
    rolling_days_past = [d for d in rolling_days if d["date"] <= today_str]

    # Current streak (allow today == 0 if yesterday > 0 so streak stays intact early in the day)
    rev_all = list(reversed(all_days_sorted))
    idx = 0
    if rev_all and rev_all[0][1] == 0:
        idx = 1
    current_streak = 0
    current_end = rev_all[idx][0] if idx < len(rev_all) else today_str
    current_start = current_end
    for dt_str, cnt in rev_all[idx:]:
        if cnt > 0:
            current_streak += 1
            current_start = dt_str
        else:
            break

    rolling_365 = rolling_cal["totalContributions"]
    active_days = sum(1 for d in rolling_days_past if d["contributionCount"] > 0)
    total_cal_days = max(1, len(rolling_days_past))
    active_pct = (active_days / total_cal_days) * 100.0
    active_avg = rolling_365 / max(1, active_days)

    best_day = max(rolling_days_past, key=lambda d: d["contributionCount"]) if rolling_days_past else {"date": today_str, "contributionCount": 0}
    last_30 = rolling_days_past[-30:]
    rolling_30 = sum(d["contributionCount"] for d in last_30)
    rolling_7 = sum(d["contributionCount"] for d in rolling_days_past[-7:])

    # Weekday cadence (Mon=0 .. Sun=6)
    # GraphQL weekday: 0=Sun, 1=Mon, ..., 6=Sat -> remap to Mon..Sun
    dow_mon_sun = [0] * 7
    for d in rolling_days_past:
        mon_idx = (d["weekday"] - 1) % 7
        dow_mon_sun[mon_idx] += d["contributionCount"]

    # Weekly sums for the 52-week horizon mountain ridge
    weekly_series: list[dict[str, Any]] = []
    for w in rolling_weeks[-52:]:
        w_sum = sum(d["contributionCount"] for d in w["contributionDays"])
        weekly_series.append({"firstDay": w["firstDay"], "total": w_sum})

    # Last 26 weeks for the calm top-right mosaic
    mosaic_weeks = rolling_weeks[-26:]

    # 3. Paginate ALL public non-fork owned repositories for exact stars, forks, languages & recent repos
    repos_query = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        repositories(
          first: 100,
          after: $cursor,
          ownerAffiliations: OWNER,
          isFork: false,
          privacy: PUBLIC,
          orderBy: {field: PUSHED_AT, direction: DESC}
        ) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes {
            name
            description
            url
            homepageUrl
            stargazerCount
            forkCount
            pushedAt
            isArchived
            primaryLanguage { name color }
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name }
              }
            }
          }
        }
      }
    }
    """
    all_public_repos: list[dict[str, Any]] = []
    cursor: str | None = None
    public_repo_count = 0
    while True:
        res = graphql(token, repos_query, {"login": USERNAME, "cursor": cursor})["user"]["repositories"]
        public_repo_count = res["totalCount"]
        all_public_repos.extend(res["nodes"])
        if not res["pageInfo"]["hasNextPage"]:
            break
        cursor = res["pageInfo"]["endCursor"]

    total_stars = sum(r["stargazerCount"] for r in all_public_repos)
    total_forks = sum(r["forkCount"] for r in all_public_repos)

    lang_bytes: dict[str, int] = {}
    lang_repo_counts: dict[str, int] = {}
    for r in all_public_repos:
        for edge in r["languages"]["edges"]:
            lname = edge["node"]["name"]
            lang_bytes[lname] = lang_bytes.get(lname, 0) + edge["size"]
            lang_repo_counts[lname] = lang_repo_counts.get(lname, 0) + 1

    total_code_bytes = sum(lang_bytes.values()) or 1
    sorted_langs = sorted(lang_bytes.items(), key=lambda kv: -kv[1])
    top_langs: list[dict[str, Any]] = []
    other_bytes = 0
    other_repos = 0
    for idx_l, (lname, sz) in enumerate(sorted_langs):
        if idx_l < 5:
            top_langs.append(
                {
                    "name": lname,
                    "bytes": sz,
                    "pct": (sz / total_code_bytes) * 100.0,
                    "repos": lang_repo_counts[lname],
                }
            )
        else:
            other_bytes += sz
            other_repos += lang_repo_counts[lname]
    if other_bytes > 0:
        top_langs.append(
            {
                "name": "Other",
                "bytes": other_bytes,
                "pct": (other_bytes / total_code_bytes) * 100.0,
                "repos": len(sorted_langs) - 5,
            }
        )

    # 4. Recent authored commit timestamps (for EAT time-of-day rhythm + latest commit messages on recently tended repos)
    recent_commits_query = """
    query($login: String!, $authorId: ID!) {
      user(login: $login) {
        repositories(
          first: 15,
          ownerAffiliations: OWNER,
          isFork: false,
          privacy: PUBLIC,
          orderBy: {field: PUSHED_AT, direction: DESC}
        ) {
          nodes {
            name
            description
            url
            homepageUrl
            pushedAt
            stargazerCount
            primaryLanguage { name }
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 15, author: {id: $authorId}) {
                    nodes {
                      committedDate
                      messageHeadline
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    recent_nodes = graphql(token, recent_commits_query, {"login": USERNAME, "authorId": user_id})["user"]["repositories"]["nodes"]

    eat_buckets = {"Morning": 0, "Afternoon": 0, "Evening": 0, "Night": 0}
    recently_tended: list[dict[str, Any]] = []
    for r in recent_nodes:
        history = []
        if r.get("defaultBranchRef") and r["defaultBranchRef"].get("target"):
            history = r["defaultBranchRef"]["target"].get("history", {}).get("nodes", [])
        for c in history:
            dt_eat = datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00")).astimezone(EAT_TZ)
            hr = dt_eat.hour
            if 6 <= hr < 12:
                eat_buckets["Morning"] += 1
            elif 12 <= hr < 18:
                eat_buckets["Afternoon"] += 1
            elif 18 <= hr < 24:
                eat_buckets["Evening"] += 1
            else:
                eat_buckets["Night"] += 1

        if r["name"].lower() != USERNAME.lower() and len(recently_tended) < 5:
            latest_msg = history[0]["messageHeadline"] if history else ""
            # Clean noisy merge or generic commit prefixes lightly
            latest_msg = re.sub(r"^(feat|fix|chore|refactor|docs|style|perf)(\([^)]+\))?:\s*", "", latest_msg, flags=re.I)
            recently_tended.append(
                {
                    "name": r["name"],
                    "url": r["url"],
                    "homepage": r.get("homepageUrl") or "",
                    "description": r.get("description") or "",
                    "language": (r.get("primaryLanguage") or {}).get("name", "TypeScript"),
                    "pushedAt": r["pushedAt"],
                    "relative": fmt_relative(r["pushedAt"], now_utc),
                    "latest_commit": truncate(latest_msg, 64),
                }
            )

    repo_lookup = {r["name"]: r for r in all_public_repos}

    return {
        "now_utc": now_utc,
        "now_eat": now_eat,
        "name": user["name"] or "Elvin Omondi Juma",
        "login": user["login"],
        "location": user["location"] or "Eldoret, Kenya",
        "company": user["company"] or "Great Thumbs Software Solutions",
        "created_year": start_year,
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "public_repos": public_repo_count,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "total_code_bytes": total_code_bytes,
        "all_time_contributions": all_time_contributions,
        "all_time_commits": all_time_commits,
        "all_time_prs": all_time_prs,
        "all_time_issues_reviews": all_time_issues + all_time_reviews,
        "all_time_restricted": all_time_restricted,
        "rolling_365": rolling_365,
        "rolling_30": rolling_30,
        "rolling_7": rolling_7,
        "active_days": active_days,
        "total_cal_days": total_cal_days,
        "active_pct": active_pct,
        "active_avg": active_avg,
        "best_day_count": best_day["contributionCount"],
        "best_day_date": fmt_short_date(best_day["date"]),
        "current_streak": current_streak,
        "current_range": f"{fmt_short_date(current_start)} – {fmt_short_date(current_end)}" if current_streak else "Resting today",
        "longest_streak": longest_streak,
        "longest_range": f"{fmt_short_date(longest_range[0])} – {fmt_short_date(longest_range[1])}" if longest_streak else "—",
        "yearly_totals": yearly_totals,
        "dow_mon_sun": dow_mon_sun,
        "top_langs": top_langs,
        "eat_buckets": eat_buckets,
        "weekly_series": weekly_series,
        "last_30_days": last_30,
        "mosaic_weeks": mosaic_weeks,
        "recently_tended": recently_tended,
        "repo_lookup": repo_lookup,
    }


def smooth_ridge_path(points: list[tuple[float, float]], baseline_y: float) -> tuple[str, str]:
    """Build a smooth cubic Bezier stroke path and closed filled area path."""
    if not points:
        return "", ""
    if len(points) == 1:
        x, y = points[0]
        return f"M {x:.1f} {y:.1f}", f"M {x:.1f} {baseline_y:.1f} L {x:.1f} {y:.1f} L {x:.1f} {baseline_y:.1f} Z"

    stroke_parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[max(0, i - 1)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(len(points) - 1, i + 2)]
        # Catmull-Rom to cubic Bezier with gentle tension for calm organic slopes
        t = 0.18
        cp1x = p1[0] + (p2[0] - p0[0]) * t
        cp1y = p1[1] + (p2[1] - p0[1]) * t
        cp2x = p2[0] - (p3[0] - p1[0]) * t
        cp2y = p2[1] - (p3[1] - p1[1]) * t
        # Clamp control points so valleys never dip below shoreline
        cp1y = min(baseline_y - 1.5, cp1y)
        cp2y = min(baseline_y - 1.5, cp2y)
        stroke_parts.append(f"C {cp1x:.1f} {cp1y:.1f}, {cp2x:.1f} {cp2y:.1f}, {p2[0]:.1f} {p2[1]:.1f}")

    stroke_d = " ".join(stroke_parts)
    area_d = f"{stroke_d} L {points[-1][0]:.1f} {baseline_y:.1f} L {points[0][0]:.1f} {baseline_y:.1f} Z"
    return stroke_d, area_d


def render_hero_svg(stats: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 920, 212
    streak_txt = f"{stats['current_streak']}-day streak" if stats["current_streak"] > 0 else "Quiet day"
    pill_text = f"Eldoret, Kenya  ·  {streak_txt}  ·  {fmt_num(stats['rolling_365'])} contributions this year"
    pill_w = min(460, max(280, int(len(pill_text) * 5.65) + 40))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Elvin Omondi Juma — Founding Engineer at Great Thumbs Software Solutions">
<defs>
  <clipPath id="heroClip"><rect width="{w}" height="{h}" rx="16"/></clipPath>
  <linearGradient id="heroBg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{t['surface']}"/>
    <stop offset="65%" stop-color="{t['canvas']}"/>
    <stop offset="100%" stop-color="{t['canvas_alt']}"/>
  </linearGradient>
  <radialGradient id="heroGlow" cx="0.85" cy="0.28" r="0.34">
    <stop offset="0%" stop-color="{t['orb_glow']}" stop-opacity="0.28"/>
    <stop offset="55%" stop-color="{t['pine']}" stop-opacity="0.06"/>
    <stop offset="100%" stop-color="{t['canvas']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="heroOrbGrad" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{t['orb']}" stop-opacity="0.62"/>
    <stop offset="72%" stop-color="{t['orb']}" stop-opacity="0.30"/>
    <stop offset="100%" stop-color="{t['orb']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="hillFar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['ridge_far']}" stop-opacity="0.26"/>
    <stop offset="100%" stop-color="{t['ridge_far']}" stop-opacity="0.04"/>
  </linearGradient>
  <linearGradient id="hillNear" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['pine']}" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="{t['pine']}" stop-opacity="0.03"/>
  </linearGradient>
</defs>

<g clip-path="url(#heroClip)">
  <rect width="{w}" height="{h}" fill="url(#heroBg)"/>
  <rect width="{w}" height="{h}" fill="url(#heroGlow)"/>

  <!-- Subtle distant highland mist silhouettes on the right -->
  <circle cx="792" cy="58" r="24" fill="url(#heroOrbGrad)"/>
  <path d="M 470 212 C 545 148, 610 132, 682 154 C 742 172, 804 102, 872 126 C 894 134, 910 144, 926 150 L 926 212 Z" fill="url(#hillFar)"/>
  <path d="M 555 212 C 625 162, 695 168, 764 146 C 824 128, 876 156, 926 142 L 926 212 Z" fill="url(#hillNear)"/>
  <path d="M 555 212 C 625 162, 695 168, 764 146 C 824 128, 876 156, 926 142" fill="none" stroke="{t['pine']}" stroke-opacity="0.22" stroke-width="1"/>

  <!-- Live status pill -->
  <g transform="translate(42, 30)">
    <rect width="{pill_w}" height="26" rx="13" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="1"/>
    <circle cx="15" cy="13" r="3.6" fill="{t['pine']}">
      <animate attributeName="opacity" values="0.95;0.38;0.95" dur="5.5s" repeatCount="indefinite"/>
    </circle>
    <text x="27" y="17" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.5" font-weight="500">{esc(pill_text)}</text>
  </g>

  <!-- Identity -->
  <text x="42" y="102" fill="{t['ink']}" font-family="{SERIF}" font-size="33" font-weight="400" letter-spacing="-0.4">{esc(stats['name'])}</text>
  <text x="42" y="129" fill="{t['ink_sec']}" font-family="{SANS}" font-size="14" font-weight="500">Founding Engineer at Great Thumbs Software Solutions</text>
  <text x="42" y="155" fill="{t['ink_muted']}" font-family="{SERIF}" font-style="italic" font-size="13">Building calm, dependable software for healthcare, local commerce, and everyday operations.</text>

  <!-- Subtle bottom bar -->
  <line x1="42" y1="176" x2="540" y2="176" stroke="{t['divider']}" stroke-width="1"/>
  <text x="42" y="195" fill="{t['ink_muted']}" font-family="{SANS}" font-size="11.2">
    <tspan fill="{t['ink_sec']}" font-weight="600">@{esc(stats['login'])}</tspan>
    <tspan>  ·  {fmt_num(stats['public_repos'])} public repositories  ·  {fmt_num(stats['all_time_contributions'])} lifetime contributions</tspan>
  </text>
</g>

<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="15.5" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
'''


def render_stats_overview_svg(stats: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 920, 344

    # Compute YoY growth or 30-day subtitle
    y_totals = stats["yearly_totals"]
    sub_all_time = f"Across {y_totals[0][0]} – {y_totals[-1][0]}" if len(y_totals) > 1 else f"Since {stats['created_year']}"
    sub_365 = f"{fmt_num(stats['rolling_30'])} in the last 30 days"

    # Left metric ledger rows (2 columns x 4 rows)
    left_rows = [
        ("Commits (all-time)", fmt_num(stats["all_time_commits"]), "Pull requests", fmt_num(stats["all_time_prs"])),
        ("Private activity", fmt_num(stats["all_time_restricted"]), "Issues &amp; reviews", fmt_num(stats["all_time_issues_reviews"])),
        ("Public repositories", fmt_num(stats["public_repos"]), "Stars · Forks", f"{fmt_num(stats['total_stars'])} · {fmt_num(stats['total_forks'])}"),
        ("Followers · Following", f"{fmt_num(stats['followers'])} · {fmt_num(stats['following'])}", "Code indexed", fmt_bytes(stats["total_code_bytes"])),
    ]

    ledger_svg = []
    for i, (l_k, l_v, r_k, r_v) in enumerate(left_rows):
        ry = 182 + i * 36
        if i > 0:
            ledger_svg.append(f'<line x1="36" y1="{ry - 22}" x2="444" y2="{ry - 22}" stroke="{t["divider"]}" stroke-width="1"/>')
        ledger_svg.append(
            f'<text x="36" y="{ry}" fill="{t["ink_sec"]}" font-family="{SANS}" font-size="11.8">{l_k}</text>'
            f'<text x="228" y="{ry}" text-anchor="end" fill="{t["ink"]}" font-family="{SANS}" font-size="12.8" font-weight="600">{l_v}</text>'
            f'<text x="252" y="{ry}" fill="{t["ink_sec"]}" font-family="{SANS}" font-size="11.8">{r_k}</text>'
            f'<text x="444" y="{ry}" text-anchor="end" fill="{t["ink"]}" font-family="{SANS}" font-size="12.8" font-weight="600">{r_v}</text>'
        )

    # Yearly trajectory horizontal bars (show up to last 4 years cleanly)
    recent_years = y_totals[-4:]
    max_y_val = max((v for _, v in recent_years), default=1) or 1
    bar_max_w = 286.0
    years_svg = []
    start_y_bar = 250
    step_y = 24 if len(recent_years) <= 3 else 20
    for idx_y, (yr, val) in enumerate(recent_years):
        by = start_y_bar + idx_y * step_y
        bw = max(6.0, (val / max_y_val) * bar_max_w)
        is_latest = idx_y == len(recent_years) - 1
        bar_col = t["pine"] if is_latest else t["moss"]
        bar_op = "0.95" if is_latest else "0.62"
        years_svg.append(
            f'<text x="494" y="{by + 9}" fill="{t["ink_sec"]}" font-family="{MONO}" font-size="11">{yr}</text>'
            f'<rect x="536" y="{by}" width="{bar_max_w:.0f}" height="10" rx="5" fill="{t["subtle"]}"/>'
            f'<rect x="536" y="{by}" width="{bw:.1f}" height="10" rx="5" fill="{bar_col}" fill-opacity="{bar_op}"/>'
            f'<text x="884" y="{by + 9}" text-anchor="end" fill="{t["ink"] if is_latest else t["ink_sec"]}" font-family="{SANS}" font-size="11.8" font-weight="{600 if is_latest else 500}">{fmt_num(val)}</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="GitHub Overview Statistics — Automatically Updated">
<rect width="{w}" height="{h}" rx="16" fill="{t['surface']}" stroke="{t['border']}" stroke-width="1"/>

<!-- Header -->
<text x="36" y="37" fill="{t['ink']}" font-family="{SERIF}" font-size="17" font-weight="400">GitHub Overview</text>
<text x="884" y="36" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="11">All-time &amp; rolling 365 days  ·  tracked automatically</text>
<line x1="36" y1="52" x2="884" y2="52" stroke="{t['divider']}" stroke-width="1"/>

<!-- Center divider -->
<line x1="468" y1="68" x2="468" y2="322" stroke="{t['divider']}" stroke-width="1"/>

<!-- LEFT: Spotlight totals -->
<g>
  <rect x="36" y="68" width="196" height="78" rx="10" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <text x="52" y="90" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.2">All-time contributions</text>
  <text x="52" y="121" fill="{t['pine']}" font-family="{SANS}" font-size="25" font-weight="700" letter-spacing="-0.5">{fmt_num(stats['all_time_contributions'])}</text>
  <text x="52" y="137" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">{esc(sub_all_time)}</text>

  <rect x="248" y="68" width="196" height="78" rx="10" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <text x="264" y="90" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.2">Past 365 days</text>
  <text x="264" y="121" fill="{t['lake']}" font-family="{SANS}" font-size="25" font-weight="700" letter-spacing="-0.5">{fmt_num(stats['rolling_365'])}</text>
  <text x="264" y="137" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">{esc(sub_365)}</text>
</g>

<!-- LEFT: Detailed Ledger -->
<g>
  {"".join(ledger_svg)}
</g>

<!-- RIGHT: Streaks -->
<g>
  <rect x="494" y="68" width="188" height="78" rx="10" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <text x="510" y="90" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.2">Current streak</text>
  <text x="510" y="121" fill="{t['ochre']}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-0.4">{stats['current_streak']} days</text>
  <text x="510" y="137" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">{esc(stats['current_range'])}</text>

  <rect x="696" y="68" width="188" height="78" rx="10" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <text x="712" y="90" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.2">Longest streak</text>
  <text x="712" y="121" fill="{t['pine']}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-0.4">{stats['longest_streak']} days</text>
  <text x="712" y="137" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">{esc(stats['longest_range'])}</text>
</g>

<!-- RIGHT: Consistency micro-summary -->
<g>
  <text x="494" y="174" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.8">Active days (1y)</text>
  <text x="494" y="194" fill="{t['ink']}" font-family="{SANS}" font-size="14" font-weight="600">{stats['active_days']} <tspan fill="{t['ink_muted']}" font-size="11.5" font-weight="400">({stats['active_pct']:.0f}%)</tspan></text>

  <text x="636" y="174" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.8">Best single day</text>
  <text x="636" y="194" fill="{t['ink']}" font-family="{SANS}" font-size="14" font-weight="600">{fmt_num(stats['best_day_count'])} <tspan fill="{t['ink_muted']}" font-size="11.5" font-weight="400">· {esc(stats['best_day_date'])}</tspan></text>

  <text x="784" y="174" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.8">Active-day avg</text>
  <text x="784" y="194" fill="{t['ink']}" font-family="{SANS}" font-size="14" font-weight="600">{stats['active_avg']:.1f} <tspan fill="{t['ink_muted']}" font-size="11.5" font-weight="400">/ day</tspan></text>
</g>

<line x1="494" y1="212" x2="884" y2="212" stroke="{t['divider']}" stroke-width="1"/>

<!-- RIGHT: Yearly trajectory -->
<text x="494" y="234" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.8" font-weight="600">Yearly contribution growth</text>
<g>
  {"".join(years_svg)}
</g>
</svg>
'''


def render_stats_rhythm_svg(stats: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 920, 304

    # LEFT: Language segmented bar & 2-col breakdown
    langs = stats["top_langs"]
    bar_x, bar_y, bar_w, bar_h = 36, 68, 396, 10
    segs = []
    cur_x = float(bar_x)
    for idx_l, l in enumerate(langs):
        col = t["lang_colors"].get(l["name"], t["lang_colors"]["Other"])
        sw = max(3.0, (l["pct"] / 100.0) * bar_w)
        if idx_l == len(langs) - 1:
            sw = max(2.0, (bar_x + bar_w) - cur_x)
        segs.append(f'<rect x="{cur_x:.1f}" y="{bar_y}" width="{sw:.1f}" height="{bar_h}" fill="{col}"/>')
        cur_x += sw

    lang_items = []
    for idx_l, l in enumerate(langs[:6]):
        col = t["lang_colors"].get(l["name"], t["lang_colors"]["Other"])
        c_idx = idx_l % 2
        r_idx = idx_l // 2
        lx = 36 + c_idx * 204
        ly = 112 + r_idx * 52
        sub_txt = f"{l['repos']} langs · {fmt_bytes(l['bytes'])}" if l["name"] == "Other" else f"{l['repos']} repos · {fmt_bytes(l['bytes'])}"
        lang_items.append(
            f'<circle cx="{lx + 5}" cy="{ly - 4}" r="4.5" fill="{col}"/>'
            f'<text x="{lx + 17}" y="{ly}" fill="{t["ink"]}" font-family="{SANS}" font-size="12.5" font-weight="600">{esc(l["name"])}</text>'
            f'<text x="{lx + 188}" y="{ly}" text-anchor="end" fill="{t["ink"]}" font-family="{SANS}" font-size="12.2" font-weight="600">{l["pct"]:.1f}%</text>'
            f'<text x="{lx + 17}" y="{ly + 16}" fill="{t["ink_muted"]}" font-family="{SANS}" font-size="10.5">{esc(sub_txt)}</text>'
        )

    # RIGHT: Weekly Cadence (Mon..Sun)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    full_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = stats["dow_mon_sun"]
    max_dow = max(dow) if dow and max(dow) > 0 else 1
    peak_i = dow.index(max(dow))

    dow_bars = []
    chart_base_y = 166
    max_bar_h = 74.0
    for i, (d_lbl, val) in enumerate(zip(day_names, dow)):
        bx = 498 + i * 56
        bh = max(8.0, (val / max_dow) * max_bar_h)
        by = chart_base_y - bh
        is_peak = i == peak_i
        fill_col = t["pine"] if is_peak else t["lake"]
        fill_op = "0.95" if is_peak else f"{0.35 + 0.45 * (val / max_dow):.2f}"
        dow_bars.append(
            f'<rect x="{bx}" y="{by:.1f}" width="32" height="{bh:.1f}" rx="6" fill="{fill_col}" fill-opacity="{fill_op}"/>'
            f'<text x="{bx + 16}" y="{by - 7:.1f}" text-anchor="middle" fill="{t["ink"] if is_peak else t["ink_muted"]}" font-family="{SANS}" font-size="10.2" font-weight="{600 if is_peak else 500}">{val}</text>'
            f'<text x="{bx + 16}" y="{chart_base_y + 18}" text-anchor="middle" fill="{t["ink"] if is_peak else t["ink_sec"]}" font-family="{SANS}" font-size="11" font-weight="{600 if is_peak else 400}">{d_lbl}</text>'
        )
    dow_bars.append(f'<line x1="492" y1="{chart_base_y + 0.5:.1f}" x2="884" y2="{chart_base_y + 0.5:.1f}" stroke="{t["divider"]}" stroke-width="1"/>')

    # RIGHT BOTTOM: Time-of-day coding rhythm (EAT UTC+3)
    buckets = stats["eat_buckets"]
    b_tot = sum(buckets.values()) or 1
    ordered_b = [
        ("Morning", "06–12", buckets["Morning"], t["ochre"]),
        ("Afternoon", "12–18", buckets["Afternoon"], t["pine"]),
        ("Evening", "18–00", buckets["Evening"], t["lake"]),
        ("Night", "00–06", buckets["Night"], t["moss"]),
    ]
    top_bucket = max(ordered_b, key=lambda x: x[2])[0]
    tod_svg = []
    for i, (b_name, b_hrs, b_cnt, b_col) in enumerate(ordered_b):
        px = 492 + i * 100
        pct = (b_cnt / b_tot) * 100.0
        fill_w = max(4.0, (pct / 100.0) * 72.0)
        tod_svg.append(
            f'<rect x="{px}" y="230" width="92" height="52" rx="8" fill="{t["subtle"]}" stroke="{t["border"]}" stroke-width="0.7"/>'
            f'<text x="{px + 10}" y="247" fill="{t["ink_sec"]}" font-family="{SANS}" font-size="10.5">{b_name}</text>'
            f'<text x="{px + 10}" y="266" fill="{b_col}" font-family="{SANS}" font-size="13.8" font-weight="700">{pct:.0f}%</text>'
            f'<text x="{px + 82}" y="265" text-anchor="end" fill="{t["ink_muted"]}" font-family="{MONO}" font-size="9">{b_hrs}</text>'
            f'<rect x="{px + 10}" y="273" width="72" height="3" rx="1.5" fill="{t["divider"]}"/>'
            f'<rect x="{px + 10}" y="273" width="{fill_w:.1f}" height="3" rx="1.5" fill="{b_col}" fill-opacity="0.85"/>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Languages and Coding Rhythm">
<defs>
  <clipPath id="langBarClip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5"/></clipPath>
</defs>

<rect width="{w}" height="{h}" rx="16" fill="{t['surface']}" stroke="{t['border']}" stroke-width="1"/>
<line x1="460" y1="24" x2="460" y2="280" stroke="{t['divider']}" stroke-width="1"/>

<!-- LEFT PANEL: Languages -->
<text x="36" y="38" fill="{t['ink']}" font-family="{SERIF}" font-size="16.5" font-weight="400">Languages</text>
<text x="432" y="37" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.8">{fmt_num(stats['public_repos'])} public repos · {fmt_bytes(stats['total_code_bytes'])}</text>
<line x1="36" y1="50" x2="432" y2="50" stroke="{t['divider']}" stroke-width="1"/>

<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{t['subtle']}"/>
<g clip-path="url(#langBarClip)">
  {"".join(segs)}
</g>

<g>
  {"".join(lang_items)}
</g>

<text x="36" y="278" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.2">Weighted by bytes across all owned non-fork public repositories.</text>

<!-- RIGHT PANEL: Weekly Cadence & EAT Rhythm -->
<text x="492" y="38" fill="{t['ink']}" font-family="{SERIF}" font-size="16.5" font-weight="400">Weekly Cadence</text>
<text x="884" y="37" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.8">Peak: {full_names[peak_i]} ({fmt_num(dow[peak_i])})</text>
<line x1="492" y1="50" x2="884" y2="50" stroke="{t['divider']}" stroke-width="1"/>

<g>
  {"".join(dow_bars)}
</g>

<line x1="492" y1="198" x2="884" y2="198" stroke="{t['divider']}" stroke-width="1"/>
<text x="492" y="220" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.5" font-weight="600">Time-of-day rhythm (EAT · UTC+3)</text>
<text x="884" y="220" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">Most active: {top_bucket}</text>

<g>
  {"".join(tod_svg)}
</g>
</svg>
'''


def render_activity_horizon_svg(stats: dict[str, Any], theme_name: str) -> str:
    """
    Signature bottom piece: "The Quiet Horizon"
    Transforms Elvin's real 52-week contribution curve + 30-day daily shipping pulse
    + 26-week calm heatmap mosaic into a serene highland mountain & still-lake reflection.
    """
    t = THEMES[theme_name]
    w, h = 920, 358
    shore_y = 228.0
    left_x, right_x = -2.0, 922.0

    # 1. Far mountain ridge: 52-week contribution volume (edge-to-edge)
    weekly = stats["weekly_series"]
    w_vals = [x["total"] for x in weekly]
    max_w = max(w_vals) if w_vals and max(w_vals) > 0 else 1
    peak_w_idx = w_vals.index(max(w_vals)) if w_vals else 0
    peak_w_val = w_vals[peak_w_idx] if w_vals else 0

    far_pts: list[tuple[float, float]] = []
    n_w = max(2, len(weekly))
    for i, item in enumerate(weekly):
        px = left_x + (i / (n_w - 1)) * (right_x - left_x)
        # Gentle sqrt scaling so peaks look architectural & quiet valleys remain legible
        norm = math.sqrt(item["total"] / max_w)
        py = shore_y - 14.0 - norm * 96.0
        far_pts.append((px, py))

    far_stroke, far_area = smooth_ridge_path(far_pts, shore_y)

    # 2. Near pine ridge: last 30 days daily activity (edge-to-edge)
    last_30 = stats["last_30_days"]
    d_vals = [d["contributionCount"] for d in last_30]
    max_d = max(d_vals) if d_vals and max(d_vals) > 0 else 1
    near_pts: list[tuple[float, float]] = []
    n_d = max(2, len(last_30))
    for i, d in enumerate(last_30):
        px = left_x + (i / (n_d - 1)) * (right_x - left_x)
        norm = math.sqrt(d["contributionCount"] / max_d)
        py = shore_y - 6.0 - norm * 54.0
        near_pts.append((px, py))

    near_stroke, near_area = smooth_ridge_path(near_pts, shore_y)

    # Peak week callout
    pk_x, pk_y = far_pts[peak_w_idx] if far_pts else (460.0, 140.0)
    pk_anchor = "middle"
    pk_tx = pk_x
    if pk_x < 130:
        pk_anchor = "start"
        pk_tx = max(36.0, pk_x)
    elif pk_x > 790:
        pk_anchor = "end"
        pk_tx = min(884.0, pk_x)
    pk_month = datetime.strptime(weekly[peak_w_idx]["firstDay"], "%Y-%m-%d").strftime("%b %Y") if weekly else ""

    # 3. Evenly paced month labels aligned to the 52-week horizontal axis (no skipped months!)
    month_positions: list[tuple[str, float]] = []
    seen_months: dict[tuple[int, int], list[float]] = {}
    for i, item in enumerate(weekly):
        dt = datetime.strptime(item["firstDay"], "%Y-%m-%d")
        key = (dt.year, dt.month)
        mx = 24.0 + (i / (n_w - 1)) * (896.0 - 24.0)
        seen_months.setdefault(key, []).append(mx)
    for (yr, mo), xs in sorted(seen_months.items()):
        # Skip tiny leading stub month (< 2 weeks) so Dec..Nov renders cleanly without gaps
        if len(xs) < 2 and xs[0] < 60:
            continue
        mid_x = sum(xs) / len(xs)
        month_positions.append((datetime(yr, mo, 1).strftime("%b"), mid_x))

    month_labels_svg = [
        f'<text x="{mx:.1f}" y="317" text-anchor="middle" fill="{t["ink_muted"]}" font-family="{SANS}" font-size="10.2">{lbl}</text>'
        for lbl, mx in month_positions
    ]

    # 4. Quiet 26-week mini contribution mosaic in the top-right corner
    mosaic_svg = []
    m_weeks = stats["mosaic_weeks"]
    m_all = [d["contributionCount"] for wk in m_weeks for d in wk["contributionDays"] if d["contributionCount"] > 0]
    m_max = max(m_all) if m_all else 1
    cell = 5.2
    gap = 2.0
    m_start_x = 884.0 - len(m_weeks) * (cell + gap) + gap
    m_start_y = 22.0
    for wi, wk in enumerate(m_weeks):
        for d in wk["contributionDays"]:
            di = d["weekday"]
            cnt = d["contributionCount"]
            if cnt == 0:
                lvl = 0
            else:
                ratio = cnt / m_max
                lvl = 1 if ratio < 0.22 else (2 if ratio < 0.48 else (3 if ratio < 0.75 else 4))
            cx = m_start_x + wi * (cell + gap)
            cy = m_start_y + di * (cell + gap)
            mosaic_svg.append(f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="1.3" fill="{t["ramp"][lvl]}"/>')

    # 5. Subtle calm lake ripples
    ripples = [
        (85, 242, 145, 0.22, "11s"),
        (310, 248, 180, 0.18, "14s"),
        (595, 244, 165, 0.20, "12s"),
        (170, 262, 120, 0.14, "16s"),
        (455, 268, 210, 0.16, "13s"),
        (710, 264, 130, 0.13, "15s"),
        (250, 284, 150, 0.10, "17s"),
        (540, 288, 140, 0.10, "14s"),
    ]
    ripples_svg = []
    for rx, ry, rw, op, dur in ripples:
        ripples_svg.append(
            f'<line x1="{rx}" y1="{ry}" x2="{rx + rw}" y2="{ry}" stroke="{t["ripple"]}" stroke-width="1" stroke-linecap="round" stroke-opacity="{op}">'
            f'<animate attributeName="stroke-opacity" values="{op};{op * 0.35:.2f};{op}" dur="{dur}" repeatCount="indefinite"/>'
            f'</line>'
        )

    # Reflection scale factor anchored at shore_y
    ref_ty = shore_y * (1.0 + 0.56)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="The Quiet Horizon — 52-Week and 30-Day GitHub Activity Landscape">
<defs>
  <clipPath id="horizonClip"><rect width="{w}" height="{h}" rx="16"/></clipPath>
  <clipPath id="skyClip"><rect x="0" y="0" width="{w}" height="{shore_y}"/></clipPath>
  <clipPath id="waterClip"><rect x="0" y="{shore_y}" width="{w}" height="{h - shore_y}"/></clipPath>

  <linearGradient id="skyGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['sky_top']}"/>
    <stop offset="55%" stop-color="{t['sky_mid']}"/>
    <stop offset="100%" stop-color="{t['sky_bot']}"/>
  </linearGradient>

  <linearGradient id="waterGrad" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['water_top']}"/>
    <stop offset="100%" stop-color="{t['water_bot']}"/>
  </linearGradient>

  <radialGradient id="orbAura" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{t['orb']}" stop-opacity="0.58"/>
    <stop offset="40%" stop-color="{t['orb_glow']}" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="{t['orb_glow']}" stop-opacity="0"/>
  </radialGradient>

  <radialGradient id="orbSoft" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{t['orb']}" stop-opacity="0.72"/>
    <stop offset="78%" stop-color="{t['orb']}" stop-opacity="0.38"/>
    <stop offset="100%" stop-color="{t['orb']}" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="farRidgeFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['ridge_far']}" stop-opacity="0.52"/>
    <stop offset="100%" stop-color="{t['ridge_far']}" stop-opacity="0.14"/>
  </linearGradient>

  <linearGradient id="nearRidgeFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['ridge_near']}" stop-opacity="0.82"/>
    <stop offset="100%" stop-color="{t['ridge_near']}" stop-opacity="0.34"/>
  </linearGradient>

  <linearGradient id="waterFade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#ffffff" stop-opacity="0.46"/>
    <stop offset="70%" stop-color="#ffffff" stop-opacity="0.12"/>
    <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
  </linearGradient>
  <mask id="reflectMask">
    <rect x="0" y="{shore_y}" width="{w}" height="96" fill="url(#waterFade)"/>
  </mask>
</defs>

<g clip-path="url(#horizonClip)">
  <!-- Sky & Water Backdrop -->
  <rect x="0" y="0" width="{w}" height="{shore_y}" fill="url(#skyGrad)"/>
  <rect x="0" y="{shore_y}" width="{w}" height="{h - shore_y}" fill="url(#waterGrad)"/>

  <!-- Soft sun / moon orb resting above the highland mist -->
  <circle cx="118" cy="118" r="56" fill="url(#orbAura)"/>
  <circle cx="118" cy="118" r="17" fill="url(#orbSoft)"/>

  <!-- Header & 26-week calm heatmap mosaic -->
  <text x="36" y="38" fill="{t['ink']}" font-family="{SERIF}" font-size="17" font-weight="400">The Quiet Horizon</text>
  <text x="36" y="57" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.2">52-week contribution topography · {fmt_num(stats['rolling_30'])} contributions in 30 days · {fmt_num(stats['rolling_7'])} in 7 days</text>
  <g>{"".join(mosaic_svg)}</g>
  <text x="884" y="84" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="9.5">Last 26 weeks</text>

  <!-- Data-driven mountain ridges -->
  <g clip-path="url(#skyClip)">
    <!-- Far ridge: 52-week momentum -->
    <path d="{far_area}" fill="url(#farRidgeFill)"/>
    <path d="{far_stroke}" fill="none" stroke="{t['ridge_far_stroke']}" stroke-opacity="0.65" stroke-width="1.3"/>

    <!-- Near ridge: 30-day daily pulse -->
    <path d="{near_area}" fill="url(#nearRidgeFill)"/>
    <path d="{near_stroke}" fill="none" stroke="{t['ridge_near_stroke']}" stroke-opacity="0.75" stroke-width="1.4"/>

    <!-- Quiet peak marker -->
    <line x1="{pk_x:.1f}" y1="{pk_y:.1f}" x2="{pk_x:.1f}" y2="{pk_y - 12:.1f}" stroke="{t['ridge_far_stroke']}" stroke-opacity="0.55" stroke-width="1"/>
    <circle cx="{pk_x:.1f}" cy="{pk_y:.1f}" r="3" fill="{t['surface']}" stroke="{t['ridge_far_stroke']}" stroke-width="1.5"/>
    <text x="{pk_tx:.1f}" y="{pk_y - 16:.1f}" text-anchor="{pk_anchor}" fill="{t['ink_sec']}" font-family="{SANS}" font-size="10.2" font-weight="500">Peak week · {fmt_num(peak_w_val)} ({esc(pk_month)})</text>
  </g>

  <!-- Still lake reflection of both ridges -->
  <g clip-path="url(#waterClip)" mask="url(#reflectMask)">
    <g transform="translate(0, {ref_ty:.2f}) scale(1, -0.56)">
      <path d="{far_area}" fill="{t['ridge_far']}" fill-opacity="0.55"/>
      <path d="{near_area}" fill="{t['ridge_near']}" fill-opacity="0.72"/>
    </g>
  </g>

  <!-- Calm waterline & subtle breathing ripples -->
  <line x1="0" y1="{shore_y}" x2="{w}" y2="{shore_y}" stroke="{t['ripple']}" stroke-opacity="0.35" stroke-width="1"/>
  <g>{"".join(ripples_svg)}</g>

  <!-- Month axis & gentle footer legend -->
  <line x1="36" y1="300" x2="884" y2="300" stroke="{t['divider']}" stroke-opacity="0.65" stroke-width="1"/>
  <g>{"".join(month_labels_svg)}</g>

  <text x="36" y="341" fill="{t['ink_muted']}" font-family="{SANS}" font-size="9.8">Every elevation is shaped directly by live GitHub contribution data.</text>
  <g transform="translate(664, 341)" font-family="{SANS}" font-size="9.8" fill="{t['ink_muted']}">
    <circle cx="0" cy="-3" r="3.5" fill="{t['ridge_far']}" fill-opacity="0.75"/>
    <text x="8" y="0">52-week trend</text>
    <circle cx="102" cy="-3" r="3.5" fill="{t['ridge_near']}" fill-opacity="0.88"/>
    <text x="110" y="0">30-day daily pulse</text>
  </g>
</g>

<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="15.5" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
'''


def build_recent_activity_md(stats: dict[str, Any]) -> str:
    rows = [
        "| Repository | Focus & Latest Update | Language | Tended |",
        "| :--- | :--- | :--- | ---: |",
    ]
    for r in stats["recently_tended"]:
        name_link = f"[**{r['name']}**]({r['url']})"
        if r["homepage"]:
            name_link += f" · [Live]({r['homepage']})"
        cleaned_desc = clean_repo_description(r["name"], r["description"])
        desc = truncate(cleaned_desc, 92) if cleaned_desc else r["latest_commit"]
        if cleaned_desc and r["latest_commit"]:
            detail = f"{desc}<br><sub>Latest commit: {r['latest_commit']}</sub>"
        else:
            detail = desc or "Active development"
        # Escape pipes for markdown table safety
        detail = detail.replace("|", "\\|")
        rows.append(f"| {name_link} | {detail} | `{r['language']}` | {r['relative']} |")
    return "\n".join(rows)


def replace_marker(content: str, tag: str, replacement: str) -> str:
    pattern = re.compile(rf"(<!-- {tag}:START -->).*?(<!-- {tag}:END -->)", re.DOTALL)
    if not pattern.search(content):
        return content
    return pattern.sub(rf"\1\n{replacement}\n\2", content)


def update_readme(stats: dict[str, Any]) -> None:
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")

    # Update live star badges on public flagship repos if markers exist
    lookup = stats["repo_lookup"]
    for repo_name in ("pharmacy_template_tier2", "hotel-intranet", "Kampus", "moi_mashinani"):
        if repo_name in lookup:
            stars = lookup[repo_name]["stargazerCount"]
            star_str = f" · ★ {stars}" if stars > 0 else ""
            text = re.sub(
                rf"(<!-- STAR:{re.escape(repo_name)} -->).*?(<!-- /STAR:{re.escape(repo_name)} -->)",
                rf"\1{star_str}\2",
                text,
            )

    text = replace_marker(text, "RECENT_ACTIVITY", build_recent_activity_md(stats))

    updated_date = stats["now_eat"].strftime("%B %-d, %Y") if os.name != "nt" else stats["now_eat"].strftime("%B %d, %Y")
    footer_line = (
        f"<sub>Updated automatically via GitHub Actions on {updated_date} · "
        f"{fmt_num(stats['all_time_contributions'])} lifetime contributions across "
        f"{fmt_num(stats['public_repos'])} public repositories</sub>"
    )
    text = replace_marker(text, "LAST_UPDATED", footer_line)

    README_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    token = get_token()
    stats = fetch_all_github_data(token)

    for mode in ("light", "dark"):
        (ASSETS / f"hero-{mode}.svg").write_text(render_hero_svg(stats, mode), encoding="utf-8")
        (ASSETS / f"stats-overview-{mode}.svg").write_text(render_stats_overview_svg(stats, mode), encoding="utf-8")
        (ASSETS / f"stats-rhythm-{mode}.svg").write_text(render_stats_rhythm_svg(stats, mode), encoding="utf-8")
        (ASSETS / f"activity-horizon-{mode}.svg").write_text(render_activity_horizon_svg(stats, mode), encoding="utf-8")

    update_readme(stats)
    print(
        f"Profile updated: {stats['all_time_contributions']} lifetime contributions, "
        f"{stats['rolling_365']} past 365d, {stats['current_streak']}d streak, "
        f"{stats['public_repos']} public repos."
    )


if __name__ == "__main__":
    main()
