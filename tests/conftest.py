import pytest
import tempfile
import os
from pathlib import Path

from src.db import init_db


@pytest.fixture
def tmp_db(tmp_path):
    """Provide a fresh SQLite database for each test."""
    db_path = str(tmp_path / "test.db")
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def tmp_output_dir(tmp_path):
    """Provide a temp directory for digest output files."""
    out = tmp_path / "slack_payloads"
    out.mkdir()
    return out


@pytest.fixture
def sample_competitor():
    return {
        "name": "NetVendor",
        "threat_level": "critical",
        "page_id": "123456789",
        "notes": "Direct VendorBids competitor.",
    }


@pytest.fixture
def sample_raw_ads():
    """Simulated Meta Ads Library API response."""
    return [
        {
            "id": "ad_001",
            "ad_creative_bodies": ["Streamline your vendor management with NetVendor"],
            "ad_creative_link_titles": ["NetVendor - Vendor Management Made Easy"],
            "ad_creative_link_captions": ["Learn More"],
            "ad_creative_link_descriptions": ["The leading vendor platform"],
            "page_name": "NetVendor",
            "page_id": "123456789",
            "ad_delivery_start_time": "2026-07-01",
            "ad_delivery_stop_time": None,
            "ad_snapshot_url": "https://www.facebook.com/ads/archive/render_ad/?id=ad_001",
            "languages": ["en"],
            "publisher_platforms": ["facebook", "instagram"],
        },
        {
            "id": "ad_002",
            "ad_creative_bodies": ["Faster vendor payments for multifamily operators"],
            "ad_creative_link_titles": ["NetVendor Payments"],
            "ad_creative_link_captions": ["Sign Up"],
            "ad_creative_link_descriptions": None,
            "page_name": "NetVendor",
            "page_id": "123456789",
            "ad_delivery_start_time": "2026-07-05",
            "ad_delivery_stop_time": None,
            "ad_snapshot_url": "https://www.facebook.com/ads/archive/render_ad/?id=ad_002",
            "languages": ["en"],
            "publisher_platforms": ["facebook"],
        },
        {
            "id": "ad_003",
            "ad_creative_bodies": ["Old campaign ending soon"],
            "ad_creative_link_titles": ["NetVendor Legacy"],
            "ad_creative_link_captions": None,
            "ad_creative_link_descriptions": None,
            "page_name": "NetVendor",
            "page_id": "123456789",
            "ad_delivery_start_time": "2026-06-01",
            "ad_delivery_stop_time": "2026-07-10",
            "ad_snapshot_url": "https://www.facebook.com/ads/archive/render_ad/?id=ad_003",
            "languages": ["en"],
            "publisher_platforms": ["facebook"],
        },
    ]


@pytest.fixture
def sample_analysis():
    """Simulated LLM analysis response."""
    return {
        "headline": "NetVendor launched new campaign targeting property managers with faster vendor payments messaging",
        "themes": ["faster vendor payments", "operator dashboard", "Yardi integration"],
        "messaging_shift": "New Yardi integration messaging not seen in prior weeks",
        "icp_signal": "operators",
        "threat_assessment": 4,
        "creative_quality": 4,
        "engagement_signal": "high",
        "why_it_works": "Strong social proof with customer count, clear ROI claim",
        "notable_creatives": ["ad_001", "ad_002"],
        "suggested_action": "Review NetVendor's Yardi integration claims and flag for Jindou",
    }
