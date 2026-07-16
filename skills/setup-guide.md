# Setup Guide: API Keys and Slack Configuration

Step-by-step guide to get the pipeline running with real data.

---

## Step 1: Validate Meta Ads Library API (do this first)

Before any other setup, confirm the API returns your competitors' ads.

### Get API access

1. Go to [facebook.com/ID](https://facebook.com/ID) and verify your identity (1-3 business days)
2. Go to [developers.facebook.com](https://developers.facebook.com) > My Apps > Create App
3. Select "Other" use case, then "Business" app type
4. In the app dashboard, click "Add Product" > find "Ad Library API" > click "Set Up"
5. Go to Tools > Graph API Explorer
6. Select your app, click "Generate Access Token"
7. Add permission: `ads_read`

### Run the validation test

Open a Python shell and run:

```python
import requests

TOKEN = "paste_your_token_here"
PAGE_ID = "paste_a_competitor_page_id_here"

r = requests.get(
    "https://graph.facebook.com/v21.0/ads_archive",
    params={
        "access_token": TOKEN,
        "search_page_ids": PAGE_ID,
        "ad_reached_countries": "US",
        "ad_active_status": "ALL",
        "fields": "id,ad_creative_bodies,page_name",
        "limit": 5,
    },
)
data = r.json()
print(f"Found {len(data.get('data', []))} ads")
for ad in data.get("data", []):
    print(f"  - {ad.get('ad_creative_bodies', ['(no body)'])[0][:80]}")
```

**If ads come back**: Proceed with the rest of this guide.
**If empty or error**: The API may not serve US-only commercial ads for this competitor. See the Apify fallback section in `revised-plan.md`.

### Get a non-expiring token (for production)

Short-lived tokens from Graph API Explorer expire in ~1 hour. For production:

1. Go to [business.facebook.com](https://business.facebook.com) > Business Settings
2. Users > System Users > Add
3. Create a system user, assign it to your app with `ads_read` permission
4. Click "Generate New Token" > select your app > check `ads_read`
5. This token does not expire

---

## Step 2: OpenRouter API key

1. Go to [openrouter.ai](https://openrouter.ai) and sign up
2. Go to Settings > API Keys > Create Key
3. Add a few dollars of credits ($5 is enough for months of use at ~$0.50/month)
4. Copy the key (starts with `sk-or-v1-`)

---

## Step 3: Slack bot setup

### Option A: Create a new Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) > Create New App > From Scratch
2. Name it "Competitive Intel Bot" (or whatever you prefer)
3. Select the HappyCo workspace
4. Go to OAuth & Permissions > Scopes > Bot Token Scopes > Add `chat:write`
5. Click "Install to Workspace" at the top of the page
6. Copy the Bot User OAuth Token (starts with `xoxb-`)

### Option B: Use your existing GitHub Actions Slack integration

If you already have a Slack App for GitHub Actions:

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Select your existing app
3. Go to OAuth & Permissions > Scopes > Bot Token Scopes
4. Add `chat:write` if not already present
5. Reinstall the app if scopes changed
6. Copy the Bot User OAuth Token

### Create the channel

1. In Slack, create `#vb-competitive-intel` (or your preferred name)
2. Invite the bot: type `/invite @YourBotName` in the channel
3. Get the channel ID: right-click the channel name > "View channel details" > scroll to the bottom > copy the ID (starts with `C`)

---

## Step 4: Add secrets to GitHub

Go to your repo ([github.com/sanalvre/happyfb](https://github.com/sanalvre/happyfb)) > Settings > Secrets and variables > Actions > New repository secret

Add these four secrets:

| Name | Value |
|------|-------|
| `META_ACCESS_TOKEN` | Your Meta System User token |
| `OPENROUTER_KEY` | Your OpenRouter API key (`sk-or-v1-...`) |
| `SLACK_BOT_TOKEN` | Your Slack bot token (`xoxb-...`) |
| `SLACK_CHANNEL_ID` | Your channel ID (`C0123...`) |

---

## Step 5: Update competitor page IDs

Edit `config/competitors.yaml` and replace each `"REPLACE"` with the actual Facebook Page ID.

**How to find a page ID:**

1. Go to the competitor's Facebook page
2. Right-click > View Page Source
3. Search for `"pageID"` in the source
4. Copy the number

Or use the Ad Library:
1. Go to [facebook.com/ads/library](https://facebook.com/ads/library)
2. Search for the competitor name
3. Click through to their ads
4. Copy `view_all_page_id` from the URL

---

## Step 6: First run

### Run backfill (seeds 90 days of history)

1. Go to repo > Actions > "Backfill historical ads"
2. Click "Run workflow"
3. Enter `90` for days
4. Click "Run workflow"
5. Watch the logs to confirm ads are being fetched

### Run a manual digest

1. Go to repo > Actions > "Weekly competitive digest"
2. Click "Run workflow"
3. Watch the logs
4. Check `#vb-competitive-intel` for the digest message

### Enable the cron

The cron is already configured in `weekly-digest.yml` to run Monday at 8am PT. Once the manual run looks good, the weekly schedule takes over automatically.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `META_ACCESS_TOKEN` expired | You're using a short-lived token. Create a System User token (Step 1) |
| Empty API results | API may not serve US-only commercial ads. Check the validation test output |
| Slack post fails with `channel_not_found` | Bot isn't in the channel. Run `/invite @BotName` |
| Slack post fails with `not_in_channel` | Same fix: `/invite @BotName` |
| `no such module: fts5` on GitHub Actions | `pysqlite3-binary` should handle this. Check it's in `requirements.txt` |
| Workflow timeout (>30 min) | A competitor has too many ads. Add `--competitor` filter to debug |
