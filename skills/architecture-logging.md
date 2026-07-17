# Architecture: Logging System

How the pipeline's logging works, why it's set up this way, and how to use it for debugging.

---

## Overview

The pipeline uses Python's built-in `logging` module with a **dual-output** design:

- **Console** (stdout): clean, human-readable output at INFO level. No timestamps, no module names. This is what you see in GitHub Actions step logs.
- **File** (`state/logs/pipeline.log`): full diagnostic output at DEBUG level with timestamps, log levels, and module names. This is what you download from GitHub Actions artifacts to debug failures.

All configuration lives in `src/logging_config.py`. Zero external dependencies.

---

## Architecture

```
                    setup_logging(run_id)
                          |
                          v
                   root: "pipeline"
                   level: INFO (default)
                   configurable via LOG_LEVEL env var
                          |
                +---------+---------+
                |                   |
         StreamHandler         FileHandler
         (sys.stdout)        (state/logs/pipeline.log)
         level: INFO           level: DEBUG
         fmt: %(message)s      fmt: timestamp | level | module | message
                |                   |
                v                   v
           GitHub Actions       GitHub Actions Artifact
           step output          (14-day retention)
```

### Module loggers

Every source module creates its own child logger:

```python
from .logging_config import get_logger
log = get_logger("extract")  # creates logger "pipeline.extract"
```

This produces a logger hierarchy under the `pipeline` root:

```
pipeline              (root - configured by setup_logging())
  pipeline.main       (orchestrator)
  pipeline.extract    (Meta API client)
  pipeline.analyze    (LLM calls)
  pipeline.digest     (Slack payload builder)
  pipeline.storage    (GitHub Releases sync)
  pipeline.db         (SQLite connection)
```

All child loggers inherit the root's handlers and level, so `setup_logging()` only needs to be called once.

### Initialization

`setup_logging()` is called in two places:

1. **`run_pipeline()`** — called with the `run_id`, which prints a marker line in the log file: `--- Run a1b2c3d4 started ---`. This makes it easy to find where a specific run begins in a multi-run log file.
2. **`main()`** (CLI entrypoint) — called without a run_id as a fallback for backfill runs and CLI usage.

The function is **idempotent**: if handlers are already attached (e.g., `run_pipeline` called after `main`), it returns immediately without adding duplicate handlers.

---

## What gets logged where

### Console only (INFO)

These are the same messages that `print()` used to produce:

| Module | Message | Example |
|--------|---------|---------|
| main | Competitor processing start | `Processing NetVendor...` |
| main | Fetch count | `  Fetched 12 ads` |
| main | Diff summary | `  New: 3, Ended: 1, Active: 12` |
| main | Threat result | `  Threat: 4/5 - New vendor payments campaign` |
| extract | Fetch complete | `Fetched 12 ads for NetVendor across 1 pages` |
| analyze | LLM request sent | `Sending analysis request for NetVendor (model=anthropic/claude-haiku-4.5)` |
| digest | Activity summary | `Building digest: 3/9 active competitors, max threat 4/5` |
| digest | Files written | `Wrote 4 digest files to state/slack_payloads` |
| storage | State sync status | `State downloaded and verified.` |

### File only (DEBUG)

These are invisible in GitHub Actions step logs but captured in the artifact:

| Module | Message | Why it matters |
|--------|---------|---------------|
| extract | `Fetching page 2 for NetVendor` | See pagination depth |
| extract | `API usage: 45.2%` | Track how close to rate limit |
| extract | `Page 1 returned 500 ads (total: 500)` | Spot truncation |
| analyze | `Prompt length: 4823 chars` | Detect prompt size issues |
| analyze | `LLM response keys: ['headline', 'themes', ...]` | Verify response shape |
| db | `Database initialized at state/ads.db` | Confirm DB path |

### Errors (ERROR — both console and file)

Errors include full stack traces via `exc_info=True`:

