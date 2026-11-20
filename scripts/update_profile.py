#!/usr/bin/env python3
"""
Fetch live GitHub telemetry for Elvinoacer and render the calm, gently animated,
light/dark adaptive SVG visual suite plus dynamic README metadata.

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
        "canvas_alt": "#ECF3EF",
        "surface": "#FFFFFF",
        "subtle": "#F0F6F3",
        "border": "#DCE6E1",
        "divider": "#E5EDE9",
        "track": "#E4ECE8",
        "ink": "#182924",
        "ink_sec": "#4B615A",
        "ink_muted": "#7A9089",
        "pine": "#2C6E5B",
        "lake": "#477A96",
        "moss": "#6C9A7F",
        "ochre": "#A8844E",
        "sky_top": "#F5F9F7",
        "sky_mid": "#EAF2EE",
        "sky_bot": "#DCEAE4",
        "orb": "#F2DFB6",
        "orb_glow": "#E5C98B",
        "wave_1": "#8EB4C4",
        "wave_2": "#699C8A",
        "wave_3": "#3B7A67",
        "firefly": "#C9A15A",
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
        "canvas_alt": "#111920",
        "surface": "#121920",
        "subtle": "#172129",
        "border": "#22303A",
        "divider": "#1D2A33",
        "track": "#1C2830",
        "ink": "#E6EFEA",
        "ink_sec": "#95AAA3",
        "ink_muted": "#687F78",
        "pine": "#63B59B",
        "lake": "#72A6C4",
        "moss": "#88BFA0",
        "ochre": "#D1B077",
        "sky_top": "#0E141A",
        "sky_mid": "#111C23",
        "sky_bot": "#16262E",
        "orb": "#E9D9B5",
        "orb_glow": "#9FC4B5",
        "wave_1": "#365E73",
        "wave_2": "#2A6154",
        "wave_3": "#1E4B40",
        "firefly": "#E5C989",
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


def compute_rank(all_time: int, rolling_365: int, merged_prs: int, stars: int, repos: int, followers: int) -> tuple[str, float]:
    """Compute a transparent, calm GitHub developer activity rank & percentile (0..1)."""
    score = (
        min(1.0, rolling_365 / 2500.0) * 0.40
        + min(1.0, all_time / 4000.0) * 0.22
        + min(1.0, merged_prs / 80.0) * 0.16
        + min(1.0, repos / 60.0) * 0.10
        + min(1.0, stars / 40.0) * 0.07
        + min(1.0, followers / 30.0) * 0.05
    )
    pct = max(0.25, min(0.98, score))
    if pct >= 0.90:
        grade = "S"
    elif pct >= 0.80:
        grade = "A+"
    elif pct >= 0.68:
        grade = "A"
    elif pct >= 0.55:
        grade = "B+"
    else:
        grade = "B"
    return grade, pct


def fetch_all_github_data(token: str) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    now_eat = now_utc.astimezone(EAT_TZ)

    # 1. Core profile + rolling 365-day calendar + merged PRs / starred repos
    core_query = """
    query($login: String!) {
      user(login: $login) {
        id
        name
        login
        location
        createdAt
        followers { totalCount }
        following { totalCount }
        mergedPRs: pullRequests(states: MERGED) { totalCount }
        starredRepositories { totalCount }
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
    created_dt = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    created_label = created_dt.strftime("%b %Y")
    current_year = now_utc.year

    # 2. Fetch EVERY year since account creation for true all-time totals & longest streak
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
    today_str = now_utc.strftime("%Y-%m-%d")

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
                if d["date"] <= today_str:
                    all_days_map[d["date"]] = max(all_days_map.get(d["date"], 0), d["contributionCount"])

    # True all-time longest streak
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

    # Current streak (allow today == 0 if yesterday > 0)
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

    # Rolling 365-day calendar
    rolling_cal = user["contributionsCollection"]["contributionCalendar"]
    rolling_weeks = rolling_cal["weeks"]
    rolling_days = [d for w in rolling_weeks for d in w["contributionDays"]]
    rolling_days_past = [d for d in rolling_days if d["date"] <= today_str]

    rolling_365 = rolling_cal["totalContributions"]
    active_days = sum(1 for d in rolling_days_past if d["contributionCount"] > 0)
    total_cal_days = max(1, len(rolling_days_past))
    active_pct = (active_days / total_cal_days) * 100.0
    active_avg = rolling_365 / max(1, active_days)
    weekly_avg = rolling_365 / 52.0

    best_day = (
        max(rolling_days_past, key=lambda d: d["contributionCount"])
        if rolling_days_past
        else {"date": today_str, "contributionCount": 0}
    )
    rolling_30 = sum(d["contributionCount"] for d in rolling_days_past[-30:])
    rolling_7 = sum(d["contributionCount"] for d in rolling_days_past[-7:])

    # Weekday cadence (Mon=0 .. Sun=6)
    dow_mon_sun = [0] * 7
    for d in rolling_days_past:
        mon_idx = (d["weekday"] - 1) % 7
        dow_mon_sun[mon_idx] += d["contributionCount"]

    # Last 12 complete/active calendar months for the Calm Currents stream
    monthly_map: dict[tuple[int, int], int] = {}
    for d in rolling_days_past:
        yr = int(d["date"][:4])
        mo = int(d["date"][5:7])
        monthly_map[(yr, mo)] = monthly_map.get((yr, mo), 0) + d["contributionCount"]
    monthly_sorted = sorted(monthly_map.items(), key=lambda kv: kv[0])[-12:]
    monthly_series = [
        {"year": yr, "month": mo, "label": datetime(yr, mo, 1).strftime("%b"), "total": val}
        for (yr, mo), val in monthly_sorted
    ]

    # Full 52-week grid for the sleek bottom ribbon
    ribbon_weeks = rolling_weeks[-52:]

    # 3. Paginate ALL public non-fork owned repositories
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
            stargazerCount
            forkCount
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
    total_langs_count = len(sorted_langs)
    top_langs: list[dict[str, Any]] = []
    other_bytes = 0
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
    if other_bytes > 0:
        top_langs.append(
            {
                "name": "Other",
                "bytes": other_bytes,
                "pct": (other_bytes / total_code_bytes) * 100.0,
                "repos": max(1, total_langs_count - 5),
            }
        )

    # 4. Authored commit timestamps for EAT (UTC+3) coding rhythm
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
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 15, author: {id: $authorId}) {
                    nodes { committedDate }
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

    merged_prs = max(all_time_prs, user["mergedPRs"]["totalCount"])
    followers = user["followers"]["totalCount"]
    rank_grade, rank_pct = compute_rank(
        all_time_contributions, rolling_365, merged_prs, total_stars, public_repo_count, followers
    )

    # YoY growth vs previous year
    yoy_label = ""
    if len(yearly_totals) >= 2 and yearly_totals[-2][1] > 0:
        prev_y, curr_y = yearly_totals[-2][1], yearly_totals[-1][1]
        pct_change = ((curr_y - prev_y) / prev_y) * 100.0
        if pct_change >= 0:
            yoy_label = f"+{pct_change:.0f}% vs {yearly_totals[-2][0]}"
        else:
            yoy_label = f"{pct_change:.0f}% vs {yearly_totals[-2][0]}"

    repo_lookup = {r["name"]: r for r in all_public_repos}

    return {
        "now_eat": now_eat,
        "name": user["name"] or "Elvin Omondi Juma",
        "login": user["login"],
        "created_label": created_label,
        "followers": followers,
        "following": user["following"]["totalCount"],
        "starred_count": user["starredRepositories"]["totalCount"],
        "public_repos": public_repo_count,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "total_code_bytes": total_code_bytes,
        "total_langs_count": total_langs_count,
        "all_time_contributions": all_time_contributions,
        "all_time_commits": all_time_commits,
        "merged_prs": merged_prs,
        "all_time_issues_reviews": all_time_issues + all_time_reviews,
        "all_time_restricted": all_time_restricted,
        "rolling_365": rolling_365,
        "rolling_30": rolling_30,
        "rolling_7": rolling_7,
        "active_days": active_days,
        "total_cal_days": total_cal_days,
        "active_pct": active_pct,
        "active_avg": active_avg,
        "weekly_avg": weekly_avg,
        "best_day_count": best_day["contributionCount"],
        "best_day_date": fmt_short_date(best_day["date"]),
        "current_streak": current_streak,
        "current_range": f"{fmt_short_date(current_start)} – {fmt_short_date(current_end)}" if current_streak else "Quiet today",
        "longest_streak": longest_streak,
        "longest_range": f"{fmt_short_date(longest_range[0])} – {fmt_short_date(longest_range[1])}" if longest_streak else "—",
        "yearly_totals": yearly_totals,
        "yoy_label": yoy_label,
        "rank_grade": rank_grade,
        "rank_pct": rank_pct,
        "dow_mon_sun": dow_mon_sun,
        "top_langs": top_langs,
        "eat_buckets": eat_buckets,
        "monthly_series": monthly_series,
        "ribbon_weeks": ribbon_weeks,
        "repo_lookup": repo_lookup,
    }


def smooth_curve(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0][0]:.1f} {points[0][1]:.1f}"
    parts = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    for i in range(len(points) - 1):
        p0 = points[max(0, i - 1)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(len(points) - 1, i + 2)]
        t = 0.2
        c1x = p1[0] + (p2[0] - p0[0]) * t
        c1y = p1[1] + (p2[1] - p0[1]) * t
        c2x = p2[0] - (p3[0] - p1[0]) * t
        c2y = p2[1] - (p3[1] - p1[1]) * t
        parts.append(f"C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(parts)


def make_periodic_wave_path(width: int, base_y: float, amp: float, cycles: int, phase: float, bottom_y: float) -> str:
    """Create a 2x-wide seamless periodic wave path for butter-smooth horizontal looping."""
    total_w = width * 2
    steps = 72
    pts = []
    for i in range(steps + 1):
        x = (i / steps) * total_w
        theta = (x / width) * 2.0 * math.pi * cycles + phase
        y = base_y + math.sin(theta) * amp + math.cos(theta * 2.0 - phase) * (amp * 0.22)
        pts.append((x, y))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} " + " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts[1:])
    return f"{d} L {total_w} {bottom_y} L 0 {bottom_y} Z"


