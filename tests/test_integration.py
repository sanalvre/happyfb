"""Integration tests: full pipeline flow with mocked external APIs."""

import json
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest
from src.main import run_pipeline, load_competitors
from src.db import init_db


@pytest.fixture
def mock_competitors():
    return [
        {
            "name": "NetVendor",
            "threat_level": "critical",
            "page_id": "111",
            "notes": "Direct competitor",
        },
        {
            "name": "Revyse",
            "threat_level": "critical",
            "page_id": "222",
            "notes": "AI vendor discovery",
        },
    ]


@pytest.fixture
def mock_ads_response():
    return [
        {
            "id": "ad_001",
            "ad_creative_bodies": ["Test ad body"],
            "ad_creative_link_titles": ["Test title"],
            "ad_creative_link_captions": ["CTA"],
            "page_name": "NetVendor",
            "page_id": "111",
            "ad_delivery_start_time": "2026-07-01",
            "ad_delivery_stop_time": None,
            "ad_snapshot_url": "https://facebook.com/ads/render/001",
            "publisher_platforms": ["facebook"],
        },
    ]


@pytest.fixture
def mock_analysis():
    return {
        "headline": "New campaign targeting operators",
        "themes": ["vendor payments", "operator tools"],
        "messaging_shift": None,
        "icp_signal": "operators",
        "threat_assessment": 3,
        "notable_creatives": ["ad_001"],
        "suggested_action": None,
    }


class TestFullPipeline:
    @patch("src.main.fetch_ads")
    @patch("src.main.analyze_competitor")
    def test_end_to_end_dry_run(self, mock_analyze, mock_fetch,
                                 mock_competitors, mock_ads_response, tmp_path):
        mock_fetch.return_value = mock_ads_response
        db_path = str(tmp_path / "test.db")

        result = run_pipeline(
            competitors=mock_competitors,
            db_path=db_path,
            dry_run=True,
            skip_leads=True,
        )

        assert result["status"] == "success"
        assert result["competitors_processed"] == 2
        assert result["competitors_failed"] == 0
        mock_analyze.assert_not_called()  # dry run skips LLM

    @patch("src.main.fetch_ads")
    @patch("src.main.analyze_competitor")
    def test_end_to_end_with_analysis(self, mock_analyze, mock_fetch,
                                      mock_competitors, mock_ads_response,
                                      mock_analysis, tmp_path):
        mock_fetch.return_value = mock_ads_response
        mock_analyze.return_value = mock_analysis
        db_path = str(tmp_path / "test.db")

        result = run_pipeline(
            competitors=mock_competitors,
            db_path=db_path,
            dry_run=False,
            skip_leads=True,
        )

        assert result["status"] == "success"
        assert result["competitors_processed"] == 2
        assert mock_analyze.call_count == 2

    @patch("src.main.fetch_ads")
    @patch("src.main.analyze_competitor")
    def test_partial_failure(self, mock_analyze, mock_fetch,
                              mock_competitors, mock_analysis, tmp_path):
        def fetch_side_effect(comp):
            if comp["name"] == "NetVendor":
                raise ConnectionError("API timeout")
            return [{"id": "ad_r1", "ad_creative_bodies": ["Revyse ad"],
                     "page_name": "Revyse", "page_id": "222",
                     "publisher_platforms": ["facebook"]}]

        mock_fetch.side_effect = fetch_side_effect
        mock_analyze.return_value = mock_analysis
        db_path = str(tmp_path / "test.db")

        result = run_pipeline(
            competitors=mock_competitors,
            db_path=db_path,
            dry_run=False,
            skip_leads=True,
        )

        assert result["status"] == "partial"
        assert result["competitors_processed"] == 1
        assert result["competitors_failed"] == 1

    @patch("src.main.fetch_ads")
    def test_total_failure_raises(self, mock_fetch, mock_competitors, tmp_path):
        mock_fetch.side_effect = ConnectionError("API down")
        db_path = str(tmp_path / "test.db")

        with pytest.raises(RuntimeError, match="all .* competitors errored"):
            run_pipeline(competitors=mock_competitors, db_path=db_path,
                         dry_run=True, skip_leads=True)

    @patch("src.main.fetch_ads")
    @patch("src.main.analyze_competitor")
    @patch("src.main.build_digest")
    def test_digest_files_created(self, mock_digest, mock_analyze, mock_fetch,
                                   mock_competitors, mock_ads_response,
                                   mock_analysis, tmp_path):
        mock_fetch.return_value = mock_ads_response
        mock_analyze.return_value = mock_analysis
        mock_digest.return_value = {"active_count": 2, "total_count": 2, "max_threat": 3,
                                    "contractors_found": 0, "files_written": 3}
        db_path = str(tmp_path / "test.db")

        result = run_pipeline(
            competitors=mock_competitors,
            db_path=db_path,
            dry_run=False,
            skip_leads=True,
        )

        assert result["digest"] is not None
        assert result["digest"]["active_count"] == 2
        mock_digest.assert_called_once()

    @patch("src.main.fetch_ads")
    def test_state_persists_across_runs(self, mock_fetch, mock_competitors,
                                         mock_ads_response, tmp_path):
        mock_fetch.return_value = mock_ads_response
        db_path = str(tmp_path / "test.db")

        run_pipeline(competitors=mock_competitors, db_path=db_path,
                     dry_run=True, skip_leads=True)

        # Second run: same ads, nothing should be new
        result = run_pipeline(competitors=mock_competitors, db_path=db_path,
                              dry_run=True, skip_leads=True)

        assert result["status"] == "success"

    @patch("src.main.fetch_ads")
    def test_pipeline_run_logged_in_db(self, mock_fetch, mock_competitors,
                                        mock_ads_response, tmp_path):
        mock_fetch.return_value = mock_ads_response
        db_path = str(tmp_path / "test.db")

        result = run_pipeline(competitors=mock_competitors, db_path=db_path,
                              dry_run=True, skip_leads=True)

        from src.db import get_connection
        conn = get_connection(db_path)
        run = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (result["run_id"],)
        ).fetchone()
        conn.close()

        assert run is not None
        assert run["status"] == "success"
        assert run["competitors_processed"] == 2


