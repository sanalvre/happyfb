# Architecture: SQLite with FTS5 Full-Text Search

How the pipeline uses SQLite's FTS5 extension for searchable ad creative text, including the trigger-based content sync pattern and the pysqlite3 workaround for GitHub Actions.

---

## Overview

The pipeline stores ad creatives in a regular `ads` table, but also maintains a parallel **FTS5 virtual table** (`ads_fts`) that enables full-text search across creative body, title, and CTA text. This lets you query things like:

```sql
SELECT * FROM ads_fts WHERE ads_fts MATCH 'vendor payments';
SELECT * FROM ads_fts WHERE ads_fts MATCH 'Yardi AND integration';
```

FTS5 supports boolean operators (`AND`, `OR`, `NOT`), prefix matching (`pay*`), phrase search (`"vendor payments"`), and column-specific search (`creative_body:vendor`).

---

## Content-sync triggers

FTS5 in "content=" mode stores no data of its own. It's a search index that points back to the source table. This saves disk space but requires **manual sync** when the source table changes.

Three triggers keep the FTS index in sync with the `ads` table:

### Insert trigger (`ads_ai`)

```sql
CREATE TRIGGER ads_ai AFTER INSERT ON ads BEGIN
  INSERT INTO ads_fts(rowid, creative_body, creative_title, cta_text)
  VALUES (new.rowid, new.creative_body, new.creative_title, new.cta_text);
END;
```

When a new ad is inserted, the trigger adds its text to the FTS index.

### Delete trigger (`ads_ad`)

```sql
CREATE TRIGGER ads_ad AFTER DELETE ON ads BEGIN
  INSERT INTO ads_fts(ads_fts, rowid, creative_body, creative_title, cta_text)
  VALUES ('delete', old.rowid, old.creative_body, old.creative_title, old.cta_text);
END;
```

FTS5 deletes are **not** `DELETE FROM` — they're a special `INSERT` with the table name as the first column value set to `'delete'`. This is a quirk of FTS5's content-sync protocol. The old values must be provided exactly as they were when inserted, otherwise the index becomes inconsistent.

### Update trigger (`ads_au`)

```sql
CREATE TRIGGER ads_au AFTER UPDATE ON ads BEGIN
  INSERT INTO ads_fts(ads_fts, rowid, creative_body, creative_title, cta_text)
  VALUES ('delete', old.rowid, old.creative_body, old.creative_title, old.cta_text);
  INSERT INTO ads_fts(rowid, creative_body, creative_title, cta_text)
  VALUES (new.rowid, new.creative_body, new.creative_title, new.cta_text);
END;
```

Updates are implemented as delete + insert. The old values are removed from the index, then the new values are added.

---

## The pysqlite3 problem

GitHub Actions runners ship with a system SQLite that has **FTS5 disabled** due to a known bug (actions/runner-images#12576). The standard Python `sqlite3` module links against this system library, so `CREATE VIRTUAL TABLE ... USING fts5(...)` fails.

### The fix

`requirements.txt` includes `pysqlite3-binary`, which bundles its own SQLite library with FTS5 enabled. The `src/db.py` module tries to import it first:

```python
try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3
```

- **GitHub Actions (Linux)**: `pysqlite3-binary` installs and provides FTS5.
- **Local dev (Windows/Mac)**: `pysqlite3-binary` is Linux-only, so the import fails and falls back to the standard `sqlite3` module. Modern desktop Python ships with FTS5 enabled by default, so it just works.

This fallback is also used in `src/diff.py` and `src/discover.py` since they reference `sqlite3.Connection` for type hints.

---

## Schema

```sql
-- Source table
CREATE TABLE IF NOT EXISTS ads (
  ad_id TEXT PRIMARY KEY,
  competitor TEXT NOT NULL,
  ...
  creative_body TEXT,
  creative_title TEXT,
  cta_text TEXT,
  ...
);

-- FTS5 index (content-sync mode)
CREATE VIRTUAL TABLE IF NOT EXISTS ads_fts USING fts5(
  creative_body, creative_title, cta_text,
  content='ads', content_rowid='rowid'
);
```

The `content='ads'` directive tells FTS5 to read row data from the `ads` table when returning results. The `content_rowid='rowid'` maps the FTS rowid to the `ads` table's implicit rowid.

---

## Use cases

### Searching ad copy

Find all ads mentioning vendor payments:

```sql
SELECT a.* FROM ads a
JOIN ads_fts f ON a.rowid = f.rowid
WHERE ads_fts MATCH 'vendor payments';
```

### Competitor-specific search

Find Yardi integration mentions from NetVendor:

```sql
SELECT a.* FROM ads a
JOIN ads_fts f ON a.rowid = f.rowid
WHERE ads_fts MATCH 'Yardi integration'
AND a.competitor = 'NetVendor';
```

### Ranking by relevance

FTS5 provides a built-in `rank` function:

```sql
SELECT a.*, rank FROM ads a
JOIN ads_fts f ON a.rowid = f.rowid
WHERE ads_fts MATCH 'operator dashboard'
ORDER BY rank;
```

---

## Future: contractor FTS

The `contractors` table doesn't have an FTS index yet because search is less critical for lead discovery. If keyword search across contractor ad text becomes useful, adding it follows the same pattern: create the virtual table, add three triggers.