def render_hero_svg(stats: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 920, 196
    streak_txt = f"{stats['current_streak']}-day streak" if stats["current_streak"] > 0 else "Quiet day"
    pill_text = f"Eldoret, Kenya  ·  {streak_txt}  ·  {fmt_num(stats['rolling_365'])} contributions / 1y"
    pill_w = min(440, max(280, int(len(pill_text) * 5.6) + 38))

    # Gentle floating light motes on the right
    motes = [
        (648, 128, 2.0, "14s", "0s"),
        (712, 108, 1.6, "18s", "-4s"),
        (766, 134, 2.2, "16s", "-8s"),
        (838, 112, 1.8, "20s", "-3s"),
        (874, 140, 1.5, "15s", "-9s"),
    ]
    motes_svg = []
    for mx, my, mr, dur, beg in motes:
        motes_svg.append(
            f'<circle cx="{mx}" cy="{my}" r="{mr}" fill="{t["firefly"]}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.55;0.2;0" dur="{dur}" begin="{beg}" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 8; 6 -16; -4 -34" dur="{dur}" begin="{beg}" repeatCount="indefinite"/>'
            f'</circle>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Elvin Omondi Juma — Founding Engineer at Great Thumbs Software Solutions">
<defs>
  <clipPath id="heroClip"><rect width="{w}" height="{h}" rx="16"/></clipPath>
  <linearGradient id="heroBg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{t['surface']}"/>
    <stop offset="62%" stop-color="{t['canvas']}"/>
    <stop offset="100%" stop-color="{t['canvas_alt']}"/>
  </linearGradient>
  <radialGradient id="heroGlow" cx="0.85" cy="0.28" r="0.34">
    <stop offset="0%" stop-color="{t['orb_glow']}" stop-opacity="0.30"/>
    <stop offset="55%" stop-color="{t['pine']}" stop-opacity="0.06"/>
    <stop offset="100%" stop-color="{t['canvas']}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="heroOrbGrad" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0%" stop-color="{t['orb']}" stop-opacity="0.72"/>
    <stop offset="70%" stop-color="{t['orb']}" stop-opacity="0.32"/>
    <stop offset="100%" stop-color="{t['orb']}" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="mistBand" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{t['pine']}" stop-opacity="0"/>
    <stop offset="50%" stop-color="{t['lake']}" stop-opacity="0.14"/>
    <stop offset="100%" stop-color="{t['pine']}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="hillFar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['wave_1']}" stop-opacity="0.28"/>
    <stop offset="100%" stop-color="{t['wave_1']}" stop-opacity="0.03"/>
  </linearGradient>
  <linearGradient id="hillNear" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['pine']}" stop-opacity="0.22"/>
    <stop offset="100%" stop-color="{t['pine']}" stop-opacity="0.03"/>
  </linearGradient>
