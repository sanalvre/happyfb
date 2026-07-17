# VendorBids Competitive Intel & Contractor Lead Pipeline

**Status:** Code complete, awaiting API keys for live testing
**Cost:** ~$2-5/month (LLM analysis only; everything else is free-tier)
**Tests:** 93 passing, no API keys required

---

## What it does

A two-track weekly pipeline running on GitHub Actions:

**Track 1 (Primary): Contractor Lead Discovery** — Finds small-to-midsize contractors (HVAC, plumbing, electrical, etc.) via Meta Ads Library keyword searches, enriches with LLM scoring and Facebook Page contact info, and delivers leads to Slack for VendorBids Vendor Connect outreach.

**Track 2 (Secondary): Competitor Creative Watch** — Monitors competitor Facebook ads, analyzes creative quality and virality with Claude Haiku, and posts highlights to Slack so marketing can mirror top-performing campaigns.

---

## Architecture

```
Monday 8am PT (GitHub Actions cron)
  |
  v
Pull SQLite from GitHub Releases
  |
  +-- Track 1: Contractor Leads --------+-- Track 2: Competitor Creatives
  |   1. discover.py: keyword search    |   1. extract.py: fetch by page_id
  |   2. enrich.py: LLM + contact info  |   2. diff.py: new/ended detection
  |   3. Store in contractors table      |   3. analyze.py: LLM creative analysis
  |                                      |   4. Store snapshots
  +--------------------------------------+
  |
  v
digest.py: Build Slack Block Kit payloads
  - Leads section (parent + per-trade thread replies)
  - Creative watch section (parent + per-competitor thread replies)
  |
  v
Push SQLite to GitHub Releases
Post payloads to Slack
Upload logs as artifact (14-day retention)
```

### External dependencies

| Service | Used for | Cost |
|---------|----------|------|
| Meta Ads Library API | Ad search (keywords + page_id) | Free |
| Facebook Graph API | Page contact info (website/phone/email) | Free |
| OpenRouter (Claude Haiku 4.5) | LLM analysis and enrichment | ~$2-5/mo |
| GitHub Actions | Weekly cron runner | Free tier |
| GitHub Releases | SQLite state persistence | Free |
| Slack API | Digest delivery | Free tier |

---

## Source modules

| File | Purpose | External dependency |
|------|---------|-------------------|
| `src/main.py` | CLI entrypoint, two-track orchestration | All below |
| `src/extract.py` | Fetches ads from Meta Ads Library by page_id | Meta API |
| `src/discover.py` | Searches Ads Library by trade keywords, deduplicates contractors | Meta API |
| `src/enrich.py` | LLM scoring + Facebook Page contact info extraction | OpenRouter + Graph API |
| `src/diff.py` | Compares fresh ads against SQLite state | None (pure logic) |
| `src/analyze.py` | Creative quality + threat analysis via Claude Haiku | OpenRouter |
| `src/digest.py` | Builds Slack Block Kit JSON (leads + creatives sections) | None (pure logic) |
| `src/storage.py` | Syncs SQLite via GitHub Releases (`VACUUM INTO` for clean uploads) | `gh` CLI |
| `src/db.py` | DB connection + pysqlite3 fallback + schema migrations | None |
| `src/logging_config.py` | Dual-output logging (console INFO + file DEBUG) | None |

---

## Key design decisions

### 1. Two-track pipeline with `--skip-leads` flag

`run_pipeline()` accepts `skip_leads=True` to skip contractor discovery. Used in tests and when only competitor tracking is needed. Both tracks share the same SQLite database and GitHub Releases state cycle.

### 2. LLM output type safety

All LLM responses go through validation before storage:
- `threat_assessment` / `relevance_score` / `creative_quality`: coerced via `int(float(...))`, clamped to 1-5
- `engagement_signal`: validated against `("low", "medium", "high")`, defaults to `"low"`
- `company_size_signal`: validated against `("small", "midsize", "large", "unknown")`, defaults to `"unknown"`
- `themes`: each element coerced to string via `str()`
- Failed enrichment still appends unenriched contractor (no data loss)

### 3. pysqlite3 fallback for FTS5

