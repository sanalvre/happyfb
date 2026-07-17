import json
import os
import time

import requests

from .logging_config import get_logger

log = get_logger("extract")

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}/ads_archive"

FIELDS = ",".join([
    "id",
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
    "page_name",
    "page_id",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "ad_snapshot_url",
    "languages",
    "publisher_platforms",
])


def fetch_ads(competitor: dict, access_token: str | None = None) -> list[dict]:
    """Fetch all ads for a competitor from Meta Ads Library API."""
    token = access_token or ACCESS_TOKEN
    if not token:
        raise ValueError("META_ACCESS_TOKEN is required")

    all_ads = []
    params = {
        "access_token": token,
        "search_page_ids": competitor["page_id"],
        "ad_reached_countries": "US",
        "ad_active_status": "ALL",
        "fields": FIELDS,
        "limit": 500,
    }

    url = BASE_URL
    page = 0
    while url:
        page += 1
        log.debug("Fetching page %d for %s", page, competitor.get("name", "?"))
        response = requests.get(url, params=params, timeout=60)

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

        batch = data.get("data", [])
        all_ads.extend(batch)
        log.debug("Page %d returned %d ads (total: %d)", page, len(batch), len(all_ads))

        paging = data.get("paging", {})
        url = paging.get("next")
        params = {}

    log.info("Fetched %d ads for %s across %d pages",
             len(all_ads), competitor.get("name", "?"), page)
    return all_ads


def normalize_ad(raw_ad: dict) -> dict:
    """Normalize a raw Meta API ad response into our internal format."""
    bodies = raw_ad.get("ad_creative_bodies") or []
    titles = raw_ad.get("ad_creative_link_titles") or []
    captions = raw_ad.get("ad_creative_link_captions") or []

    return {
        "ad_id": raw_ad.get("id", ""),
        "creative_body": bodies[0] if bodies else None,
        "creative_title": titles[0] if titles else None,
        "cta_text": captions[0] if captions else None,
        "snapshot_url": raw_ad.get("ad_snapshot_url"),
        "platforms": json.dumps(raw_ad.get("publisher_platforms") or []),
        "start_date": raw_ad.get("ad_delivery_start_time"),
        "end_date": raw_ad.get("ad_delivery_stop_time"),
        "page_name": raw_ad.get("page_name"),
        "raw_json": json.dumps(raw_ad),
    }