| Module | When | What you see |
|--------|------|-------------|
| main | Competitor processing fails | `ERROR processing NetVendor: ConnectionError(...)` + traceback |
| main | Backfill fails | `Backfill error for NetVendor: ...` + traceback |
| storage | Download fails | `gh release download failed: ...` |
| storage | Upload fails | `gh release upload failed: ...` |
| storage | Integrity check fails | `Database integrity check failed: ...` |

### Warnings (WARNING — both console and file)

| Module | When |
|--------|------|
| extract | API usage exceeds 80% and the pipeline is sleeping for 60 seconds |

---

## Configuration

### Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `LOG_LEVEL` | `INFO` | Sets the root logger level. Use `DEBUG` to see debug messages on console too. |
| `LOG_DIR` | `state/logs` | Directory where `pipeline.log` is written. |

### GitHub Actions integration

The weekly digest workflow uploads logs as an artifact:

```yaml
- name: Upload pipeline logs
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: pipeline-logs
    path: state/logs/
    retention-days: 14
    if-no-files-found: ignore
```

`if: always()` ensures logs are captured even on failure. `if-no-files-found: ignore` prevents the step from failing if the log directory doesn't exist (e.g., if the pipeline crashed before writing any logs).

### .gitignore

`state/logs/` is gitignored so local test runs don't accidentally get committed.

---

## Debugging a failed run

1. Go to the failed GitHub Actions run
2. Download the `pipeline-logs` artifact
3. Open `pipeline.log`
4. Search for `--- Run XXXXXXXX started ---` to find the run
5. Look for `ERROR` lines — they include full stack traces
6. Check DEBUG lines above the error for context (which page of API pagination, what the LLM returned, etc.)

### Example log file output

```
2026-07-14 15:00:01 | INFO     | pipeline.main        | --- Run a1b2c3d4 started ---
2026-07-14 15:00:01 | INFO     | pipeline.main        | Processing NetVendor...
2026-07-14 15:00:01 | DEBUG    | pipeline.extract     | Fetching page 1 for NetVendor
2026-07-14 15:00:02 | DEBUG    | pipeline.extract     | API usage: 12.3%
2026-07-14 15:00:02 | DEBUG    | pipeline.extract     | Page 1 returned 8 ads (total: 8)
2026-07-14 15:00:02 | INFO     | pipeline.extract     | Fetched 8 ads for NetVendor across 1 pages
2026-07-14 15:00:02 | INFO     | pipeline.main        |   Fetched 8 ads
2026-07-14 15:00:02 | INFO     | pipeline.main        |   New: 3, Ended: 1, Active: 8
2026-07-14 15:00:02 | INFO     | pipeline.analyze     | Sending analysis request for NetVendor (model=anthropic/claude-haiku-4.5)
2026-07-14 15:00:02 | DEBUG    | pipeline.analyze     | Prompt length: 4823 chars
2026-07-14 15:00:04 | DEBUG    | pipeline.analyze     | LLM response keys: ['headline', 'themes', 'messaging_shift', 'icp_signal', 'threat_assessment', 'notable_creatives', 'suggested_action']
2026-07-14 15:00:04 | INFO     | pipeline.main        |   Threat: 4/5 - New vendor payments campaign targeting operators
```

---

## Design rationale

**Why not structlog / loguru?** Zero-dependency constraint. The pipeline runs on GitHub Actions where every `pip install` adds time, and the stdlib `logging` module does everything needed here.

**Why dual output?** GitHub Actions step logs are great for quick "did it work?" checks, but they're ephemeral and hard to search. The file handler gives you a persistent, grep-able record with timestamps for correlating events across modules.

**Why not JSON structured logs?** Overkill for a pipeline that runs once a week with ~10 iterations. If this ever needs log aggregation (Datadog, CloudWatch), switch the file handler's formatter to `json.dumps()` output — the logger hierarchy and message structure are already there.

**Why `exc_info=True` on errors?** Stack traces are critical for debugging. Without them, you get `ERROR processing NetVendor: 429 Client Error` with no idea which line or which API call failed. With them, you get the full traceback pointing to the exact request.