GitHub Actions runners have a known bug (actions/runner-images#12576) where FTS5 is disabled. `src/db.py` tries `import pysqlite3 as sqlite3` first, falls back to standard `sqlite3` (works on Windows/Mac where FTS5 is enabled by default).

### 4. State persistence via GitHub Releases

`src/storage.py` uses `gh release download/upload` with a `state` tag. `VACUUM INTO` produces a clean single-file database (no WAL/SHM split). Workflow concurrency group prevents overlapping runs from corrupting state. `push()` runs on `if: always()` so even failed runs preserve extract/diff work.

### 5. Threaded Slack messages

Digest writes JSON files to `state/slack_payloads/`. The workflow posts them. Each section (leads, creatives) gets its own parent message with per-trade or per-competitor thread replies. Avoids Block Kit's 50-block / ~13KB limit entirely.

### 6. Dual-output logging

Console (stdout) gets clean INFO messages for GitHub Actions step logs. File (`state/logs/pipeline.log`) gets timestamped DEBUG output uploaded as a 14-day artifact. Each run is marked with `--- Run {run_id} started ---` for easy searching. Error logs include full stack traces via `exc_info=True`.

### 7. FTS5 content-sync triggers

The `ads_fts` virtual table uses `content='ads'` mode (stores no data, just index). Three triggers (`ads_ai`, `ads_ad`, `ads_au`) keep it in sync. FTS5 deletes are special inserts with the table name as first column value — a quirk of the content-sync protocol.

### 8. Schema migrations

`db.py` includes `_run_migrations()` that checks `PRAGMA table_info` and adds missing columns (e.g., `contractors_found` to `pipeline_runs`). Runs on every `init_db()` call. Idempotent.

---

## Database schema

### `ads` table — competitor ad tracking

```sql
CREATE TABLE ads (
  ad_id TEXT PRIMARY KEY,
  competitor TEXT NOT NULL,
  first_seen DATE NOT NULL, last_seen DATE NOT NULL,
  status TEXT NOT NULL,  -- 'active' | 'ended'
  creative_body TEXT, creative_title TEXT, cta_text TEXT,
  snapshot_url TEXT, platforms TEXT,  -- JSON array
  start_date DATE, end_date DATE,
  raw_json TEXT NOT NULL
);
```

### `contractors` table — discovered leads

```sql
CREATE TABLE contractors (
  page_id TEXT PRIMARY KEY,
  page_name TEXT NOT NULL, trade TEXT NOT NULL,
  first_seen DATE NOT NULL, last_seen DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',  -- 'new' | 'contacted' | 'qualified' | 'skip'
  website TEXT, phone TEXT, email TEXT,
  city TEXT, state TEXT,
  ad_count INTEGER DEFAULT 0,
  relevance_score INTEGER,  -- 1-5, LLM-assessed
  serves_multifamily BOOLEAN,
  company_size_signal TEXT,  -- 'small' | 'midsize' | 'large' | 'unknown'
  sample_ad_text TEXT, notes TEXT, raw_json TEXT
);
```

### Supporting tables

- `weekly_snapshots` — per-competitor weekly analysis snapshots (themes, threat score, headline)
- `pipeline_runs` — run metadata (status, counts, timing, `contractors_found`)
- `ads_fts` — FTS5 virtual table for full-text search across ad creatives

---

## Configuration files

- `config/competitors.yaml` — 9 competitors with name, threat_level, page_id, notes
- `config/trades.yaml` — 8 trade categories (HVAC, Plumbing, Electrical, Landscaping, Painting, Roofing, Cleaning, General Maintenance) with 3 search terms each
- `prompts/weekly_analysis.md` — LLM prompt template for competitor analysis (8 output fields including creative_quality, engagement_signal, why_it_works)

---

## GitHub Actions workflows

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| `weekly-digest.yml` | Monday 8am PT cron + manual | Full pipeline: pull state, run both tracks, digest, post to Slack, push state |
| `backfill.yml` | Manual only | Seed historical ads for a given number of days (no LLM analysis) |
| `tests.yml` | Push to main + PRs | Runs pytest suite |

The weekly workflow has conditional steps: `has_leads` and `has_competitors` output variables control which Slack posting steps run.

---

## Test coverage (93 tests)

| Test file | Count | What it covers |
|-----------|-------|---------------|
| `test_extract.py` | 10 | Ad normalization, pagination, rate limiting, HTTP errors, API params, unicode/long text |
| `test_diff.py` | 9 | New/ended detection, reactivation, empty response, schema consistency, snapshots |
| `test_analyze.py` | 12 | LLM parsing, type coercion/clamping, invalid fields, markdown-fenced JSON, HTTP errors |
| `test_digest.py` | 8 | Skip flag, file generation, parent/reply structure, alert thresholds, contractor digest |
| `test_discover.py` | 14 | Extraction, dedup, search, cross-run dedup, failure handling, config loading |
| `test_enrich.py` | 13 | LLM enrichment, contact fetching, batch enrichment, score clamping, validation |
| `test_integration.py` | 27 | Full pipeline flows, state persistence, DB migration, FTS5 triggers |

---

## What's needed to go live

### 1. Meta Ads Library API access
- Verify identity at facebook.com/ID (1-3 days)
- Create Meta Developer App, add "Ad Library API" product
- Create System User token (non-expiring) with `ads_read` scope
- Store as `META_ACCESS_TOKEN` in repo secrets
- **Critical**: Run a test query against a known competitor. If US-only commercial ads aren't returned, swap `extract.py` to use Apify (~$50-80/month instead of free).

### 2. OpenRouter API key
- Sign up at openrouter.ai, generate key
- Store as `OPENROUTER_KEY` in repo secrets

### 3. Slack bot setup
- Create Slack App with `chat:write` scope, install to workspace
- Store bot token as `SLACK_BOT_TOKEN`, channel ID as `SLACK_CHANNEL_ID`
- Create `#vb-competitive-intel` channel, invite bot

### 4. Competitor page IDs
- Update `config/competitors.yaml` with actual Facebook Page IDs
- For each: View Page Source > search `"pageID"`

### 5. First run sequence
1. Run backfill workflow (90 days) to seed history
2. Run manual weekly digest to verify Slack posting
3. Monday cron handles the rest

---

## File tree

```
happyfb/
├── .github/workflows/
│   ├── weekly-digest.yml
│   ├── backfill.yml
│   └── tests.yml
├── config/
│   ├── competitors.yaml
│   └── trades.yaml
├── prompts/
│   └── weekly_analysis.md
├── src/
│   ├── __init__.py
│   ├── db.py
│   ├── logging_config.py
│   ├── extract.py
│   ├── discover.py
│   ├── enrich.py
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
│   ├── test_discover.py
│   ├── test_enrich.py
│   └── test_integration.py
├── schema.sql
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
