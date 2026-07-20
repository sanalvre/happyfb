"""Export pipeline data from SQLite to JSON for the GitHub Pages dashboard."""

import json
from datetime import datetime
from pathlib import Path

from .db import init_db
from .main import load_competitors
from .logging_config import get_logger

log = get_logger("export")

SITE_DIR = Path(__file__).parent.parent / "site"


def export_dashboard_data(db_path: str | None = None,
                          output_dir: Path | None = None) -> Path:
    """Read SQLite state and write a JSON file for the static dashboard."""
    db = init_db(db_path)
    out = output_dir or SITE_DIR
    out.mkdir(parents=True, exist_ok=True)

    competitors = load_competitors()
    comp_map = {c["name"]: c for c in competitors}

    snapshots = _get_snapshots(db, weeks=12)
    latest_by_target = _get_latest_snapshots(db)
    ads_summary = _get_ads_summary(db)
    contractor_leads = _get_contractor_leads(db)
    recent_runs = _get_recent_runs(db)

    targets = []
    for comp in competitors:
        name = comp["name"]
        latest = latest_by_target.get(name, {})
        history = snapshots.get(name, [])
        ad_info = ads_summary.get(name, {"active": 0, "total": 0})

        targets.append({
            "name": name,
            "category": comp.get("category", "competitor"),
            "threat_level": comp.get("threat_level"),
            "page_id": comp.get("page_id"),
            "notes": comp.get("notes", ""),
            "latest": latest,
            "history": history,
            "ads": ad_info,
        })

    data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "target_count": len(targets),
        "targets": targets,
        "contractor_leads": contractor_leads,
        "recent_runs": recent_runs,
    }

    out_path = out / "data.json"
    out_path.write_text(json.dumps(data, indent=2, default=str))
    log.info("Exported dashboard data to %s (%d targets, %d leads)",
             out_path, len(targets), len(contractor_leads))

    db.close()
    return out_path


def _get_snapshots(db, weeks: int = 12) -> dict:
    """Get weekly snapshots grouped by competitor, most recent first."""
    rows = db.execute(
        "SELECT * FROM weekly_snapshots ORDER BY week_of DESC LIMIT ?",
        (weeks * 50,),
    ).fetchall()

    grouped = {}
    for row in rows:
        name = row["competitor"]
        grouped.setdefault(name, []).append({
            "week_of": row["week_of"],
            "active_count": row["active_count"],
            "new_count": row["new_count"],
            "ended_count": row["ended_count"],
            "themes": json.loads(row["themes_json"]) if row["themes_json"] else [],
            "threat_score": row["threat_score"],
            "headline": row["headline"],
            "shift_summary": row["shift_summary"],
        })
    return grouped


def _get_latest_snapshots(db) -> dict:
    """Get the single most recent snapshot per competitor."""
    rows = db.execute("""
        SELECT s.* FROM weekly_snapshots s
        INNER JOIN (
            SELECT competitor, MAX(week_of) as max_week
            FROM weekly_snapshots GROUP BY competitor
        ) latest ON s.competitor = latest.competitor AND s.week_of = latest.max_week
    """).fetchall()

    result = {}
    for row in rows:
        result[row["competitor"]] = {
            "week_of": row["week_of"],
            "active_count": row["active_count"],
            "new_count": row["new_count"],
            "ended_count": row["ended_count"],
            "themes": json.loads(row["themes_json"]) if row["themes_json"] else [],
            "threat_score": row["threat_score"],
            "headline": row["headline"],
            "shift_summary": row["shift_summary"],
        }
    return result


def _get_ads_summary(db) -> dict:
    """Get ad counts per competitor."""
    rows = db.execute("""
        SELECT competitor,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
        FROM ads GROUP BY competitor
    """).fetchall()

    return {row["competitor"]: {"active": row["active"], "total": row["total"]} for row in rows}


def _get_contractor_leads(db) -> list:
    """Get all discovered contractor leads."""
    rows = db.execute(
        "SELECT * FROM contractors ORDER BY first_seen DESC LIMIT 200"
    ).fetchall()

    return [{
        "page_id": row["page_id"],
        "page_name": row["page_name"],
        "trade": row["trade"],
        "first_seen": row["first_seen"],
        "last_seen": row["last_seen"],
        "status": row["status"],
        "website": row["website"],
        "phone": row["phone"],
        "email": row["email"],
        "city": row["city"],
        "state": row["state"],
        "ad_count": row["ad_count"],
        "relevance_score": row["relevance_score"],
        "serves_multifamily": bool(row["serves_multifamily"]) if row["serves_multifamily"] is not None else None,
        "company_size_signal": row["company_size_signal"],
        "sample_ad_text": row["sample_ad_text"],
    } for row in rows]


def _get_recent_runs(db) -> list:
    """Get recent pipeline run history."""
    rows = db.execute(
        "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 20"
    ).fetchall()

    return [{
        "run_id": row["run_id"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "status": row["status"],
        "competitors_processed": row["competitors_processed"],
        "competitors_failed": row["competitors_failed"],
        "contractors_found": row["contractors_found"],
    } for row in rows]


if __name__ == "__main__":
    export_dashboard_data()
