# Architecture: State Persistence via GitHub Releases

How the pipeline stores and retrieves its SQLite database between runs using GitHub Releases as a free, zero-config object store.

---

## The problem

GitHub Actions runners are **ephemeral** — every workflow run starts from a clean checkout with no local state. But the pipeline needs to persist its SQLite database (`ads.db`) between runs to detect which ads are new, ended, or unchanged week over week.

Common solutions (S3, GCS, database service) all require external accounts, credentials, and billing. This pipeline uses **GitHub Releases** instead — free, built-in, and the `gh` CLI is pre-installed on every runner.

---

## How it works

```
Monday Run N                              Monday Run N+1
============                              ==============

1. gh release download "state"            1. gh release download "state"
   -> state/ads.db                           -> state/ads.db (with Run N's data)

2. Pipeline reads/writes ads.db           2. Pipeline reads/writes ads.db

3. VACUUM INTO ads_upload.db              3. VACUUM INTO ads_upload.db
   (clean single-file copy)                  (clean single-file copy)

4. gh release upload "state"              4. gh release upload "state"
   ads_upload.db --clobber                   ads_upload.db --clobber
```

The release tag `state` acts like a named storage bucket. The `--clobber` flag on upload overwrites the previous asset, so only the latest version is kept.

---

## Implementation: `src/storage.py`

### `pull(db_path)`

1. Creates `state/` directory if needed
2. Runs `gh release download state --pattern ads.db --dir state/ --clobber`
3. **If release not found**: initializes a fresh database with `init_db()` (first-ever run)
4. **If download succeeds**: runs `PRAGMA integrity_check` to verify the file isn't corrupted

### `push(db_path)`

1. Creates a clean copy via `VACUUM INTO` (see below)
2. Ensures the release exists: `gh release create state` (idempotent — fails silently if already exists)
3. Uploads: `gh release upload state ads_upload.db --clobber`
4. Removes the temporary upload file

---

## Why `VACUUM INTO` matters

SQLite in WAL (Write-Ahead Log) mode creates up to three files:

```
state/ads.db        (main database)
state/ads.db-wal    (write-ahead log)
state/ads.db-shm    (shared memory index)
```

If you upload just `ads.db` without the WAL file, you lose uncommitted writes. If you upload all three, the download needs to reassemble them correctly.

`VACUUM INTO` solves this by creating a **single, self-contained file** with all data:

```python
conn.execute("VACUUM INTO ?", (upload_path,))
```

Key properties:
- Produces a clean database with no WAL/SHM dependencies
- Uses a parameterized query (not string interpolation) to avoid SQL injection with unusual file paths
- The original database remains untouched (read-only operation)
- Output file is defragmented and compacted

### Path construction

The upload path is built with `pathlib` to avoid string manipulation bugs:

```python
p = Path(path)
upload_path = str(p.parent / (p.stem + "_upload" + p.suffix))
# state/ads.db -> state/ads_upload.db
```

This is safer than `path.replace(".db", "_upload.db")`, which would break on paths like `my.db.backup/ads.db`.

---

## Concurrency protection

Two overlapping pipeline runs could corrupt the database (Run A downloads, Run B downloads, Run A uploads, Run B uploads stale data over Run A's changes).

The workflow prevents this with a **concurrency group**:

```yaml
concurrency:
  group: competitive-intel
  cancel-in-progress: false
```

- `group: competitive-intel` — only one workflow in this group runs at a time
- `cancel-in-progress: false` — if a second run is triggered while the first is running, the second **queues** instead of canceling the first. This prevents data loss from interrupted uploads.

---

## Failure handling

### `push()` runs on `if: always()`

```yaml
- name: Push SQLite state
  if: always()
  env:
    GH_TOKEN: ${{ github.token }}
  run: python -c "from src.storage import push; push()"
```

Even if the analysis or digest steps fail, the state is pushed. This preserves the extract and diff work so the next run doesn't re-process the same ads.

### First-run bootstrap

On the very first run, there's no release and no database. `pull()` handles this gracefully:

```python
if "release not found" in result.stderr.lower() or "not found" in result.stderr.lower():
    log.info("No existing state found. Initializing fresh database.")
    init_db(path)
```

Similarly, `push()` creates the release tag if it doesn't exist:

```python
subprocess.run(
    ["gh", "release", "create", RELEASE_TAG, ...],
    capture_output=True, text=True,  # ignore errors if already exists
)
```

---

## Limits and tradeoffs

| Aspect | GitHub Releases | Notes |
|--------|----------------|-------|
| Max asset size | 2 GB | More than enough for ad metadata |
| Retention | Indefinite | No expiration policy |
| Cost | Free | Included in all GitHub plans |
| Auth | `GITHUB_TOKEN` | Provided automatically by Actions |
| Versioning | None (overwrite) | Only latest state is kept |
| Concurrent access | None built-in | Handled by workflow concurrency group |
| Geographic redundancy | GitHub's infra | Not configurable |

### When to outgrow this

If the database grows beyond ~100 MB or you need:
- Point-in-time recovery (versioned snapshots)
- Multi-writer access (parallel workflows)
- Sub-second access latency

...then migrate to a proper object store (S3, GCS) or a hosted database. The `storage.py` module is the only file that needs to change — `pull()` and `push()` are the entire interface.

---

## Gitignore entries

```
state/ads.db
state/ads_upload.db
*.db-wal
*.db-shm
```

The database and its artifacts are never committed to the repo. They live exclusively in GitHub Releases.
