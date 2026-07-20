import json
import os
import time
from datetime import date
from pathlib import Path

import requests
import yaml

from .logging_config import get_logger

try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3

log = get_logger("discover")

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}/ads_archive"
TRADES_PATH = Path(__file__).parent.parent / "config" / "trades.yaml"

FIELDS = ",".join([
    "id",
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "page_name",
    "page_id",
    "ad_delivery_start_time",
    "publisher_platforms",
])


def load_trades(config_path: Path | None = None) -> list[dict]:
    path = config_path or TRADES_PATH
    with open(path) as f:
        return yaml.safe_load(f)["trades"]


def search_ads_by_term(search_term: str, access_token: str | None = None,
                       limit: int = 100) -> list[dict]:
    """Search Meta Ads Library for ads matching a keyword."""
    token = access_token or ACCESS_TOKEN
    if not token:
        raise ValueError("META_ACCESS_TOKEN is required")

    params = {
        "access_token": token,
        "search_terms": search_term,
        "ad_reached_countries": '["US"]',
        "ad_active_status": "all",
        "ad_type": "all",
        "fields": FIELDS,
        "limit": min(limit, 500),
    }

    log.debug("Searching for '%s'", search_term)
    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()

    usage_header = response.headers.get("X-App-Usage", "")
    if usage_header:
        usage_data = json.loads(usage_header)
        call_count = float(usage_data.get("call_count", 0))
        log.debug("API usage: %.1f%%", call_count)
        if call_count > 80:
            log.warning("Rate limit at %.1f%%, sleeping 60s", call_count)
            time.sleep(60)

    data = response.json()
    ads = data.get("data", [])
    log.debug("'%s' returned %d ads", search_term, len(ads))
    return ads


def extract_contractors_from_ads(ads: list[dict], trade: str) -> list[dict]:
    """Extract unique contractor pages from a list of ads."""
    seen = {}
    for ad in ads:
        page_id = ad.get("page_id", "")
        if not page_id or page_id in seen:
            if page_id in seen:
                seen[page_id]["ad_count"] += 1
            continue

        bodies = ad.get("ad_creative_bodies") or []
        titles = ad.get("ad_creative_link_titles") or []

        seen[page_id] = {
            "page_id": page_id,
            "page_name": ad.get("page_name", ""),
            "trade": trade,
            "ad_count": 1,
            "sample_ad_text": bodies[0] if bodies else (titles[0] if titles else ""),
            "raw_json": json.dumps(ad),
        }

    return list(seen.values())


def discover_contractors(trades: list[dict] | None = None,
                         db: sqlite3.Connection | None = None,
                         access_token: str | None = None) -> dict:
    """Search for contractor leads across all trade categories.

    Returns summary dict with new contractors found per trade.
    """
    if trades is None:
        trades = load_trades()

    today = date.today().isoformat()
    all_new = []
    trade_counts = {}

    for trade in trades:
        trade_name = trade["name"]
        trade_contractors = []

        for term in trade["search_terms"]:
            try:
                ads = search_ads_by_term(term, access_token=access_token)
                contractors = extract_contractors_from_ads(ads, trade_name)
                trade_contractors.extend(contractors)
            except Exception as e:
                log.error("Search failed for '%s': %s", term, e, exc_info=True)

        deduped = _dedupe_by_page_id(trade_contractors)
        log.info("Trade %s: found %d unique pages across %d search terms",
                 trade_name, len(deduped), len(trade["search_terms"]))

        if db is not None:
            new = _store_contractors(deduped, today, db)
        else:
            new = deduped

        trade_counts[trade_name] = len(new)
        all_new.extend(new)

    log.info("Discovery complete: %d new contractors across %d trades",
             len(all_new), len(trades))

    return {
        "new_contractors": all_new,
        "total_new": len(all_new),
        "by_trade": trade_counts,
    }


def _dedupe_by_page_id(contractors: list[dict]) -> list[dict]:
    seen = {}
    for c in contractors:
        pid = c["page_id"]
        if pid not in seen:
            seen[pid] = c
        else:
            seen[pid]["ad_count"] += c["ad_count"]
    return list(seen.values())


def _store_contractors(contractors: list[dict], today: str,
                       db: sqlite3.Connection) -> list[dict]:
    """Insert new contractors into DB, update last_seen for existing. Returns only new ones."""
    new = []
    for c in contractors:
        existing = db.execute(
            "SELECT page_id FROM contractors WHERE page_id = ?",
            (c["page_id"],),
        ).fetchone()

        if existing:
            db.execute(
                "UPDATE contractors SET last_seen = ?, ad_count = ? WHERE page_id = ?",
                (today, c["ad_count"], c["page_id"]),
            )
        else:
            db.execute("""
                INSERT INTO contractors (page_id, page_name, trade, first_seen,
                                        last_seen, ad_count, sample_ad_text, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["page_id"], c["page_name"], c["trade"], today, today,
                c["ad_count"], c["sample_ad_text"], c["raw_json"],
            ))
            new.append(c)

    db.commit()
    updated = len(contractors) - len(new)
    if new or updated:
        log.debug("Stored contractors: %d new, %d updated", len(new), updated)
    return new
