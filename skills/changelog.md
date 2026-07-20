# Changelog

All notable changes to the VendorBids Competitive Intel Pipeline.

---

## 2026-07-19 — Category-Aware Pipeline

**`1a2a1da`** Make pipeline category-aware for operators and contractors

- Added `prompts/operator_analysis.md` — LLM prompt framed as buyer intelligence (growth signals, vendor needs) instead of competitive threat
- Added `prompts/contractor_analysis.md` — LLM prompt framed as vendor intelligence (how they market to PMs, pricing signals)
- `analyze.py` selects prompt by category field, defaults to competitor prompt for backwards compatibility
- `digest.py` builds separate Slack messages per category: "Competitor creative watch", "Operator intelligence", "Vendor intelligence"
- `main.py` segments analyses by category before passing to digest builder
- Added `--category` CLI flag to filter pipeline to one category (`competitor`, `operator`, or `contractor`)
- Updated `weekly-digest.yml` with 4 new Slack posting steps for operator and vendor intel threads
- Added `skills/category-aware-pipeline.md` plan documenting the problems and implementation
- 6 new tests (99 total, all passing)

---

## 2026-07-18 — Operator & Contractor Monitoring Targets

**`f3b9793`** Add operator and contractor monitoring targets to competitors.yaml

- Added 8 multifamily operators with verified Facebook page IDs: MAA Communities, Bozzuto, Cushman & Wakefield, Morgan Properties, Brookfield Properties, Equity Residential, Cortland Living, RPM Living
- Added 7 national contractors with verified Facebook page IDs: ABM Industries, TruGreen, Cintas Corporation, Terminix, Stanley Steemer, Mr. Rooter Plumbing, Davey Tree
- Introduced `category` field (`competitor`, `operator`, `contractor`) to `competitors.yaml`
- Documented 7 operators and 4 contractors without Facebook ad presence (Greystar, BrightView, etc.)
- Updated test to expect 19 total entries with category validation

**`3fe01a4`** Add operator research skill

- `skills/operator-research.md` — full operator watchlist, selection criteria (unit count, growth trajectory, tech posture), community-vs-corporate Facebook page pitfalls, signals to watch

**`26d5f70`** Add contractor research skill

- `skills/contractor-research.md` — trade coverage map with gap analysis (HVAC, electrical, roofing, painting gaps), franchise-vs-corporate scraping pitfalls, signals for Vendor Connect GTM

---

## 2026-07-18 — Competitor Research & Config Verification

**`83d5378`** Add competitor research skill

- `skills/competitor-research.md` — documents full competitive landscape, 4 methods for getting Facebook page IDs, threat level definitions, when to re-run research

**`9e39914`** Update competitors.yaml with verified Facebook Page IDs

- Replaced 9 placeholder competitors with 4 verified active Facebook advertisers: ServiceTitan, Procore Technologies, AppFolio, Property Meld
- Documented 10 enterprise B2B competitors (NetVendor, Revyse, VendorPM, Yardi, RealPage, etc.) that don't run Facebook ads
- Key finding: most direct VendorBids competitors use ABM/events marketing, not paid social

---

## 2026-07-17 — Pipeline Reliability & Logging

**`4130434`** Fix dry-run to work without META_ACCESS_TOKEN

- `main.py` catches ValueError from `fetch_ads()` when token is missing in dry-run mode, falls back to empty ad set
- Same pattern for contractor discovery in dry-run
- Fixes regression where dry-run required a real API token

**`5a9630f`** Add logging to diff.py and improve error tracing

- `diff.py` had zero logging — added debug logs for diff computation, reactivation detection at INFO, snapshot saves
- `discover.py` — added `exc_info=True` to error handlers, debug log for store counts
- `enrich.py` — added `exc_info=True` to error handlers, per-contractor progress logging

**`4d1764f`** Consolidate implementation skill docs

- Merged 6 separate skill files into single `skills/pipeline-architecture.md` reference

---

## 2026-07-16 — Test Coverage & Bug Fixes

**`8447335`** Expand test coverage (76 to 93 tests)

- Edge case tests for Unicode creative bodies, very long text, API param verification
- FTS search and delete trigger tests
- Database migration idempotency tests

**`1c4d54d`** Fix workflow, schema migration, validation, and unused imports

- Fixed GitHub Actions workflow syntax
- Added schema migration for `contractors_found` column
- Fixed validation edge cases in `build_analysis_result`

---

## 2026-07-15 — Contractor Lead Discovery

**`e51c7ec`** Add contractor lead discovery and competitor creative analysis

- `src/discover.py` — searches Meta Ads Library by trade keywords, extracts contractor pages, deduplicates, stores in SQLite
- `src/enrich.py` — LLM enrichment of discovered contractors (relevance scoring, multifamily signal, company size)
- `src/analyze.py` — LLM-powered weekly competitive analysis with structured JSON output
- `src/digest.py` — Slack Block Kit payload builder for both competitor watch and contractor leads
- `config/trades.yaml` — trade categories with search terms for contractor discovery
- Full test suite for all new modules

---

## 2026-07-14 — Foundation

**`47d8b92` - `d514b62`** Initial pipeline architecture

- `src/extract.py` — Meta Ads Library API client with pagination and rate limiting
- `src/diff.py` — ad state diffing (new, ended, reactivated) against SQLite
- `src/db.py` — SQLite schema with FTS5 full-text search, migrations
- `src/main.py` — CLI entry point with `--dry-run`, `--backfill`, `--competitor` flags
- `.github/workflows/weekly-digest.yml` — Monday 3pm UTC cron with Slack integration
- `.github/workflows/tests.yml` — CI test runner
- Architecture skill docs for state persistence, SQLite FTS, logging
