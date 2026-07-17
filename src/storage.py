import os
import subprocess
from pathlib import Path

from .db import init_db, get_connection, DB_PATH
from .logging_config import get_logger

log = get_logger("storage")

RELEASE_TAG = "state"


def pull(db_path: str | None = None) -> None:
    """Download SQLite from GitHub Releases."""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    result = subprocess.run(
        ["gh", "release", "download", RELEASE_TAG,
         "--pattern", "ads.db",
         "--dir", os.path.dirname(path) or ".",
         "--clobber"],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        if "release not found" in result.stderr.lower() or "not found" in result.stderr.lower():
            log.info("No existing state found. Initializing fresh database.")
            init_db(path)
        else:
            log.error("gh release download failed: %s", result.stderr)
            raise RuntimeError(f"Failed to download state: {result.stderr}")
    else:
        conn = get_connection(path)
        check = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if check[0] != "ok":
            log.error("Database integrity check failed: %s", check[0])
            raise RuntimeError(f"Database integrity check failed: {check[0]}")
        log.info("State downloaded and verified.")


def push(db_path: str | None = None) -> None:
    """Upload SQLite to GitHub Releases."""
    path = db_path or DB_PATH
    p = Path(path)
    upload_path = str(p.parent / (p.stem + "_upload" + p.suffix))

    conn = get_connection(path)
    conn.execute("VACUUM INTO ?", (upload_path,))
    conn.close()

    subprocess.run(
        ["gh", "release", "create", RELEASE_TAG,
         "--title", "Pipeline State",
         "--notes", "SQLite state for competitive intel pipeline. Auto-updated.",
         "--latest=false"],
        capture_output=True, text=True,
    )

    result = subprocess.run(
        ["gh", "release", "upload", RELEASE_TAG,
         upload_path, "--clobber"],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        log.error("gh release upload failed: %s", result.stderr)
        raise RuntimeError(f"Failed to upload state: {result.stderr}")

    os.remove(upload_path)
    log.info("State uploaded to GitHub Releases.")
