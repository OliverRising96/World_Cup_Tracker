"""
World Cup Slack Bot
-------------------
Runs at midday (UK) and posts to Slack:
  * Results from the previous 24 hours (so last night's late kick-offs are
    reported with their final scores, not listed as "today's fixtures").
  * Fixtures kicking off in the next 24 hours.

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
WINDOW = timedelta(hours=24)

FLAGS = {
    "Argentina": "\U0001F1E6\U0001F1F7", "Australia": "\U0001F1E6\U0001F1FA",
    "Belgium": "\U0001F1E7\U0001F1EA", "Brazil": "\U0001F1E7\U0001F1F7",
    "Canada": "\U0001F1E8\U0001F1E6", "Colombia": "\U0001F1E8\U0001F1F4",
    "Croatia": "\U0001F1ED\U0001F1F7", "Ecuador": "\U0001F1EA\U0001F1E8",
    "Egypt": "\U0001F1EA\U0001F1EC", "France": "\U0001F1EB\U0001F1F7",
    "Germany": "\U0001F1E9\U0001F1EA", "Ghana": "\U0001F1EC\U0001F1ED",
    "Iran": "\U0001F1EE\U0001F1F7", "Italy": "\U0001F1EE\U0001F1F9",
    "Japan": "\U0001F1EF\U0001F1F5", "Mexico": "\U0001F1F2\U0001F1FD",
    "Morocco": "\U0001F1F2\U0001F1E6", "Netherlands": "\U0001F1F3\U0001F1F1",
    "New Zealand": "\U0001F1F3\U0001F1FF", "Nigeria": "\U0001F1F3\U0001F1EC",
    "Norway": "\U0001F1F3\U0001F1F4", "Panama": "\U0001F1F5\U0001F1E6",
    "Paraguay": "\U0001F1F5\U0001F1FE", "Portugal": "\U0001F1F5\U0001F1F9",
    "Qatar": "\U0001F1F6\U0001F1E6", "Saudi Arabia": "\U0001F1F8\U0001F1E6",
    "Senegal": "\U0001F1F8\U0001F1F3", "South Korea": "\U0001F1F0\U0001F1F7",
    "Spain": "\U0001F1EA\U0001F1F8", "Switzerland": "\U0001F1E8\U0001F1ED",
    "Tunisia": "\U0001F1F9\U0001F1F3", "Uruguay": "\U0001F1FA\U0001F1FE",
    "USA": "\U0001F1FA\U0001F1F8", "United States": "\U0001F1FA\U0001F1F8",
    "Uzbekistan": "\U0001F1FA\U0001F1FF", "Ivory Coast": "\U0001F1E8\U0001F1EE",
    "Jordan": "\U0001F1EF\U0001F1F4", "Cape Verde": "\U0001F1E8\U0001F1FB",
    "South Africa": "\U0001F1FF\U0001F1E6", "Algeria": "\U0001F1E9\U0001F1FF",
    "Austria": "\U0001F1E6\U0001F1F9", "Denmark": "\U0001F1E9\U0001F1F0",
    "Haiti": "\U0001F1ED\U0001F1F9", "Curacao": "\U0001F1E8\U0001F1FC",
    "England": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "Scotland": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
    "Wales": "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F",
}


def flag(team_name: str) -> str:
    return FLAGS.get(team_name, "\u26BD")


def team_label(team: dict) -> str:
    name = team.get("name") or "TBD"
    return f"{flag(name)} {name}"


def fetch_matches(date_from: str, date_to: str) -> list:
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
    group = match.get("group")
    if group:
        return group.replace("GROUP_", "Group ")
    return (match.get("stage") or "").replace("_", " ").title()


def when_label(match: dict) -> str:
    """Day-of-week + time, e.g. 'Sat 19:00' - needed because a 24h window
    can straddle two calendar days."""
    return f"{kickoff_uk(match):%a %H:%M}"


def format_fixture(match: dict) -> str:
    return (
        f"`{when_label(match)}`  {team_label(match['homeTeam'])} vs "
        f"{team_label(match['awayTeam'])}  _({stage_label(match)})_"
    )


def format_result(match: dict) -> str:
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    line = (
        f"`{when_label(match)}`  {team_label(match['homeTeam'])} "
        f"*{ft.get('home')} - {ft.get('away')}* {team_label(match['awayTeam'])}"
    )
    if score.get("duration") == "PENALTY_SHOOTOUT":
        pens = score.get("penalties", {})
        line += f"  _(pens {pens.get('home')}-{pens.get('away')})_"
    return f"{line}  _({stage_label(match)})_"


def format_live(match: dict) -> str:
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    h, a = ft.get("home") or 0, ft.get("away") or 0
    return (
        f"\U0001F534 LIVE  {team_label(match['homeTeam'])} *{h} - {a}* "
        f"{team_label(match['awayTeam'])}  _({stage_label(match)})_"
    )


def section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def build_message(upcoming, results, live, now_uk) -> dict:
    blocks = [{
        "type": "header",
        "text": {"type": "plain_text",
                 "text": f"\U0001F3C6 World Cup - {now_uk:%A %d %B}, {now_uk:%H:%M}"},
    }]

    blocks.append(section("*\U0001F4CB Results - last 24 hours*"))
    if results:
        blocks.append(section("\n".join(format_result(m) for m in results)))
    else:
        blocks.append(section("_No completed matches in the last 24 hours._"))

    if live:
        blocks.append(section("\n".join(format_live(m) for m in live)))

    blocks.append({"type": "divider"})
    blocks.append(section("*\u26BD Upcoming - next 24 hours* (kick-off times UK)"))
    if upcoming:
        blocks.append(section("\n".join(format_fixture(m) for m in upcoming)))
    else:
        blocks.append(section("_No matches kicking off in the next 24 hours._"))

    return {"blocks": blocks, "text": "World Cup update"}


def main() -> None:
    now_uk = datetime.now(UK_TZ)
    window_start = now_uk - WINDOW
    window_end = now_uk + WINDOW

    # Fetch a generous UTC window (now-2d .. now+2d), then filter precisely by
    # actual kick-off time so the rolling 24h windows are exact.
    matches = fetch_matches(
        (now_uk - timedelta(days=2)).date().isoformat(),
        (now_uk + timedelta(days=2)).date().isoformat(),
    )

    upcoming, results, live = [], [], []
    for m in matches:
        ko = kickoff_uk(m)
        status = m.get("status")
        if window_start <= ko <= now_uk:
            # Kicked off in the past 24h
            if status in ("FINISHED", "AWARDED"):
                results.append(m)
            elif status in ("IN_PLAY", "PAUSED"):
                live.append(m)
        elif now_uk < ko <= window_end:
            # Kicks off in the next 24h
            upcoming.append(m)

    results.sort(key=kickoff_uk)
    live.sort(key=kickoff_uk)
    upcoming.sort(key=kickoff_uk)

    payload = build_message(upcoming, results, live, now_uk)

    webhook = os.environ["SLACK_WEBHOOK_URL"]
    resp = requests.post(webhook, json=payload, timeout=30)
    resp.raise_for_status()
    print(f"Posted: {len(results)} results, {len(live)} live, "
          f"{len(upcoming)} upcoming.")


if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        sys.exit(f"Missing environment variable: {e}")
    except requests.HTTPError as e:
        sys.exit(f"HTTP error: {e} - {e.response.text[:300]}")
