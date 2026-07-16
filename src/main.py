import argparse
import json
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from .db import init_db, get_connection
from .extract import fetch_ads
from .diff import compute_diff, get_prior_themes, save_snapshot
from .analyze import analyze_competitor, build_analysis_result
from .digest import build_digest

CONFIG_PATH = Path(__file__).parent.parent / "config" / "competitors.yaml"


def load_competitors(config_path: Path | None = None) -> list[dict]:
    path = config_path or CONFIG_PATH
    with open(path) as f:
        return yaml.safe_load(f)["competitors"]


def run_pipeline(competitors: list[dict] | None = None, db_path: str | None = None,
                 dry_run: bool = False) -> dict:
    """Run the full extract-diff-analyze-digest pipeline."""
    if competitors is None:
        competitors = load_competitors()

    db = init_db(db_path) if db_path else init_db()
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.utcnow().isoformat()
    week_of = date.today().isoformat()

    db.execute(
        "INSERT INTO pipeline_runs (run_id, started_at, status) VALUES (?, ?, 'running')",
        (run_id, started_at),
    )
    db.commit()

    analyses = []
    failed = 0

    for comp in competitors:
        try:
            print(f"Processing {comp['name']}...")

            raw_ads = fetch_ads(comp)
            print(f"  Fetched {len(raw_ads)} ads")

            diff = compute_diff(comp["name"], raw_ads, db)
            print(f"  New: {diff['new_count']}, Ended: {diff['ended_count']}, Active: {diff['active_count']}")

            prior = get_prior_themes(comp["name"], db)

            if dry_run:
                analysis = {
                    "headline": f"[DRY RUN] {diff['new_count']} new, {diff['ended_count']} ended",
                    "themes": ["dry-run"],
                    "messaging_shift": None,
                    "icp_signal": "unclear",
                    "threat_assessment": 1,
                    "notable_creatives": [],
                    "suggested_action": None,
                }
            else:
                analysis = analyze_competitor(comp, diff, prior)

            save_snapshot(comp["name"], week_of, analysis, diff, db)

            result = build_analysis_result(comp, diff, analysis)
            analyses.append(result)
            print(f"  Threat: {analysis.get('threat_assessment', '?')}/5 - {analysis.get('headline', 'N/A')}")

        except Exception as e:
            failed += 1
            print(f"  ERROR processing {comp['name']}: {e}", file=sys.stderr)

    digest_result = build_digest(week_of, analyses) if analyses else None

    status = "success" if failed == 0 else ("partial" if analyses else "failed")
    db.execute(
        "UPDATE pipeline_runs SET completed_at = ?, status = ?, "
        "competitors_processed = ?, competitors_failed = ? WHERE run_id = ?",
        (datetime.utcnow().isoformat(), status, len(analyses), failed, run_id),
    )
    db.commit()
    db.close()

    if status == "failed":
        raise RuntimeError(f"Pipeline failed: all {failed} competitors errored")

    return {
        "run_id": run_id,
        "status": status,
        "competitors_processed": len(analyses),
        "competitors_failed": failed,
        "digest": digest_result,
    }


def run_backfill(days: int, competitors: list[dict] | None = None,
                 db_path: str | None = None) -> None:
    """Seed historical data by fetching all available ads (no LLM analysis).

    The days parameter is accepted for CLI compatibility but the Meta Ads
    Library API returns all available ads regardless of date range.
    """
    if competitors is None:
        competitors = load_competitors()

    db = init_db(db_path) if db_path else init_db()
    print(f"Backfilling all available ads (requested {days} days)")

    for comp in competitors:
        try:
            print(f"Backfilling {comp['name']}...")
            raw_ads = fetch_ads(comp)
            diff = compute_diff(comp["name"], raw_ads, db)
            print(f"  Stored {diff['active_count']} ads")
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)

    db.close()


def main():
    parser = argparse.ArgumentParser(description="VendorBids Competitive Intel Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM analysis")
    parser.add_argument("--backfill", type=int, metavar="DAYS",
                        help="Backfill N days of historical ads (no LLM)")
    parser.add_argument("--competitor", type=str, help="Process only this competitor")
    args = parser.parse_args()

    competitors = load_competitors()
    if args.competitor:
        competitors = [c for c in competitors if c["name"].lower() == args.competitor.lower()]
        if not competitors:
            print(f"Competitor '{args.competitor}' not found in config.", file=sys.stderr)
            sys.exit(1)

    if args.backfill:
        run_backfill(args.backfill, competitors)
    else:
        result = run_pipeline(competitors, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
