# World Cup Slack Bot 🏆

Posts a daily message to Slack with today's World Cup fixtures (UK kick-off
times) and yesterday's results.

## Setup (about 10 minutes)

### 1. Get a free football data API token
1. Register at https://www.football-data.org/client/register
2. You'll receive an API token by email. The free tier includes the FIFA
   World Cup.

### 2. Create a Slack incoming webhook
1. Go to https://api.slack.com/apps and click **Create New App** → "From scratch".
2. Name it (e.g. "World Cup Bot") and pick your workspace.
3. In the app settings, open **Incoming Webhooks**, toggle it on, then click
   **Add New Webhook to Workspace** and choose the channel (or your own DMs).
4. Copy the webhook URL (starts with `https://hooks.slack.com/services/...`).

### 3. Put this in a GitHub repo
1. Create a new (private is fine) repository and add these files, keeping the
   `.github/workflows/worldcup.yml` path intact.
2. In the repo, go to **Settings → Secrets and variables → Actions** and add
   two repository secrets:
   - `FOOTBALL_DATA_TOKEN` — your football-data.org token
   - `SLACK_WEBHOOK_URL` — your Slack webhook URL

### 4. Test it
Go to the **Actions** tab, select "World Cup daily Slack update", and click
**Run workflow**. You should see the message appear in Slack within a minute.

From then on it runs automatically every morning at 8am UK time.

## Run locally instead (optional)

```bash
pip install requests
export FOOTBALL_DATA_TOKEN="your-token"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python worldcup_bot.py
```

## Notes
- Kick-off times are converted to Europe/London, so late-night games in North
  America are attributed to the correct UK calendar day.
- The schedule is `0 7 * * *` (07:00 UTC = 8am BST). If you want a different
  time, edit the cron line in `.github/workflows/worldcup.yml`.
- GitHub's cron can occasionally run a few minutes late at busy times — normal
  behaviour, nothing to fix.
