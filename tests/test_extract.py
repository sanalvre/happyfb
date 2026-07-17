import json
from unittest.mock import patch, MagicMock

import pytest
from src.extract import fetch_ads, normalize_ad


class TestNormalizeAd:
    def test_full_ad(self, sample_raw_ads):
        result = normalize_ad(sample_raw_ads[0])

        assert result["ad_id"] == "ad_001"
        assert result["creative_body"] == "Streamline your vendor management with NetVendor"
        assert result["creative_title"] == "NetVendor - Vendor Management Made Easy"
        assert result["cta_text"] == "Learn More"
        assert result["start_date"] == "2026-07-01"
        assert result["end_date"] is None
        assert result["page_name"] == "NetVendor"
        assert json.loads(result["platforms"]) == ["facebook", "instagram"]
        assert json.loads(result["raw_json"])["id"] == "ad_001"

    def test_missing_fields(self):
        sparse_ad = {"id": "ad_sparse", "page_name": "Test"}
        result = normalize_ad(sparse_ad)

        assert result["ad_id"] == "ad_sparse"
        assert result["creative_body"] is None
        assert result["creative_title"] is None
        assert result["cta_text"] is None
        assert result["snapshot_url"] is None
        assert json.loads(result["platforms"]) == []

    def test_empty_arrays(self):
        ad = {
            "id": "ad_empty",
            "ad_creative_bodies": [],
            "ad_creative_link_titles": [],
            "ad_creative_link_captions": [],
            "publisher_platforms": [],
        }
        result = normalize_ad(ad)

        assert result["creative_body"] is None
        assert result["creative_title"] is None
        assert result["cta_text"] is None


class TestFetchAds:
    def test_missing_token(self, sample_competitor):
        with patch.dict("os.environ", {"META_ACCESS_TOKEN": ""}, clear=False):
            with pytest.raises(ValueError, match="META_ACCESS_TOKEN"):
                fetch_ads(sample_competitor, access_token="")

    @patch("src.extract.requests.get")
    def test_single_page(self, mock_get, sample_competitor, sample_raw_ads):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": sample_raw_ads,
            "paging": {},
        }
        mock_response.headers = {}
        mock_get.return_value = mock_response

        result = fetch_ads(sample_competitor, access_token="test_token")

        assert len(result) == 3
        assert result[0]["id"] == "ad_001"
        mock_get.assert_called_once()

    @patch("src.extract.requests.get")
    def test_pagination(self, mock_get, sample_competitor, sample_raw_ads):
        page1_response = MagicMock()
        page1_response.json.return_value = {
            "data": sample_raw_ads[:2],
            "paging": {"next": "https://graph.facebook.com/v21.0/ads_archive?after=cursor1"},
        }
        page1_response.headers = {}

        page2_response = MagicMock()
        page2_response.json.return_value = {
            "data": sample_raw_ads[2:],
            "paging": {},
        }
        page2_response.headers = {}

        mock_get.side_effect = [page1_response, page2_response]

        result = fetch_ads(sample_competitor, access_token="test_token")

        assert len(result) == 3
        assert mock_get.call_count == 2

    @patch("src.extract.requests.get")
    @patch("src.extract.time.sleep")
    def test_rate_limit_backoff(self, mock_sleep, mock_get, sample_competitor):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "paging": {}}
        mock_response.headers = {"X-App-Usage": json.dumps({"call_count": 85})}
        mock_get.return_value = mock_response

        fetch_ads(sample_competitor, access_token="test_token")

        mock_sleep.assert_called_once_with(60)

    @patch("src.extract.requests.get")
    def test_http_error_propagates(self, mock_get, sample_competitor):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("429 Too Many Requests")
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="429"):
            fetch_ads(sample_competitor, access_token="test_token")

    @patch("src.extract.requests.get")
    def test_malformed_usage_header_ignored(self, mock_get, sample_competitor):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "ad_1"}], "paging": {}}
        mock_response.headers = {"X-App-Usage": "not-json"}
        mock_get.return_value = mock_response

        with pytest.raises(json.JSONDecodeError):
            fetch_ads(sample_competitor, access_token="test_token")

    @patch("src.extract.requests.get")
    def test_api_params_include_page_id(self, mock_get, sample_competitor):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [], "paging": {}}
        mock_response.headers = {}
        mock_get.return_value = mock_response

        fetch_ads(sample_competitor, access_token="test_token")

        call_args = mock_get.call_args
        params = call_args.kwargs.get("params") or call_args[1].get("params")
        assert params["search_page_ids"] == sample_competitor["page_id"]
        assert params["ad_reached_countries"] == "US"
        assert "id" in params["fields"]


class TestNormalizeAdEdgeCases:
    def test_unicode_in_creative_body(self):
        ad = {
            "id": "ad_unicode",
            "ad_creative_bodies": ["Save money! \U0001f4b0 Best HVAC in town ❤️"],
            "page_name": "Test",
        }
        result = normalize_ad(ad)
        assert "\U0001f4b0" in result["creative_body"]

    def test_very_long_creative_body(self):
        ad = {
            "id": "ad_long",
            "ad_creative_bodies": ["x" * 10000],
            "page_name": "Test",
        }
        result = normalize_ad(ad)
        assert len(result["creative_body"]) == 10000
        assert json.loads(result["raw_json"])["id"] == "ad_long"
