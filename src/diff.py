import json
from datetime import date

from .extract import normalize_ad
from .logging_config import get_logger

try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3

log = get_logger("diff")


def compute_diff(competitor: str, scraped_ads: list[dict], db: sqlite3.Connection) -> dict:
    """Compare fresh ads against stored state. Returns new, ended, and counts."""
    today = date.today().isoformat()

    log.debug("Computing diff for %s with %d scraped ads", competitor, len(scraped_ads))

    normalized = [normalize_ad(ad) for ad in scraped_ads]
    scraped_ids = {ad["ad_id"] for ad in normalized}

    cursor = db.execute(
        "SELECT ad_id FROM ads WHERE competitor = ? AND status = 'active'",
        (competitor,),
    )
    known_active_ids = {row[0] for row in cursor}

    new_ads = [a for a in normalized if a["ad_id"] not in known_active_ids]
    ended_ids = known_active_ids - scraped_ids

    reactivated = scraped_ids & {row[0] for row in db.execute(
        "SELECT ad_id FROM ads WHERE competitor = ? AND status = 'ended'", (competitor,)
    ).fetchall()}
    if reactivated:
        log.info("%s: %d ads reactivated", competitor, len(reactivated))

    ended_ads = []
    for ad_id in ended_ids:
        row = db.execute("SELECT * FROM ads WHERE ad_id = ?", (ad_id,)).fetchone()
        if row:
            ended_ads.append({
                "ad_id": row["ad_id"],
                "creative_body": row["creative_body"],
                "creative_title": row["creative_title"],
                "cta_text": row["cta_text"],
                "snapshot_url": row["snapshot_url"],
                "platforms": row["platforms"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
                "raw_json": row["raw_json"],
            })
        db.execute(
            "UPDATE ads SET status = 'ended', end_date = ?, last_seen = ? WHERE ad_id = ?",
            (today, today, ad_id),
        )

    for ad in normalized:
        db.execute("""
            INSERT INTO ads (ad_id, competitor, first_seen, last_seen, status,
                           creative_body, creative_title, cta_text, snapshot_url,
                           platforms, start_date, end_date, raw_json)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ad_id) DO UPDATE SET
                last_seen = excluded.last_seen,
                status = 'active',
                end_date = NULL,
                creative_body = excluded.creative_body,
                creative_title = excluded.creative_title,
                cta_text = excluded.cta_text,
                snapshot_url = excluded.snapshot_url,
                platforms = excluded.platforms,
                start_date = excluded.start_date,
                raw_json = excluded.raw_json
        """, (
            ad["ad_id"], competitor, today, today,
            ad["creative_body"], ad["creative_title"], ad["cta_text"],
            ad["snapshot_url"], ad["platforms"], ad["start_date"],
            ad["end_date"], ad["raw_json"],
        ))

    db.commit()

    log.debug("%s diff: %d new, %d ended, %d active (was %d)",
              competitor, len(new_ads), len(ended_ads),
              len(scraped_ids), len(known_active_ids))

    return {
        "competitor": competitor,
        "week_of": today,
        "new": new_ads,
        "ended": ended_ads,
        "active_count": len(scraped_ids),
        "prev_active_count": len(known_active_ids),
        "new_count": len(new_ads),
        "ended_count": len(ended_ads),
    }


def get_prior_themes(competitor: str, db: sqlite3.Connection, weeks: int = 4) -> list[dict]:
    """Retrieve the last N weeks of theme data for a competitor."""
    rows = db.execute(
        "SELECT week_of, themes_json, headline FROM weekly_snapshots "
        "WHERE competitor = ? ORDER BY week_of DESC LIMIT ?",
        (competitor, weeks),
    ).fetchall()
    return [
        {
            "week_of": row["week_of"],
            "themes": json.loads(row["themes_json"]) if row["themes_json"] else [],
            "headline": row["headline"],
        }
        for row in rows
    ]


def save_snapshot(competitor: str, week_of: str, analysis: dict, diff: dict, db: sqlite3.Connection) -> None:
    """Persist weekly analysis results."""
    log.debug("Saving snapshot for %s week %s (threat=%s)",
              competitor, week_of, analysis.get("threat_assessment"))
    db.execute("""
        INSERT INTO weekly_snapshots
            (week_of, competitor, active_count, new_count, ended_count,
             themes_json, shift_summary, threat_score, headline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(week_of, competitor) DO UPDATE SET
            active_count = excluded.active_count,
            new_count = excluded.new_count,
            ended_count = excluded.ended_count,
            themes_json = excluded.themes_json,
            shift_summary = excluded.shift_summary,
            threat_score = excluded.threat_score,
            headline = excluded.headline
    """, (
        week_of, competitor, diff["active_count"], diff["new_count"],
        diff["ended_count"], json.dumps(analysis.get("themes", [])),
        analysis.get("messaging_shift"), analysis.get("threat_assessment"),
        analysis.get("headline"),
    ))
    db.commit()
