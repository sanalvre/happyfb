# Implementation Log: Competitive Intel Pipeline

**Date:** 2026-07-15
**Status:** Code complete, awaiting API keys for live testing

---

## What was built

A fully functional competitive ad monitoring pipeline that runs on GitHub Actions and posts weekly digests to Slack. All external API calls are abstracted behind modules that can be tested with mocks.

### Source modules

| File | Purpose | External dependency |
|------|---------|-------------------|
| `src/extract.py` | Fetches ads from Meta Ads Library API | Meta API (needs `META_ACCESS_TOKEN`) |
| `src/diff.py` | Compares fresh ads against SQLite state, detects new/ended/changed | None (pure logic) |
| `src/analyze.py` | Sends diffs to Claude Haiku for theme/threat analysis | OpenRouter (needs `OPENROUTER_KEY`) |
| `src/digest.py` | Builds Slack Block Kit JSON files (parent + threaded replies) | None (pure logic) |
| `src/storage.py` | Syncs SQLite state via GitHub Releases | `gh` CLI (provided by GitHub Actions) |
| `src/db.py` | Database connection helper, falls back from pysqlite3 to sqlite3 | None |
| `src/main.py` | CLI entrypoint, orchestrates all stages | All of the above |

### Key design decisions

1. **pysqlite3 fallback**: `src/db.py` tries `import pysqlite3` first (for GitHub Actions where FTS5 is broken), falls back to standard `sqlite3` (works on Windows/Mac local dev). This means the same code runs everywhere.

2. **Digest writes files, not HTTP**: `src/digest.py` writes JSON files to `state/slack_payloads/`. The GitHub Actions workflow reads these files and posts them. This separation means digest logic is fully testable without Slack credentials.

3. **`VACUUM INTO` for uploads**: `src/storage.py` uses `VACUUM INTO` to produce a clean single-file database before uploading, avoiding WAL/SHM split-file issues.

4. **Concurrency group**: The workflow uses `concurrency: { group: competitive-intel, cancel-in-progress: false }` to prevent overlapping runs from corrupting state.

5. **Threaded Slack messages**: Parent message goes to channel, per-competitor details post as thread replies. Avoids the 50-block / ~13KB Block Kit limit entirely.

### Test coverage

**40 tests, all passing, no API keys required.**

| Test file | Count | What it covers |
|-----------|-------|---------------|
| `test_extract.py` | 7 | Ad normalization (full/sparse/empty), API pagination, rate limit backoff, missing token |
| `test_diff.py` | 8 | New ad detection, ended ad detection, no-change runs, separate competitors, snapshot save/upsert, prior themes |
| `test_analyze.py` | 5 | Missing key validation, LLM response parsing, prompt template population, result merging, defaults |
| `test_digest.py` | 8 | Skip flag on no activity, file generation, parent/reply structure, alert emoji thresholds, threat bar rendering, optional block omission |
| `test_integration.py` | 12 | Full pipeline dry run, pipeline with analysis, partial failure, state persistence across runs, pipeline run logging, config loading, FTS5 search/delete triggers |

### GitHub Actions workflows

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `weekly-digest.yml` | Monday 8am PT cron + manual | Full pipeline: pull state, extract, diff, analyze, digest, post to Slack, push state |
| `backfill.yml` | Manual only | Seed historical ads for a given number of days (no LLM analysis) |
| `tests.yml` | Push to main + PRs | Runs pytest suite |

---

## What's needed to go live

### 1. Meta Ads Library API access

- Verify identity at facebook.com/ID (1-3 days)
- Create Meta Developer App
- Add "Ad Library API" product
- Create System User token (non-expiring) with `ads_read` scope
- Store as `META_ACCESS_TOKEN` in repo secrets

**Critical validation**: Run a test query against a known competitor to confirm the API returns their US commercial ads. If it doesn't (API limitation for US-only campaigns), swap `extract.py` to use Apify.

### 2. OpenRouter API key

- Sign up at openrouter.ai
- Generate API key
- Store as `OPENROUTER_KEY` in repo secrets

### 3. Slack bot setup

- Create Slack App at api.slack.com/apps (or use existing)
- Add `chat:write` OAuth scope
- Install to workspace
- Store bot token as `SLACK_BOT_TOKEN` in repo secrets
- Create `#vb-competitive-intel` channel
- Invite bot to channel (`/invite @BotName`)
- Store channel ID as `SLACK_CHANNEL_ID` in repo secrets

### 4. Competitor page IDs

- Update `config/competitors.yaml` with actual Facebook Page IDs
- For each competitor: go to their Facebook page > View Page Source > search `"pageID"`

### 5. First run sequence

```bash
# 1. Run backfill to seed 90 days of history
# (via GitHub Actions > backfill.yml > Run workflow > days: 90)

# 2. Run a manual digest to verify Slack posting
# (via GitHub Actions > weekly-digest.yml > Run workflow)

# 3. If everything looks good, the Monday cron handles the rest
```

---

## File tree (final)

```
happyfb/
├── .github/workflows/
│   ├── weekly-digest.yml
│   ├── backfill.yml
│   └── tests.yml
├── config/
│   └── competitors.yaml
├── prompts/
│   └── weekly_analysis.md
├── skills/
│   ├── README.md                       # Original plan
│   ├── revised-plan.md                 # Research-validated revision
│   ├── competitive-intel-pipeline.md   # Implementation-ready plan
│   └── implementation-log.md           # This file
├── src/
│   ├── __init__.py
│   ├── db.py
│   ├── extract.py
│   ├── diff.py
│   ├── analyze.py
│   ├── digest.py
│   ├── storage.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_extract.py
│   ├── test_diff.py
│   ├── test_analyze.py
│   ├── test_digest.py
│   └── test_integration.py
├── schema.sql
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