</defs>

<g clip-path="url(#heroClip)">
  <rect width="{w}" height="{h}" fill="url(#heroBg)"/>
  <rect width="{w}" height="{h}" fill="url(#heroGlow)"/>

  <!-- Gently breathing dawn/dusk orb -->
  <circle cx="792" cy="56" r="34" fill="url(#heroOrbGrad)">
    <animate attributeName="r" values="30;37;30" dur="9s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="0.72;1;0.72" dur="9s" repeatCount="indefinite"/>
  </circle>

  <!-- Soft drifting mist ribbon -->
  <ellipse cx="720" cy="126" rx="220" ry="20" fill="url(#mistBand)">
    <animateTransform attributeName="transform" type="translate" values="-28 0; 28 0; -28 0" dur="28s" repeatCount="indefinite"/>
  </ellipse>

  <!-- Layered highland curves -->
  <path d="M 476 196 C 548 136, 616 122, 686 144 C 746 162, 806 96, 874 120 C 896 128, 912 136, 926 142 L 926 196 Z" fill="url(#hillFar)"/>
  <path d="M 556 196 C 626 150, 696 156, 766 134 C 826 118, 878 144, 926 132 L 926 196 Z" fill="url(#hillNear)"/>
  <path d="M 556 196 C 626 150, 696 156, 766 134 C 826 118, 878 144, 926 132" fill="none" stroke="{t['pine']}" stroke-opacity="0.24" stroke-width="1"/>

  <!-- Subtle drifting light motes -->
  <g>{"".join(motes_svg)}</g>

  <!-- Live status pill -->
  <g transform="translate(42, 26)">
    <rect width="{pill_w}" height="26" rx="13" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="1"/>
    <circle cx="15" cy="13" r="3.6" fill="{t['pine']}">
      <animate attributeName="opacity" values="0.95;0.35;0.95" dur="5s" repeatCount="indefinite"/>
    </circle>
    <text x="27" y="17" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.4" font-weight="500">{esc(pill_text)}</text>
  </g>

  <!-- Concise identity -->
  <text x="42" y="98" fill="{t['ink']}" font-family="{SERIF}" font-size="33" font-weight="400" letter-spacing="-0.4">{esc(stats['name'])}</text>
  <text x="42" y="125" fill="{t['ink_sec']}" font-family="{SANS}" font-size="13.8" font-weight="500">Founding Engineer @ GTSS  ·  Full-Stack Product Architect</text>
  <text x="42" y="152" fill="{t['ink_muted']}" font-family="{SERIF}" font-style="italic" font-size="12.8">Quiet, dependable software for healthcare, commerce, and real-world operations.</text>

  <!-- Subtle footer telemetry line -->
  <text x="42" y="178" fill="{t['ink_muted']}" font-family="{SANS}" font-size="11">
    <tspan fill="{t['ink_sec']}" font-weight="600">@{esc(stats['login'])}</tspan>
    <tspan>  ·  {fmt_num(stats['public_repos'])} public repos  ·  {fmt_num(stats['all_time_contributions'])} lifetime contributions</tspan>
  </text>
</g>

