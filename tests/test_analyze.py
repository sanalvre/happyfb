import json
from unittest.mock import patch, MagicMock

import pytest
from src.analyze import analyze_competitor, build_analysis_result


class TestAnalyzeCompetitor:
    def test_missing_key(self, sample_competitor):
        diff = {"week_of": "2026-07-14", "new_count": 0, "ended_count": 0,
                "active_count": 0, "prev_active_count": 0, "new": [], "ended": []}
        with pytest.raises(ValueError, match="OPENROUTER_KEY"):
            analyze_competitor(sample_competitor, diff, [], api_key="")

    @patch("src.analyze.requests.post")
    def test_successful_analysis(self, mock_post, sample_competitor, sample_analysis):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(sample_analysis)}}]
        }
        mock_post.return_value = mock_response

        diff = {
            "week_of": "2026-07-14", "new_count": 2, "ended_count": 1,
            "active_count": 5, "prev_active_count": 4, "new": [], "ended": [],
        }

        result = analyze_competitor(sample_competitor, diff, [], api_key="test_key")

        assert result["headline"] == sample_analysis["headline"]
        assert result["threat_assessment"] == 4
        assert result["themes"] == sample_analysis["themes"]
        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs["json"] if "json" in call_kwargs.kwargs else call_kwargs[1]["json"]
        assert body["model"] == "anthropic/claude-haiku-4.5"
        assert body["temperature"] == 0.3

    @patch("src.analyze.requests.post")
    def test_prompt_template_populated(self, mock_post, sample_competitor, sample_analysis):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(sample_analysis)}}]
        }
        mock_post.return_value = mock_response

        diff = {
            "week_of": "2026-07-14", "new_count": 2, "ended_count": 0,
            "active_count": 5, "prev_active_count": 3,
            "new": [{"ad_id": "ad_001", "creative_body": "Test ad"}],
            "ended": [],
        }
        prior = [{"week_of": "2026-07-07", "themes": ["old theme"], "headline": "Old"}]

        analyze_competitor(sample_competitor, diff, prior, api_key="test_key")

        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs["json"] if "json" in call_kwargs.kwargs else call_kwargs[1]["json"]
        prompt = body["messages"][0]["content"]

        assert "NetVendor" in prompt
        assert "critical" in prompt
        assert "2026-07-14" in prompt
        assert "old theme" in prompt


class TestBuildAnalysisResult:
    def test_merges_all_fields(self, sample_competitor, sample_analysis):
        diff = {
            "new_count": 3, "ended_count": 1, "active_count": 10,
            "new": [], "ended": [],
        }

        result = build_analysis_result(sample_competitor, diff, sample_analysis)

        assert result["competitor"]["name"] == "NetVendor"
        assert result["headline"] == sample_analysis["headline"]
        assert result["threat_assessment"] == 4
        assert result["new_count"] == 3
        assert result["active_count"] == 10
        assert result["icp_signal"] == "operators"

    def test_defaults_for_missing_fields(self, sample_competitor):
        diff = {"new_count": 0, "ended_count": 0, "active_count": 0, "new": [], "ended": []}
        empty_analysis = {}

        result = build_analysis_result(sample_competitor, diff, empty_analysis)

        assert result["headline"] == "steady state, no notable changes."
        assert result["threat_assessment"] == 1
        assert result["icp_signal"] == "unclear"
        assert result["themes"] == []

    def test_coerces_float_threat(self, sample_competitor):
        diff = {"new_count": 0, "ended_count": 0, "active_count": 0, "new": [], "ended": []}
        analysis = {"threat_assessment": 3.5, "themes": ["test"]}

        result = build_analysis_result(sample_competitor, diff, analysis)

        assert result["threat_assessment"] == 3
        assert isinstance(result["threat_assessment"], int)

    def test_coerces_string_threat(self, sample_competitor):
        diff = {"new_count": 0, "ended_count": 0, "active_count": 0, "new": [], "ended": []}
        analysis = {"threat_assessment": "4", "themes": ["test"]}

        result = build_analysis_result(sample_competitor, diff, analysis)

        assert result["threat_assessment"] == 4

    def test_clamps_threat_to_range(self, sample_competitor):
        diff = {"new_count": 0, "ended_count": 0, "active_count": 0, "new": [], "ended": []}

        result = build_analysis_result(sample_competitor, diff, {"threat_assessment": 99})
        assert result["threat_assessment"] == 5

        result = build_analysis_result(sample_competitor, diff, {"threat_assessment": -1})
        assert result["threat_assessment"] == 1

    def test_coerces_non_string_themes(self, sample_competitor):
        diff = {"new_count": 0, "ended_count": 0, "active_count": 0, "new": [], "ended": []}
        analysis = {"themes": [{"name": "pricing"}, 42]}

        result = build_analysis_result(sample_competitor, diff, analysis)

        assert all(isinstance(t, str) for t in result["themes"])
