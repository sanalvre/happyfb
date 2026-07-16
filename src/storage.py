import os
import subprocess

from .db import init_db, get_connection, DB_PATH

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
            print("No existing state found. Initializing fresh database.")
            init_db(path)
        else:
            raise RuntimeError(f"Failed to download state: {result.stderr}")
    else:
        conn = get_connection(path)
        check = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        if check[0] != "ok":
            raise RuntimeError(f"Database integrity check failed: {check[0]}")
        print("State downloaded and verified.")


def push(db_path: str | None = None) -> None:
    """Upload SQLite to GitHub Releases."""
    path = db_path or DB_PATH
    upload_path = path.replace(".db", "_upload.db")

    conn = get_connection(path)
    conn.execute(f"VACUUM INTO '{upload_path}'")
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
        raise RuntimeError(f"Failed to upload state: {result.stderr}")

    os.remove(upload_path)
    print("State uploaded to GitHub Releases.")