<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="15.5" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
'''


def render_stats_overview_svg(stats: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 920, 356

    # Circular ring helper (r=33 -> circumference = 207.35)
    r = 33.0
    circ = 2.0 * math.pi * r
    rank_dash = circ * stats["rank_pct"]
    cons_dash = circ * min(1.0, stats["active_pct"] / 100.0)
    streak_ratio = min(1.0, max(0.16, stats["current_streak"] / max(1, stats["longest_streak"])))
    streak_dash = circ * streak_ratio

    # 6 compact vector-icon metric tiles (x=36..884 -> 6 * 134 + 5 * 8.8 = 848)
    rev_cnt = stats["all_time_issues_reviews"]
    rev_lbl = f"{rev_cnt} review" if rev_cnt == 1 else f"{rev_cnt} reviews"
    tiles = [
        ("Commits", fmt_num(stats["all_time_commits"]), "all-time", t["pine"],
         '<circle cx="7" cy="7" r="2.6" fill="none" stroke="COL" stroke-width="1.4"/><line x1="1" y1="7" x2="4.4" y2="7" stroke="COL" stroke-width="1.4"/><line x1="9.6" y1="7" x2="13" y2="7" stroke="COL" stroke-width="1.4"/>'),
        ("Merged PRs", fmt_num(stats["merged_prs"]), rev_lbl, t["lake"],
         '<circle cx="3.5" cy="3.5" r="1.8" fill="none" stroke="COL" stroke-width="1.3"/><circle cx="3.5" cy="10.5" r="1.8" fill="none" stroke="COL" stroke-width="1.3"/><circle cx="10.5" cy="10.5" r="1.8" fill="none" stroke="COL" stroke-width="1.3"/><line x1="3.5" y1="5.3" x2="3.5" y2="8.7" stroke="COL" stroke-width="1.3"/><path d="M 3.5 5.3 C 3.5 8, 10.5 7, 10.5 8.7" fill="none" stroke="COL" stroke-width="1.3"/>'),
        ("Private", fmt_num(stats["all_time_restricted"]), "contributions", t["moss"],
         '<rect x="2.5" y="6.2" width="9" height="6.2" rx="1.5" fill="none" stroke="COL" stroke-width="1.3"/><path d="M 4.5 6.2 V 4.4 A 2.5 2.5 0 0 1 9.5 4.4 V 6.2" fill="none" stroke="COL" stroke-width="1.3"/>'),
        ("Public Repos", fmt_num(stats["public_repos"]), fmt_bytes(stats["total_code_bytes"]), t["lake"],
         '<rect x="2" y="2.5" width="10" height="9" rx="1.6" fill="none" stroke="COL" stroke-width="1.3"/><line x1="2" y1="5.8" x2="12" y2="5.8" stroke="COL" stroke-width="1.2"/>'),
        ("Stars · Forks", f"{fmt_num(stats['total_stars'])} · {fmt_num(stats['total_forks'])}", f"{stats['starred_count']} starred", t["ochre"],
         '<polygon points="7,1.5 8.7,5 12.5,5.5 9.7,8.2 10.4,12 7,10.2 3.6,12 4.3,8.2 1.5,5.5 5.3,5" fill="none" stroke="COL" stroke-width="1.25" stroke-linejoin="round"/>'),
        ("Followers", fmt_num(stats["followers"]), f"{stats['following']} following", t["pine"],
         '<circle cx="7" cy="4.8" r="2.3" fill="none" stroke="COL" stroke-width="1.3"/><path d="M 2.4 11.8 C 2.8 9.2, 11.2 9.2, 11.6 11.8" fill="none" stroke="COL" stroke-width="1.3" stroke-linecap="round"/>'),
    ]

    tiles_svg = []
    tile_w = 133.5
    tile_gap = 9.4
    for i, (lbl, val, sub, col, icon_raw) in enumerate(tiles):
        tx = 36.0 + i * (tile_w + tile_gap)
        icon = icon_raw.replace("COL", col)
        tiles_svg.append(
            f'<g transform="translate({tx:.1f}, 186)">'
            f'<rect width="{tile_w:.1f}" height="68" rx="10" fill="{t["subtle"]}" stroke="{t["border"]}" stroke-width="0.8"/>'
            f'<g transform="translate(12, 11)">{icon}</g>'
            f'<text x="31" y="21.5" fill="{t["ink_sec"]}" font-family="{SANS}" font-size="10.6" font-weight="500">{lbl}</text>'
            f'<text x="12" y="45" fill="{t["ink"]}" font-family="{SANS}" font-size="16" font-weight="700">{val}</text>'
            f'<text x="12" y="59" fill="{t["ink_muted"]}" font-family="{SANS}" font-size="9.6">{sub}</text>'
            f'</g>'
        )

    # Bottom 3-column Yearly Growth Cards (cleanly aligned with the 3 circular gauges above!)
    recent_years = stats["yearly_totals"][-3:]
    max_y = max((v for _, v in recent_years), default=1) or 1
    n_yr = max(1, len(recent_years))
    yr_gap = 14.0
    yr_w = (848.0 - yr_gap * (n_yr - 1)) / n_yr
    yr_svg = []
    for i, (yr, val) in enumerate(recent_years):
        yx = 36.0 + i * (yr_w + yr_gap)
        is_latest = i == len(recent_years) - 1
        bar_w = max(8.0, (val / max_y) * (yr_w - 28.0))
        bar_col = t["pine"] if is_latest else t["moss"]
        bar_op = "0.95" if is_latest else "0.62"
        yr_svg.append(
            f'<g transform="translate({yx:.1f}, 292)">'
            f'<rect width="{yr_w:.1f}" height="46" rx="9" fill="{t["subtle"]}" stroke="{t["border"]}" stroke-width="0.8"/>'
            f'<text x="14" y="19" fill="{t["ink_sec"]}" font-family="{MONO}" font-size="11">{yr}</text>'
            f'<text x="{yr_w - 14:.1f}" y="20" text-anchor="end" fill="{t["ink"] if is_latest else t["ink_sec"]}" font-family="{SANS}" font-size="13" font-weight="{700 if is_latest else 600}">{fmt_num(val)}</text>'
            f'<rect x="14" y="29" width="{yr_w - 28:.1f}" height="6" rx="3" fill="{t["track"]}"/>'
            f'<rect x="14" y="29" width="{bar_w:.1f}" height="6" rx="3" fill="{bar_col}" fill-opacity="{bar_op}"/>'
            f'</g>'
        )

    yoy_pill = f"  ·  {stats['yoy_label']}" if stats["yoy_label"] else ""

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="GitHub Telemetry — Automatically Tracked">
<rect width="{w}" height="{h}" rx="16" fill="{t['surface']}" stroke="{t['border']}" stroke-width="1"/>

<!-- Header -->
<text x="36" y="36" fill="{t['ink']}" font-family="{SERIF}" font-size="17" font-weight="400">GitHub Telemetry</text>
<g transform="translate(692, 26)">
  <circle cx="0" cy="6" r="3.2" fill="{t['pine']}">
    <animate attributeName="opacity" values="0.95;0.32;0.95" dur="4.5s" repeatCount="indefinite"/>
  </circle>
  <text x="10" y="10" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.8">Synced automatically by GitHub</text>
</g>
<line x1="36" y1="50" x2="884" y2="50" stroke="{t['divider']}" stroke-width="1"/>

<!-- ROW 1: 3 Circular Gauge Cards -->
<!-- Gauge 1: Rank & Lifetime Contributions -->
<g transform="translate(36, 64)">
  <rect width="273" height="108" rx="12" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <circle cx="54" cy="54" r="{r:.0f}" fill="none" stroke="{t['track']}" stroke-width="6"/>
  <circle cx="54" cy="54" r="{r:.0f}" fill="none" stroke="{t['pine']}" stroke-width="6" stroke-linecap="round"
          stroke-dasharray="{rank_dash:.1f} {circ:.1f}" transform="rotate(-90 54 54)">
    <animate attributeName="stroke-opacity" values="0.96;0.74;0.96" dur="6s" repeatCount="indefinite"/>
  </circle>
  <text x="54" y="59" text-anchor="middle" fill="{t['pine']}" font-family="{SERIF}" font-size="22" font-weight="700">{esc(stats['rank_grade'])}</text>
  <text x="104" y="34" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11">Lifetime contributions</text>
  <text x="104" y="62" fill="{t['ink']}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-0.4">{fmt_num(stats['all_time_contributions'])}</text>
  <text x="104" y="81" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">{fmt_num(stats['rolling_365'])} past year · {fmt_num(stats['rolling_30'])} / 30d</text>
</g>

<!-- Gauge 2: Consistency Ring -->
<g transform="translate(323.5, 64)">
  <rect width="273" height="108" rx="12" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <circle cx="54" cy="54" r="{r:.0f}" fill="none" stroke="{t['track']}" stroke-width="6"/>
  <circle cx="54" cy="54" r="{r:.0f}" fill="none" stroke="{t['lake']}" stroke-width="6" stroke-linecap="round"
          stroke-dasharray="{cons_dash:.1f} {circ:.1f}" transform="rotate(-90 54 54)"/>
  <text x="54" y="59" text-anchor="middle" fill="{t['lake']}" font-family="{SANS}" font-size="15.5" font-weight="700">{stats['active_pct']:.0f}%</text>
  <text x="104" y="34" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11">Active days (past year)</text>
  <text x="104" y="62" fill="{t['ink']}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-0.4">{stats['active_days']} days</text>
  <text x="104" y="81" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">{stats['active_avg']:.1f} / active day · {stats['weekly_avg']:.0f} / wk</text>
</g>

<!-- Gauge 3: Streak Ring -->
<g transform="translate(611, 64)">
  <rect width="273" height="108" rx="12" fill="{t['subtle']}" stroke="{t['border']}" stroke-width="0.8"/>
  <circle cx="54" cy="54" r="{r:.0f}" fill="none" stroke="{t['track']}" stroke-width="6"/>
  <circle cx="54" cy="54" r="{r:.0f}" fill="none" stroke="{t['ochre']}" stroke-width="6" stroke-linecap="round"
          stroke-dasharray="{streak_dash:.1f} {circ:.1f}" transform="rotate(-90 54 54)">
    <animate attributeName="stroke-opacity" values="1;0.68;1" dur="5.2s" repeatCount="indefinite"/>
  </circle>
  <text x="54" y="59" text-anchor="middle" fill="{t['ochre']}" font-family="{SANS}" font-size="16" font-weight="700">{stats['current_streak']}d</text>
  <text x="104" y="34" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11">Current &amp; best streak</text>
  <text x="104" y="62" fill="{t['ink']}" font-family="{SANS}" font-size="24" font-weight="700" letter-spacing="-0.4">{stats['longest_streak']}d best</text>
  <text x="104" y="81" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.5">Peak day: {fmt_num(stats['best_day_count'])} · {esc(stats['best_day_date'])}</text>
</g>

<!-- ROW 2: 6 Crisp Icon Stat Tiles -->
<g>{"".join(tiles_svg)}</g>

<!-- ROW 3: Yearly Momentum Strip -->
<text x="36" y="280" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.5" font-weight="600">Yearly momentum<tspan fill="{t['pine']}" font-weight="600">{esc(yoy_pill)}</tspan></text>
<text x="884" y="280" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.6">Active since {esc(stats['created_label'])} · {stats['total_langs_count']} languages · {fmt_bytes(stats['total_code_bytes'])}</text>
<g>{"".join(yr_svg)}</g>
</svg>
'''


