import json
from unittest.mock import patch, MagicMock

import pytest
from src.enrich import enrich_contractor, fetch_page_contact, enrich_contractors


@pytest.fixture
def sample_contractor():
    return {
        "page_id": "pg_abc",
        "page_name": "ABC Heating & Cooling",
        "trade": "HVAC",
        "ad_count": 3,
        "sample_ad_text": "24/7 HVAC service for apartment complexes and commercial buildings",
    }


@pytest.fixture
def sample_enrichment():
    return {
        "relevance_score": 4,
        "serves_multifamily": True,
        "company_size_signal": "midsize",
        "city": "Phoenix",
        "state": "AZ",
        "notes": "Serves apartment complexes, strong multifamily fit.",
    }


class TestEnrichContractor:
    def test_missing_key(self, sample_contractor):
        with pytest.raises(ValueError, match="OPENROUTER_KEY"):
            enrich_contractor(sample_contractor, api_key="")

    @patch("src.enrich.requests.post")
    def test_successful_enrichment(self, mock_post, sample_contractor, sample_enrichment):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(sample_enrichment)}}]
        }
        mock_post.return_value = mock_response

        result = enrich_contractor(sample_contractor, api_key="test_key")

        assert result["relevance_score"] == 4
        assert result["serves_multifamily"] is True
        assert result["city"] == "Phoenix"

    @patch("src.enrich.requests.post")
    def test_prompt_includes_contractor_info(self, mock_post, sample_contractor, sample_enrichment):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(sample_enrichment)}}]
        }
        mock_post.return_value = mock_response

        enrich_contractor(sample_contractor, api_key="test_key")

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
        prompt = body["messages"][0]["content"]

        assert "ABC Heating & Cooling" in prompt
        assert "HVAC" in prompt


class TestFetchPageContact:
    def test_missing_token(self):
        with pytest.raises(ValueError, match="META_ACCESS_TOKEN"):
            fetch_page_contact("pg_abc", access_token="")

    @patch("src.enrich.requests.get")
    def test_returns_contact_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "ABC Heating",
            "website": "https://abcheating.com",
            "phone": "(602) 555-1234",
            "emails": ["info@abcheating.com"],
        }
        mock_get.return_value = mock_response

        result = fetch_page_contact("pg_abc", access_token="test_token")

        assert result["website"] == "https://abcheating.com"
        assert result["phone"] == "(602) 555-1234"
        assert result["email"] == "info@abcheating.com"

    @patch("src.enrich.requests.get")
    def test_handles_inaccessible_page(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        result = fetch_page_contact("pg_private", access_token="test_token")
        assert result == {}

    @patch("src.enrich.requests.get")
    def test_handles_partial_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Test Co"}
        mock_get.return_value = mock_response

        result = fetch_page_contact("pg_partial", access_token="test_token")
        assert result == {}


class TestEnrichContractors:
    @patch("src.enrich.fetch_page_contact")
    @patch("src.enrich.enrich_contractor")
    def test_enriches_batch(self, mock_enrich, mock_contact,
                            sample_contractor, sample_enrichment, tmp_db):
        mock_enrich.return_value = sample_enrichment
        mock_contact.return_value = {"website": "https://abcheating.com"}

        tmp_db.execute("""
            INSERT INTO contractors (page_id, page_name, trade, first_seen, last_seen, ad_count)
            VALUES ('pg_abc', 'ABC Heating & Cooling', 'HVAC', '2026-07-16', '2026-07-16', 3)
        """)
        tmp_db.commit()

        result = enrich_contractors([sample_contractor], tmp_db, api_key="test_key")

        assert len(result) == 1
        assert result[0]["relevance_score"] == 4
        assert result[0]["website"] == "https://abcheating.com"

        row = tmp_db.execute("SELECT * FROM contractors WHERE page_id = 'pg_abc'").fetchone()
        assert row["relevance_score"] == 4
        assert row["website"] == "https://abcheating.com"

    @patch("src.enrich.fetch_page_contact")
    @patch("src.enrich.enrich_contractor")
    def test_handles_enrichment_failure(self, mock_enrich, mock_contact,
                                        sample_contractor, tmp_db):
        mock_enrich.side_effect = ConnectionError("API down")

        tmp_db.execute("""
            INSERT INTO contractors (page_id, page_name, trade, first_seen, last_seen, ad_count)
            VALUES ('pg_abc', 'ABC Heating & Cooling', 'HVAC', '2026-07-16', '2026-07-16', 3)
        """)
        tmp_db.commit()

        result = enrich_contractors([sample_contractor], tmp_db, api_key="test_key")
        assert len(result) == 1

    @patch("src.enrich.fetch_page_contact")
    @patch("src.enrich.enrich_contractor")
    def test_clamps_relevance_score(self, mock_enrich, mock_contact, tmp_db):
        mock_enrich.return_value = {"relevance_score": 99, "serves_multifamily": False}
        mock_contact.return_value = {}

        contractor = {"page_id": "pg_x", "page_name": "Test", "trade": "HVAC"}
        tmp_db.execute("""
            INSERT INTO contractors (page_id, page_name, trade, first_seen, last_seen)
            VALUES ('pg_x', 'Test', 'HVAC', '2026-07-16', '2026-07-16')
        """)
        tmp_db.commit()

        result = enrich_contractors([contractor], tmp_db, api_key="test_key")
        assert result[0]["relevance_score"] == 5
