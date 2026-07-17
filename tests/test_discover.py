import json
from unittest.mock import patch, MagicMock

import pytest
from src.discover import (
    search_ads_by_term,
    extract_contractors_from_ads,
    discover_contractors,
    load_trades,
)


@pytest.fixture
def sample_contractor_ads():
    return [
        {
            "id": "ad_101",
            "ad_creative_bodies": ["ABC Heating & Cooling - 24/7 HVAC service for apartments"],
            "ad_creative_link_titles": ["ABC HVAC"],
            "page_name": "ABC Heating & Cooling",
            "page_id": "pg_abc",
            "ad_delivery_start_time": "2026-06-01",
            "publisher_platforms": ["facebook"],
        },
        {
            "id": "ad_102",
            "ad_creative_bodies": ["Best rates on commercial plumbing"],
            "ad_creative_link_titles": ["Quick Plumb Pro"],
            "page_name": "Quick Plumb Pro",
            "page_id": "pg_qpp",
            "ad_delivery_start_time": "2026-07-01",
            "publisher_platforms": ["facebook", "instagram"],
        },
        {
            "id": "ad_103",
            "ad_creative_bodies": ["Another ad from ABC Heating"],
            "ad_creative_link_titles": ["ABC HVAC Summer Special"],
            "page_name": "ABC Heating & Cooling",
            "page_id": "pg_abc",
            "ad_delivery_start_time": "2026-07-10",
            "publisher_platforms": ["facebook"],
        },
    ]


class TestExtractContractors:
    def test_deduplicates_by_page_id(self, sample_contractor_ads):
        result = extract_contractors_from_ads(sample_contractor_ads, "HVAC")
        page_ids = [c["page_id"] for c in result]
        assert len(page_ids) == 2
        assert len(set(page_ids)) == 2

    def test_counts_ads_per_page(self, sample_contractor_ads):
        result = extract_contractors_from_ads(sample_contractor_ads, "HVAC")
        abc = next(c for c in result if c["page_id"] == "pg_abc")
        assert abc["ad_count"] == 2

    def test_captures_trade(self, sample_contractor_ads):
        result = extract_contractors_from_ads(sample_contractor_ads, "Plumbing")
        assert all(c["trade"] == "Plumbing" for c in result)

    def test_captures_sample_text(self, sample_contractor_ads):
        result = extract_contractors_from_ads(sample_contractor_ads, "HVAC")
        abc = next(c for c in result if c["page_id"] == "pg_abc")
        assert "HVAC" in abc["sample_ad_text"] or "Heating" in abc["sample_ad_text"]

    def test_empty_ads(self):
        result = extract_contractors_from_ads([], "HVAC")
        assert result == []

    def test_missing_fields(self):
        ads = [{"id": "ad_x", "page_id": "pg_x", "page_name": "Test"}]
        result = extract_contractors_from_ads(ads, "Electrical")
        assert len(result) == 1
        assert result[0]["sample_ad_text"] == ""


class TestSearchAdsByTerm:
    def test_missing_token(self):
        with pytest.raises(ValueError, match="META_ACCESS_TOKEN"):
            search_ads_by_term("plumbing", access_token="")

    @patch("src.discover.requests.get")
    def test_returns_ads(self, mock_get, sample_contractor_ads):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": sample_contractor_ads}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        result = search_ads_by_term("HVAC contractor", access_token="test_token")
        assert len(result) == 3
        mock_get.assert_called_once()

    @patch("src.discover.requests.get")
    def test_uses_search_terms_param(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        search_ads_by_term("commercial plumber", access_token="test_token")

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params") or call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs["params"]
        assert params["search_terms"] == "commercial plumber"
        assert params["ad_active_status"] == "ACTIVE"


class TestDiscoverContractors:
    @patch("src.discover.search_ads_by_term")
    def test_discovery_without_db(self, mock_search, sample_contractor_ads):
        mock_search.return_value = sample_contractor_ads

        trades = [{"name": "HVAC", "search_terms": ["HVAC contractor"]}]
        result = discover_contractors(trades=trades, db=None, access_token="test")

        assert result["total_new"] == 2
        assert "HVAC" in result["by_trade"]

    @patch("src.discover.search_ads_by_term")
    def test_stores_new_contractors(self, mock_search, sample_contractor_ads, tmp_db):
        mock_search.return_value = sample_contractor_ads

        trades = [{"name": "HVAC", "search_terms": ["HVAC contractor"]}]
        result = discover_contractors(trades=trades, db=tmp_db, access_token="test")

        assert result["total_new"] == 2

        rows = tmp_db.execute("SELECT * FROM contractors").fetchall()
        assert len(rows) == 2

    @patch("src.discover.search_ads_by_term")
    def test_deduplicates_across_runs(self, mock_search, sample_contractor_ads, tmp_db):
        mock_search.return_value = sample_contractor_ads

        trades = [{"name": "HVAC", "search_terms": ["HVAC contractor"]}]

        result1 = discover_contractors(trades=trades, db=tmp_db, access_token="test")
        assert result1["total_new"] == 2

        result2 = discover_contractors(trades=trades, db=tmp_db, access_token="test")
        assert result2["total_new"] == 0

    @patch("src.discover.search_ads_by_term")
    def test_handles_search_failure(self, mock_search):
        mock_search.side_effect = ConnectionError("API down")

        trades = [{"name": "HVAC", "search_terms": ["HVAC contractor"]}]
        result = discover_contractors(trades=trades, db=None, access_token="test")

        assert result["total_new"] == 0


class TestLoadTrades:
    def test_loads_config(self):
        trades = load_trades()
        assert len(trades) == 8
        assert trades[0]["name"] == "HVAC"
        assert len(trades[0]["search_terms"]) >= 2

    def test_custom_path(self, tmp_path):
        config = tmp_path / "test_trades.yaml"
        config.write_text("trades:\n  - name: Test\n    search_terms:\n      - 'test term'\n")

        trades = load_trades(config)
        assert len(trades) == 1
        assert trades[0]["name"] == "Test"