def render_stats_rhythm_svg(stats: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    w, h = 920, 290

    # LEFT: Language Donut Chart + Clean Compact Legend
    langs = stats["top_langs"]
    cx_d, cy_d, r_d = 104.0, 148.0, 50.0
    circ_d = 2.0 * math.pi * r_d
    donut_segs = []
    offset_acc = 0.0
    for l in langs:
        col = t["lang_colors"].get(l["name"], t["lang_colors"]["Other"])
        seg_len = max(2.0, (l["pct"] / 100.0) * circ_d)
        # Small 1.5px visual gap between slices
        vis_len = max(1.5, seg_len - 1.5)
        donut_segs.append(
            f'<circle cx="{cx_d:.0f}" cy="{cy_d:.0f}" r="{r_d:.0f}" fill="none" stroke="{col}" stroke-width="14" '
            f'stroke-dasharray="{vis_len:.2f} {circ_d:.2f}" stroke-dashoffset="{-offset_acc:.2f}" '
            f'transform="rotate(-90 {cx_d:.0f} {cy_d:.0f})"/>'
        )
        offset_acc += seg_len

    lang_rows = []
    for i, l in enumerate(langs[:6]):
        col = t["lang_colors"].get(l["name"], t["lang_colors"]["Other"])
        ly = 88 + i * 26
        sub_label = f"{l['repos']} langs" if l["name"] == "Other" else f"{l['repos']} repos"
        lang_rows.append(
            f'<circle cx="192" cy="{ly - 4}" r="4.2" fill="{col}"/>'
            f'<text x="204" y="{ly}" fill="{t["ink"]}" font-family="{SANS}" font-size="12" font-weight="600">{esc(l["name"])}</text>'
            f'<text x="352" y="{ly}" text-anchor="end" fill="{t["ink_muted"]}" font-family="{SANS}" font-size="10.4">{esc(sub_label)}</text>'
            f'<text x="424" y="{ly}" text-anchor="end" fill="{t["ink"]}" font-family="{SANS}" font-size="12" font-weight="600">{l["pct"]:.1f}%</text>'
        )

    # Core stack calm visual pill bar along bottom-left (flush to x=424)
    stack_items = ["TypeScript", "Next.js", "React", "Prisma", "PostgreSQL", "Socket.IO"]
    stack_svg = []
    sx = 36
    for s_name in stack_items:
        sw = int(len(s_name) * 5.6) + 14
        if sx + sw > 428:
            break
        stack_svg.append(
            f'<rect x="{sx}" y="246" width="{sw}" height="22" rx="6" fill="{t["subtle"]}" stroke="{t["border"]}" stroke-width="0.7"/>'
            f'<text x="{sx + sw / 2:.1f}" y="260.5" text-anchor="middle" fill="{t["ink_sec"]}" font-family="{SANS}" font-size="9.6" font-weight="500">{s_name}</text>'
        )
        sx += sw + 5

    # RIGHT: Weekly Cadence (Mon..Sun) with gentle breathing highlight on peak day
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    full_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = stats["dow_mon_sun"]
    max_dow = max(dow) if dow and max(dow) > 0 else 1
    peak_i = dow.index(max(dow))

    dow_bars = []
    chart_base_y = 160
    max_bar_h = 72.0
    for i, (d_lbl, val) in enumerate(zip(day_names, dow)):
        bx = 496 + i * 56
        bh = max(8.0, (val / max_dow) * max_bar_h)
        by = chart_base_y - bh
        is_peak = i == peak_i
        fill_col = t["pine"] if is_peak else t["lake"]
        fill_op = "0.95" if is_peak else f"{0.35 + 0.44 * (val / max_dow):.2f}"
        anim = '<animate attributeName="fill-opacity" values="0.96;0.70;0.96" dur="5.2s" repeatCount="indefinite"/>' if is_peak else ""
        dow_bars.append(
            f'<rect x="{bx}" y="{by:.1f}" width="32" height="{bh:.1f}" rx="6" fill="{fill_col}" fill-opacity="{fill_op}">{anim}</rect>'
            f'<text x="{bx + 16}" y="{by - 6:.1f}" text-anchor="middle" fill="{t["ink"] if is_peak else t["ink_muted"]}" font-family="{SANS}" font-size="10" font-weight="{600 if is_peak else 500}">{val}</text>'
            f'<text x="{bx + 16}" y="{chart_base_y + 17}" text-anchor="middle" fill="{t["ink"] if is_peak else t["ink_sec"]}" font-family="{SANS}" font-size="11" font-weight="{600 if is_peak else 400}">{d_lbl}</text>'
        )
    dow_bars.append(f'<line x1="490" y1="{chart_base_y + 0.5:.1f}" x2="884" y2="{chart_base_y + 0.5:.1f}" stroke="{t["divider"]}" stroke-width="1"/>')

    # RIGHT BOTTOM: Sleek segmented Time-of-Day Rhythm Bar (EAT · UTC+3)
    buckets = stats["eat_buckets"]
    b_tot = sum(buckets.values()) or 1
    ordered_b = [
        ("Morning", "06–12", buckets["Morning"], t["ochre"]),
        ("Afternoon", "12–18", buckets["Afternoon"], t["pine"]),
        ("Evening", "18–00", buckets["Evening"], t["lake"]),
        ("Night", "00–06", buckets["Night"], t["moss"]),
    ]
    top_bucket = max(ordered_b, key=lambda x: x[2])[0]
    tod_bar_x, tod_bar_w = 490.0, 394.0
    tod_segs = []
    tod_labels = []
    cur_tx = tod_bar_x
    for i, (b_name, b_hrs, b_cnt, b_col) in enumerate(ordered_b):
        pct = (b_cnt / b_tot) * 100.0
        sw = max(8.0, (pct / 100.0) * tod_bar_w)
        if i == len(ordered_b) - 1:
            sw = max(4.0, (tod_bar_x + tod_bar_w) - cur_tx)
        tod_segs.append(f'<rect x="{cur_tx:.1f}" y="224" width="{sw:.1f}" height="10" fill="{b_col}" fill-opacity="0.88"/>')
        cur_tx += sw

        lx = 490 + i * 100
        tod_labels.append(
            f'<circle cx="{lx + 4}" cy="252" r="3.5" fill="{b_col}"/>'
            f'<text x="{lx + 13}" y="256" fill="{t["ink_sec"]}" font-family="{SANS}" font-size="10.4">{b_name}</text>'
            f'<text x="{lx + 13}" y="271" fill="{t["ink"]}" font-family="{SANS}" font-size="11.5" font-weight="700">{pct:.0f}% <tspan fill="{t["ink_muted"]}" font-family="{MONO}" font-size="9" font-weight="400">{b_hrs}</tspan></text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Languages, Stack, Weekly Cadence, and Coding Rhythm">
<defs>
  <clipPath id="todClip"><rect x="{tod_bar_x:.0f}" y="224" width="{tod_bar_w:.0f}" height="10" rx="5"/></clipPath>
</defs>

<rect width="{w}" height="{h}" rx="16" fill="{t['surface']}" stroke="{t['border']}" stroke-width="1"/>
<line x1="458" y1="22" x2="458" y2="268" stroke="{t['divider']}" stroke-width="1"/>

<!-- LEFT: Languages Donut + Stack -->
<text x="36" y="36" fill="{t['ink']}" font-family="{SERIF}" font-size="16.5" font-weight="400">Languages &amp; Stack</text>
<text x="424" y="35" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.6">{fmt_num(stats['public_repos'])} public repos</text>
<line x1="36" y1="48" x2="424" y2="48" stroke="{t['divider']}" stroke-width="1"/>

<circle cx="{cx_d:.0f}" cy="{cy_d:.0f}" r="{r_d:.0f}" fill="none" stroke="{t['track']}" stroke-width="14"/>
<g>{"".join(donut_segs)}</g>
<text x="{cx_d:.0f}" y="{cy_d - 2:.0f}" text-anchor="middle" fill="{t['ink']}" font-family="{SANS}" font-size="14.5" font-weight="700">{fmt_bytes(stats['total_code_bytes'])}</text>
<text x="{cx_d:.0f}" y="{cy_d + 14:.0f}" text-anchor="middle" fill="{t['ink_muted']}" font-family="{SANS}" font-size="9.6">{stats['total_langs_count']} languages</text>

<g>{"".join(lang_rows)}</g>
<g>{"".join(stack_svg)}</g>

<!-- RIGHT: Weekly Cadence & EAT Time-of-Day -->
<text x="490" y="36" fill="{t['ink']}" font-family="{SERIF}" font-size="16.5" font-weight="400">Coding Rhythm</text>
<text x="884" y="35" text-anchor="end" fill="{t['ink_muted']}" font-family="{SANS}" font-size="10.6">Peak: {full_names[peak_i]} · {top_bucket} (EAT)</text>
<line x1="490" y1="48" x2="884" y2="48" stroke="{t['divider']}" stroke-width="1"/>

<g>{"".join(dow_bars)}</g>

<line x1="490" y1="194" x2="884" y2="194" stroke="{t['divider']}" stroke-width="1"/>
<text x="490" y="214" fill="{t['ink_sec']}" font-family="{SANS}" font-size="11.2" font-weight="600">Daily window (EAT · UTC+3)</text>
<rect x="{tod_bar_x:.0f}" y="224" width="{tod_bar_w:.0f}" height="10" rx="5" fill="{t['track']}"/>
<g clip-path="url(#todClip)">{"".join(tod_segs)}</g>
<g>{"".join(tod_labels)}</g>
</svg>
'''


def render_activity_flow_svg(stats: dict[str, Any], theme_name: str) -> str:
    """
    Brand-new bottom centerpiece: "Calm Currents"
    - 3 softly gliding seamless silk-water waves (infinite smooth animation)
    - 12 luminous monthly contribution lanterns/orbs floating along a smooth flow curve
    - Expanding concentric zen ripples on Peak Month & Latest Month
    - Gentle drifting firefly motes
    - Full-width sleek 52-week contribution ribbon bridging cleanly into GitHub's native section
    """
    t = THEMES[theme_name]
    w, h = 920, 294

    # 3 seamless periodic silk waves gliding gently horizontally
    wave_back = make_periodic_wave_path(w, 154.0, 12.0, 2, 0.4, 212.0)
    wave_mid = make_periodic_wave_path(w, 168.0, 9.5, 3, 1.8, 212.0)
    wave_front = make_periodic_wave_path(w, 182.0, 6.5, 2, 3.1, 212.0)

    # 12 monthly contribution orbs floating smoothly above the water
    months = stats["monthly_series"]
    m_vals = [m["total"] for m in months]
    max_m = max(m_vals) if m_vals and max(m_vals) > 0 else 1
    peak_m_idx = m_vals.index(max(m_vals)) if m_vals else 0
    latest_m_idx = max(0, len(months) - 1)

    orb_pts: list[tuple[float, float]] = []
    n_m = max(2, len(months))
    for i, m in enumerate(months):
        mx = 58.0 + (i / (n_m - 1)) * (862.0 - 58.0)
        norm = math.sqrt(m["total"] / max_m)
        my = 166.0 - norm * 78.0
        orb_pts.append((mx, my))

    flow_line = smooth_curve(orb_pts)

    orbs_svg = []
    ripples_svg = []
    for i, (m, (ox, oy)) in enumerate(zip(months, orb_pts)):
        is_peak = i == peak_m_idx
        is_latest = i == latest_m_idx
        norm = math.sqrt(m["total"] / max_m)
        orb_r = 4.0 + norm * 3.8
        col = t["ochre"] if is_peak else (t["pine"] if is_latest else t["lake"])

        # Delicate vertical tether down to the waterline
        orbs_svg.append(
            f'<line x1="{ox:.1f}" y1="{oy + orb_r:.1f}" x2="{ox:.1f}" y2="188" stroke="{col}" stroke-opacity="0.22" stroke-width="1" stroke-dasharray="2 3"/>'
        )

        # Expanding zen water ripples beneath Peak & Latest months
        if is_peak or is_latest:
            rip_col = t["ochre"] if is_peak else t["pine"]
            dur_r = "4.8s" if is_peak else "5.6s"
            for delay in ("0s", "-2.4s"):
                ripples_svg.append(
                    f'<ellipse cx="{ox:.1f}" cy="188" rx="4" ry="1.8" fill="none" stroke="{rip_col}" stroke-width="1.1">'
                    f'<animate attributeName="rx" values="4;26" dur="{dur_r}" begin="{delay}" repeatCount="indefinite"/>'
                    f'<animate attributeName="ry" values="1.6;7.5" dur="{dur_r}" begin="{delay}" repeatCount="indefinite"/>'
                    f'<animate attributeName="stroke-opacity" values="0.55;0" dur="{dur_r}" begin="{delay}" repeatCount="indefinite"/>'
                    f'</ellipse>'
                )

        # Soft aura + glowing monthly orb
        orbs_svg.append(
            f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="{orb_r + 6:.1f}" fill="{col}" fill-opacity="0.16">'
            f'<animate attributeName="r" values="{orb_r + 4:.1f};{orb_r + 9:.1f};{orb_r + 4:.1f}" dur="{5.0 + (i % 4) * 1.1:.1f}s" repeatCount="indefinite"/>'
            f'</circle>'
            f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="{orb_r:.1f}" fill="{t["surface"]}" stroke="{col}" stroke-width="2"/>'
            f'<circle cx="{ox:.1f}" cy="{oy:.1f}" r="{max(1.8, orb_r * 0.42):.1f}" fill="{col}"/>'
        )

        # Month label + exact monthly total tucked cleanly along the quiet footer line of the water
        val_txt = fmt_num(m["total"])
        m_op = "1.0" if (is_peak or is_latest) else "0.74"
        orbs_svg.append(
            f'<text x="{ox:.1f}" y="{oy - orb_r - 7:.1f}" text-anchor="middle" fill="{t["ink"] if (is_peak or is_latest) else t["ink_sec"]}" font-family="{SANS}" font-size="9.8" font-weight="{700 if (is_peak or is_latest) else 500}">{val_txt}</text>'
            f'<text x="{ox:.1f}" y="203" text-anchor="middle" fill="{t["ink"]}" fill-opacity="{m_op}" font-family="{SANS}" font-size="9.8" font-weight="{700 if (is_peak or is_latest) else 500}">{esc(m["label"])}</text>'
        )

    # Floating peaceful twilight fireflies
    fireflies = [
        (135, 134, 1.7, "12s", "0s"),
        (275, 118, 1.5, "16s", "-5s"),
        (410, 126, 1.9, "14s", "-2s"),
        (545, 112, 1.5, "18s", "-7s"),
        (685, 130, 1.8, "13s", "-4s"),
        (805, 120, 1.6, "15s", "-9s"),
    ]
    ff_svg = []
    for fx, fy, fr, dur, beg in fireflies:
        ff_svg.append(
            f'<circle cx="{fx}" cy="{fy}" r="{fr}" fill="{t["firefly"]}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.65;0.18;0" dur="{dur}" begin="{beg}" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 6; 8 -14; -6 -28" dur="{dur}" begin="{beg}" repeatCount="indefinite"/>'
            f'</circle>'
        )

    # Full-width sleek 52-week calm pill-brick heatmap ribbon (y=222..276)
    r_weeks = stats["ribbon_weeks"]
    r_all = [d["contributionCount"] for wk in r_weeks for d in wk["contributionDays"] if d["contributionCount"] > 0]
    r_max = max(r_all) if r_all else 1
    nw = max(1, len(r_weeks))
    col_step = 848.0 / nw
    brick_w = max(6.0, col_step - 3.6)
    brick_h = 5.2
    row_step = 7.4
    ribbon_svg = []
    for wi, wk in enumerate(r_weeks):
        bx = 36.0 + wi * col_step
        for d in wk["contributionDays"]:
            di = d["weekday"]
            cnt = d["contributionCount"]
            if cnt == 0:
                lvl = 0
            else:
                ratio = cnt / r_max
                lvl = 1 if ratio < 0.20 else (2 if ratio < 0.45 else (3 if ratio < 0.72 else 4))
            by = 223.0 + di * row_step
            ribbon_svg.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{brick_w:.1f}" height="{brick_h:.1f}" rx="1.6" fill="{t["ramp"][lvl]}"/>'
            )

    peak_m = months[peak_m_idx] if months else {"label": "—", "total": 0}

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Calm Currents — Animated Monthly Contribution Flow and 52-Week Activity Ribbon">
<defs>
  <clipPath id="flowClip"><rect width="{w}" height="{h}" rx="16"/></clipPath>
  <clipPath id="waveBox"><rect x="0" y="56" width="{w}" height="156"/></clipPath>
  <linearGradient id="flowSky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{t['surface']}"/>
    <stop offset="48%" stop-color="{t['sky_mid']}"/>
    <stop offset="100%" stop-color="{t['sky_bot']}"/>
  </linearGradient>
</defs>

<g clip-path="url(#flowClip)">
  <!-- Backdrop -->
  <rect x="0" y="0" width="{w}" height="212" fill="url(#flowSky)"/>
  <rect x="0" y="212" width="{w}" height="{h - 212}" fill="{t['surface']}"/>

  <!-- Header -->
  <text x="36" y="34" fill="{t['ink']}" font-family="{SERIF}" font-size="16.5" font-weight="400">Calm Currents</text>
  <text x="884" y="33" text-anchor="end" fill="{t['ink_sec']}" font-family="{SANS}" font-size="10.8">
    {fmt_num(stats['rolling_30'])} in 30d  ·  {fmt_num(stats['rolling_7'])} in 7d  ·  Peak: {esc(peak_m['label'])} ({fmt_num(peak_m['total'])})
  </text>
  <line x1="36" y1="47" x2="884" y2="47" stroke="{t['divider']}" stroke-width="1"/>

  <!-- Gently gliding infinite silk-water waves -->
  <g clip-path="url(#waveBox)">
    <g>
      <path d="{wave_back}" fill="{t['wave_1']}" fill-opacity="0.22"/>
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-{w} 0" dur="36s" repeatCount="indefinite"/>
    </g>
    <g>
      <path d="{wave_mid}" fill="{t['wave_2']}" fill-opacity="0.24"/>
      <animateTransform attributeName="transform" type="translate" from="-{w} 0" to="0 0" dur="28s" repeatCount="indefinite"/>
    </g>
    <g>
      <path d="{wave_front}" fill="{t['wave_3']}" fill-opacity="0.16"/>
      <animateTransform attributeName="transform" type="translate" from="0 0" to="-{w} 0" dur="22s" repeatCount="indefinite"/>
    </g>
  </g>

  <!-- Floating firefly motes & zen ripples -->
  <g>{"".join(ff_svg)}</g>
  <g>{"".join(ripples_svg)}</g>

  <!-- Monthly luminous spline & floating lanterns -->
  <path d="{flow_line}" fill="none" stroke="{t['lake']}" stroke-opacity="0.45" stroke-width="1.6"/>
  <g>{"".join(orbs_svg)}</g>

  <!-- Subtle waterline divider into full 52-week calm ribbon -->
  <line x1="0" y1="212" x2="{w}" y2="212" stroke="{t['divider']}" stroke-width="1"/>
  <g>{"".join(ribbon_svg)}</g>
  <text x="36" y="285" fill="{t['ink_muted']}" font-family="{SANS}" font-size="9.5">52-week contribution cadence · automatically tracked by GitHub</text>
  <g transform="translate(772, 279)" font-family="{SANS}" font-size="9.2" fill="{t['ink_muted']}">
    <text x="0" y="6">Less</text>
    <rect x="25" y="-1" width="9" height="6" rx="1.5" fill="{t['ramp'][0]}"/>
    <rect x="37" y="-1" width="9" height="6" rx="1.5" fill="{t['ramp'][1]}"/>
    <rect x="49" y="-1" width="9" height="6" rx="1.5" fill="{t['ramp'][2]}"/>
    <rect x="61" y="-1" width="9" height="6" rx="1.5" fill="{t['ramp'][3]}"/>
    <rect x="73" y="-1" width="9" height="6" rx="1.5" fill="{t['ramp'][4]}"/>
    <text x="86" y="6">More</text>
  </g>
</g>

<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="15.5" fill="none" stroke="{t['border']}" stroke-width="1"/>
</svg>
'''


def replace_marker(content: str, tag: str, replacement: str) -> str:
    pattern = re.compile(rf"(<!-- {tag}:START -->).*?(<!-- {tag}:END -->)", re.DOTALL)
    if not pattern.search(content):
        return content
    return pattern.sub(rf"\1\n{replacement}\n\2", content)


def update_readme(stats: dict[str, Any]) -> None:
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")

    # Sync live star counts on public flagship repos
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

    updated_date = stats["now_eat"].strftime("%b %-d, %Y") if os.name != "nt" else stats["now_eat"].strftime("%b %d, %Y")
    footer_line = f"<sub>Auto-synced by GitHub Actions · {updated_date}</sub>"
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
        (ASSETS / f"activity-flow-{mode}.svg").write_text(render_activity_flow_svg(stats, mode), encoding="utf-8")

    update_readme(stats)
    print(
        f"Profile updated: rank {stats['rank_grade']}, {stats['all_time_contributions']} lifetime, "
        f"{stats['rolling_365']} past 365d, {stats['current_streak']}d streak, "
        f"{stats['public_repos']} public repos."
    )


if __name__ == "__main__":
    main()
