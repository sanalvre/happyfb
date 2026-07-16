# happyfb

VendorBids competitive intelligence pipeline for HappyCo. Weekly automated digest of competitor Meta ad activity, posted to Slack.

**Status:** Code complete, awaiting API keys. 40 tests passing.

## Quick start

1. Read the [Setup Guide](skills/setup-guide.md) for API keys and Slack configuration
2. Update `config/competitors.yaml` with real Facebook Page IDs
3. Add secrets to GitHub repo settings
4. Run the backfill workflow, then the weekly digest workflow
5. Monday 8am PT, digests arrive automatically in `#vb-competitive-intel`

## How it works

```
GitHub Actions (Monday 8am PT)
  -> extract.py (Meta Ads Library API)
  -> diff.py (SQLite: what's new, what ended)
  -> analyze.py (Claude Haiku: themes, threat score)
  -> digest.py (Slack Block Kit: threaded messages)
```

Cost: ~$0.50/month (LLM only; everything else is free-tier).

## Structure

```
happyfb/
├── .github/workflows/
│   ├── weekly-digest.yml          # Monday cron + manual trigger
│   ├── backfill.yml               # Historical ad seed (manual)
│   └── tests.yml                  # CI: pytest on push/PR
├── src/
│   ├── extract.py                 # Meta Ads Library API client
│   ├── diff.py                    # Change detection against SQLite
│   ├── analyze.py                 # LLM theme/threat analysis
│   ├── digest.py                  # Slack Block Kit builder
│   ├── storage.py                 # GitHub Releases state sync
│   ├── db.py                      # SQLite connection helper
│   └── main.py                    # Pipeline orchestrator + CLI
├── tests/                         # 40 tests, no API keys needed
├── config/competitors.yaml        # Competitor list + page IDs
├── prompts/weekly_analysis.md     # LLM prompt template
├── skills/
│   ├── README.md                  # Original plan brainstorm
│   ├── revised-plan.md            # Research-validated revision
│   ├── competitive-intel-pipeline.md  # Implementation-ready plan
│   ├── implementation-log.md      # Build log + design decisions
│   └── setup-guide.md            # API keys + Slack setup steps
├── schema.sql                     # SQLite schema (ads, snapshots, FTS5)
├── requirements.txt
└── .env.example
```

## Running tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## CLI usage

```bash
# Dry run (no LLM, no Slack)
python -m src.main --dry-run

# Single competitor
python -m src.main --competitor NetVendor --dry-run

# Backfill 90 days of history
python -m src.main --backfill 90
```