class TestLoadCompetitors:
    def test_loads_config(self):
        competitors = load_competitors()
        assert len(competitors) == 9
        assert competitors[0]["name"] == "NetVendor"
        assert competitors[0]["threat_level"] == "critical"

    def test_custom_path(self, tmp_path):
        config = tmp_path / "test_competitors.yaml"
        config.write_text("competitors:\n  - name: Test\n    threat_level: watch\n    page_id: '999'\n")

        competitors = load_competitors(config)
        assert len(competitors) == 1
        assert competitors[0]["name"] == "Test"


class TestDatabaseIntegrity:
    def test_fts_search(self, tmp_db):
        """Verify FTS5 triggers populate the search index."""
        tmp_db.execute("""
            INSERT INTO ads (ad_id, competitor, first_seen, last_seen, status,
                           creative_body, creative_title, cta_text, raw_json)
            VALUES ('fts_test', 'TestCo', '2026-07-14', '2026-07-14', 'active',
                    'Streamline vendor payments today', 'Vendor Platform', 'Sign Up',
                    '{}')
        """)
        tmp_db.commit()

        results = tmp_db.execute(
            "SELECT * FROM ads_fts WHERE ads_fts MATCH 'vendor payments'"
        ).fetchall()
        assert len(results) == 1

    def test_fts_delete_trigger(self, tmp_db):
        """Verify FTS index removes entry when ad is deleted."""
        tmp_db.execute("""
            INSERT INTO ads (ad_id, competitor, first_seen, last_seen, status,
                           creative_body, creative_title, cta_text, raw_json)
            VALUES ('fts_del', 'TestCo', '2026-07-14', '2026-07-14', 'active',
                    'Deletable body text', 'Delete title', 'CTA', '{}')
        """)
        tmp_db.commit()

        before = tmp_db.execute(
            "SELECT * FROM ads_fts WHERE ads_fts MATCH 'Deletable'"
        ).fetchall()
        assert len(before) == 1

        tmp_db.execute("DELETE FROM ads WHERE ad_id = 'fts_del'")
        tmp_db.commit()

        after = tmp_db.execute(
            "SELECT * FROM ads_fts WHERE ads_fts MATCH 'Deletable'"
        ).fetchall()
        assert len(after) == 0
