"""
World Cup Slack Bot
-------------------
Posts today's World Cup fixtures (UK time) and yesterday's results to Slack.

Data source: football-data.org (free tier includes the FIFA World Cup).
Delivery: Slack Incoming Webhook.

Required environment variables:
  FOOTBALL_DATA_TOKEN  - API token from https://www.football-data.org/client/register
  SLACK_WEBHOOK_URL    - Slack incoming webhook URL
"""

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

API_BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"  # FIFA World Cup
UK_TZ = ZoneInfo("Europe/London")

FLAGS = {
    "Argentina": "🇦🇷", "Australia": "🇦🇺", "Belgium": "🇧🇪", "Brazil": "🇧🇷",
    "Canada": "🇨🇦", "Colombia": "🇨🇴", "Croatia": "🇭🇷", "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "France": "🇫🇷", "Germany": "🇩🇪",
    "Ghana": "🇬🇭", "Iran": "🇮🇷", "Italy": "🇮🇹", "Japan": "🇯🇵",
    "Mexico": "🇲🇽", "Morocco": "🇲🇦", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿",
    "Nigeria": "🇳🇬", "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾",
    "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Senegal": "🇸🇳", "South Korea": "🇰🇷", "Spain": "🇪🇸", "Switzerland": "🇨🇭",
    "Tunisia": "🇹🇳", "Uruguay": "🇺🇾", "USA": "🇺🇸", "United States": "🇺🇸",
    "Uzbekistan": "🇺🇿", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Ivory Coast": "🇨🇮",
    "Côte d'Ivoire": "🇨🇮", "Jordan": "🇯🇴", "Cape Verde": "🇨🇻",
    "South Africa": "🇿🇦", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Denmark": "🇩🇰",
    "Haiti": "🇭🇹", "Curaçao": "🇨🇼",
}


def flag(team_name: str) -> str:
    return FLAGS.get(team_name, "⚽")


def team_label(team: dict) -> str:
    name = team.get("name") or "TBD"
    return f"{flag(name)} {name}"


def fetch_matches(date_from: str, date_to: str) -> list[dict]:
    """Fetch World Cup matches in a UTC date window (inclusive)."""
    token = os.environ["FOOTBALL_DATA_TOKEN"]
    resp = requests.get(
        f"{API_BASE}/competitions/{COMPETITION}/matches",
        headers={"X-Auth-Token": token},
        params={"dateFrom": date_from, "dateTo": date_to},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def kickoff_uk(match: dict) -> datetime:
    utc = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00"))
    return utc.astimezone(UK_TZ)


def stage_label(match: dict) -> str:
    stage = (match.get("stage") or "").replace("_", " ").title()
    group = match.get("group")
    if group:
        return group.replace("GROUP_", "Group ")
    return stage


def format_fixture(match: dict) -> str:
    ko = kickoff_uk(match)
    return (
        f"`{ko:%H:%M}`  {team_label(match['homeTeam'])} vs "
        f"{team_label(match['awayTeam'])}  _({stage_label(match)})_"
    )


def format_result(match: dict) -> str:
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    home_goals, away_goals = ft.get("home"), ft.get("away")
    line = (
        f"{team_label(match['homeTeam'])} *{home_goals} - {away_goals}* "
        f"{team_label(match['awayTeam'])}"
    )
    # Note penalties if the match went to a shootout
    if score.get("duration") == "PENALTY_SHOOTOUT":
        pens = score.get("penalties", {})
        line += f"  _(pens {pens.get('home')}-{pens.get('away')})_"
    return f"{line}  _({stage_label(match)})_"


def build_message(today_fixtures: list[dict], yesterday_results: list[dict],
                  today: datetime, yesterday: datetime) -> dict:
    blocks = [{
        "type": "header",
        "text": {"type": "plain_text",
                 "text": f"🏆 World Cup Daily — {today:%A %d %B}"},
    }]

    blocks.append({"type": "section", "text": {
        "type": "mrkdwn", "text": f"*⚽ Today's fixtures* (kick-off times UK)"}})
    if today_fixtures:
        lines = "\n".join(format_fixture(m) for m in today_fixtures)
    else:
        lines = "_No matches scheduled today._"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": lines}})

    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {
        "type": "mrkdwn",
        "text": f"*📋 Yesterday's results* ({yesterday:%A %d %B})"}})
    if yesterday_results:
        lines = "\n".join(format_result(m) for m in yesterday_results)
    else:
        lines = "_No matches were played yesterday._"
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": lines}})

    return {"blocks": blocks, "text": "World Cup daily update"}


def main() -> None:
    now_uk = datetime.now(UK_TZ)
    today_uk = now_uk.date()
    yesterday_uk = today_uk - timedelta(days=1)

    # Fetch a 3-day UTC window around now, then filter by UK-local date.
    # (Matches in North America can cross midnight UK time, so filtering by
    # the API's UTC date alone would mislabel late kick-offs.)
    matches = fetch_matches(
        (yesterday_uk - timedelta(days=1)).isoformat(),
        (today_uk + timedelta(days=1)).isoformat(),
    )

    today_fixtures, yesterday_results = [], []
    for m in matches:
        local_date = kickoff_uk(m).date()
        if local_date == today_uk:
            today_fixtures.append(m)
        elif local_date == yesterday_uk and m.get("status") in (
                "FINISHED", "AWARDED"):
            yesterday_results.append(m)

    today_fixtures.sort(key=kickoff_uk)
    yesterday_results.sort(key=kickoff_uk)

    payload = build_message(today_fixtures, yesterday_results, now_uk,
                            now_uk - timedelta(days=1))

    webhook = os.environ["SLACK_WEBHOOK_URL"]
    resp = requests.post(webhook, json=payload, timeout=30)
    resp.raise_for_status()
    print(f"Posted: {len(today_fixtures)} fixtures, "
          f"{len(yesterday_results)} results.")


if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        sys.exit(f"Missing environment variable: {e}")
    except requests.HTTPError as e:
        sys.exit(f"HTTP error: {e} — {e.response.text[:300]}")
