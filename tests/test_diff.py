import json
import pytest
from src.diff import compute_diff, get_prior_themes, save_snapshot


class TestComputeDiff:
    def test_all_new_ads(self, tmp_db, sample_raw_ads):
        diff = compute_diff("NetVendor", sample_raw_ads, tmp_db)

        assert diff["competitor"] == "NetVendor"
        assert diff["new_count"] == 3
        assert diff["ended_count"] == 0
        assert diff["active_count"] == 3
        assert diff["prev_active_count"] == 0
        assert len(diff["new"]) == 3

    def test_no_change_second_run(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)
        diff = compute_diff("NetVendor", sample_raw_ads, tmp_db)

        assert diff["new_count"] == 0
        assert diff["ended_count"] == 0
        assert diff["active_count"] == 3

    def test_ended_ads_detected(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)

        # Second run with one ad removed
        remaining = sample_raw_ads[:2]
        diff = compute_diff("NetVendor", remaining, tmp_db)

        assert diff["new_count"] == 0
        assert diff["ended_count"] == 1
        assert diff["active_count"] == 2
        assert len(diff["ended"]) == 1
        assert diff["ended"][0]["ad_id"] == "ad_003"

    def test_new_ad_added(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)

        new_ad = {
            "id": "ad_004",
            "ad_creative_bodies": ["Brand new campaign"],
            "ad_creative_link_titles": ["New!"],
            "page_name": "NetVendor",
            "page_id": "123456789",
            "ad_delivery_start_time": "2026-07-14",
            "publisher_platforms": ["facebook"],
        }
        diff = compute_diff("NetVendor", sample_raw_ads + [new_ad], tmp_db)

        assert diff["new_count"] == 1
        assert diff["active_count"] == 4
        assert diff["new"][0]["ad_id"] == "ad_004"

    def test_ended_ad_status_in_db(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)
        compute_diff("NetVendor", sample_raw_ads[:2], tmp_db)

        row = tmp_db.execute("SELECT status FROM ads WHERE ad_id = 'ad_003'").fetchone()
        assert row["status"] == "ended"

    def test_separate_competitors(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)

        other_ads = [{"id": "other_001", "ad_creative_bodies": ["Other product"],
                      "page_name": "Revyse", "page_id": "999",
                      "publisher_platforms": ["facebook"]}]
        diff = compute_diff("Revyse", other_ads, tmp_db)

        assert diff["new_count"] == 1
        assert diff["active_count"] == 1

        nv_count = tmp_db.execute(
            "SELECT COUNT(*) as c FROM ads WHERE competitor = 'NetVendor'"
        ).fetchone()["c"]
        assert nv_count == 3


    def test_empty_api_response_marks_all_ended(self, tmp_db, sample_raw_ads):
        """If the API returns 0 ads, all active ads are marked as ended.

        This is correct behavior when the competitor genuinely stopped all ads,
        but could be a false positive if the API errored silently. The pipeline
        catches API errors upstream before reaching compute_diff.
        """
        compute_diff("NetVendor", sample_raw_ads, tmp_db)
        diff = compute_diff("NetVendor", [], tmp_db)

        assert diff["ended_count"] == 3
        assert diff["active_count"] == 0
        assert diff["new_count"] == 0

    def test_reactivated_ad_clears_end_date(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)
        compute_diff("NetVendor", sample_raw_ads[:2], tmp_db)

        row = tmp_db.execute("SELECT status, end_date FROM ads WHERE ad_id = 'ad_003'").fetchone()
        assert row["status"] == "ended"
        assert row["end_date"] is not None

        compute_diff("NetVendor", sample_raw_ads, tmp_db)

        row = tmp_db.execute("SELECT status, end_date FROM ads WHERE ad_id = 'ad_003'").fetchone()
        assert row["status"] == "active"
        assert row["end_date"] is None

    def test_ended_ads_have_consistent_schema(self, tmp_db, sample_raw_ads):
        compute_diff("NetVendor", sample_raw_ads, tmp_db)
        diff = compute_diff("NetVendor", sample_raw_ads[:2], tmp_db)

        ended = diff["ended"][0]
        new_keys = set(diff["new"][0].keys()) if diff["new"] else None

        required_keys = {"ad_id", "creative_body", "creative_title", "cta_text",
                         "snapshot_url", "platforms", "start_date", "end_date"}
        assert required_keys.issubset(set(ended.keys()))


class TestGetPriorThemes:
    def test_no_history(self, tmp_db):
        result = get_prior_themes("NetVendor", tmp_db)
        assert result == []

    def test_returns_stored_themes(self, tmp_db):
        tmp_db.execute(
            "INSERT INTO weekly_snapshots (week_of, competitor, themes_json, headline) "
            "VALUES ('2026-07-07', 'NetVendor', ?, 'Test headline')",
            (json.dumps(["theme1", "theme2"]),),
        )
        tmp_db.commit()

        result = get_prior_themes("NetVendor", tmp_db)
        assert len(result) == 1
        assert result[0]["themes"] == ["theme1", "theme2"]
        assert result[0]["headline"] == "Test headline"


class TestSaveSnapshot:
    def test_save_and_retrieve(self, tmp_db, sample_analysis):
        diff = {"active_count": 10, "new_count": 3, "ended_count": 1}
        save_snapshot("NetVendor", "2026-07-14", sample_analysis, diff, tmp_db)

        row = tmp_db.execute(
            "SELECT * FROM weekly_snapshots WHERE competitor = 'NetVendor'"
        ).fetchone()

        assert row["week_of"] == "2026-07-14"
        assert row["active_count"] == 10
        assert row["threat_score"] == 4
        assert row["headline"] == sample_analysis["headline"]
        assert json.loads(row["themes_json"]) == sample_analysis["themes"]

    def test_upsert_same_week(self, tmp_db, sample_analysis):
        diff = {"active_count": 10, "new_count": 3, "ended_count": 1}
        save_snapshot("NetVendor", "2026-07-14", sample_analysis, diff, tmp_db)

        updated = {**sample_analysis, "threat_assessment": 5, "headline": "Updated"}
        save_snapshot("NetVendor", "2026-07-14", updated, diff, tmp_db)

        rows = tmp_db.execute(
            "SELECT * FROM weekly_snapshots WHERE competitor = 'NetVendor'"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["threat_score"] == 5
        assert rows[0]["headline"] == "Updated"
