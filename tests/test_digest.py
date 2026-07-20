import json
import pytest
from src.digest import build_digest


def _make_analysis(name, threat, headline, threat_level="critical",
                   creative_quality=3, engagement_signal="medium",
                   why_it_works=None, category="competitor"):
    return {
        "competitor": {"name": name, "threat_level": threat_level, "category": category},
        "headline": headline,
        "themes": ["theme1", "theme2"],
        "messaging_shift": "Shifted to new messaging" if threat >= 3 else None,
        "icp_signal": "operators",
        "threat_assessment": threat,
        "creative_quality": creative_quality,
        "engagement_signal": engagement_signal,
        "why_it_works": why_it_works,
        "notable_creatives": [],
        "suggested_action": "Review this" if threat >= 4 else None,
        "new_count": 2,
        "ended_count": 1,
        "active_count": 5,
    }


def _make_contractor(name, page_id, trade, relevance=3, serves_multifamily=True):
    return {
        "page_id": page_id,
        "page_name": name,
        "trade": trade,
        "ad_count": 2,
        "relevance_score": relevance,
        "serves_multifamily": serves_multifamily,
        "company_size_signal": "midsize",
        "city": "Phoenix",
        "state": "AZ",
        "website": "https://example.com",
        "phone": "(555) 123-4567",
        "email": None,
        "sample_ad_text": "Professional service for commercial properties",
    }


class TestBuildDigest:
    def test_no_activity_creates_skip_flag(self, tmp_output_dir):
        analyses = [
            _make_analysis("NetVendor", 1, "steady state, no notable changes."),
            _make_analysis("Revyse", 1, "steady state, no notable changes."),
        ]

        result = build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        assert result is None
        assert (tmp_output_dir / "skip.flag").exists()
        assert not (tmp_output_dir / "parent.json").exists()

    def test_active_competitors_generate_files(self, tmp_output_dir):
        analyses = [
            _make_analysis("NetVendor", 4, "New campaign launched"),
            _make_analysis("Revyse", 3, "Two new ads"),
            _make_analysis("AppFolio", 1, "steady state, no notable changes.", "watch"),
        ]

        result = build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        assert result is not None
        assert result["active_count"] == 2
        assert result["total_count"] == 3
        assert result["max_threat"] == 4
        assert result["files_written"] == 3  # parent + 2 replies

        assert (tmp_output_dir / "parent.json").exists()
        assert (tmp_output_dir / "reply_00_netvendor.json").exists()
        assert (tmp_output_dir / "reply_01_revyse.json").exists()

    def test_parent_message_structure(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 4, "New campaign launched")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        parent = json.loads((tmp_output_dir / "parent.json").read_text())
        assert "text" in parent
        assert "blocks" in parent
        assert parent["blocks"][0]["type"] == "header"
        assert "2026-07-14" in parent["blocks"][0]["text"]["text"]

        # Should have header, summary section, divider, and competitor line
        assert len(parent["blocks"]) == 4

    def test_parent_has_alert_emoji_for_high_threat(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 4, "Dangerous new campaign")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        parent = json.loads((tmp_output_dir / "parent.json").read_text())
        competitor_block = parent["blocks"][3]
        assert ":rotating_light:" in competitor_block["text"]["text"]

    def test_no_alert_emoji_for_low_threat(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 2, "Minor update")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        parent = json.loads((tmp_output_dir / "parent.json").read_text())
        competitor_block = parent["blocks"][3]
        assert ":rotating_light:" not in competitor_block["text"]["text"]

    def test_reply_includes_creative_quality(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 4, "New campaign launched",
                                   creative_quality=4, engagement_signal="high",
                                   why_it_works="Strong social proof")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        stats_text = reply["blocks"][1]["text"]["text"]
        assert "Creative quality" in stats_text
        assert "Engagement" in stats_text

    def test_reply_includes_why_it_works(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 4, "New campaign launched",
                                   why_it_works="Clear ROI claim")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        texts = [b["text"]["text"] for b in reply["blocks"] if b["type"] == "section"]
        assert any("Why it works" in t for t in texts)

    def test_reply_omits_optional_blocks_when_empty(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 2, "Minor update")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        # header, stats, themes only (no why_it_works, no shift, no action)
        assert len(reply["blocks"]) == 3

    def test_threat_bar_rendering(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 3, "Medium threat")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        stats_text = reply["blocks"][1]["text"]["text"]
        assert ":red_circle::red_circle::red_circle:" in stats_text
        assert ":white_circle::white_circle:" in stats_text


class TestContractorDigest:
    def test_contractors_only_digest(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 1, "steady state, no notable changes.")]
        contractors = [_make_contractor("ABC HVAC", "pg1", "HVAC")]

        result = build_digest("2026-07-14", analyses, contractors=contractors,
                              output_dir=tmp_output_dir)

        assert result is not None
        assert result["contractors_found"] == 1
        assert (tmp_output_dir / "leads_parent.json").exists()
        assert (tmp_output_dir / "leads_reply_00_hvac.json").exists()
        assert not (tmp_output_dir / "parent.json").exists()  # no active competitors

    def test_both_tracks_digest(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 4, "New campaign launched")]
        contractors = [
            _make_contractor("ABC HVAC", "pg1", "HVAC"),
            _make_contractor("Quick Plumb", "pg2", "Plumbing"),
        ]

        result = build_digest("2026-07-14", analyses, contractors=contractors,
                              output_dir=tmp_output_dir)

        assert result["active_count"] == 1
        assert result["contractors_found"] == 2
        assert (tmp_output_dir / "leads_parent.json").exists()
        assert (tmp_output_dir / "parent.json").exists()

    def test_contractor_parent_summary(self, tmp_output_dir):
        contractors = [
            _make_contractor("ABC HVAC", "pg1", "HVAC"),
            _make_contractor("DEF HVAC", "pg2", "HVAC"),
            _make_contractor("Quick Plumb", "pg3", "Plumbing"),
        ]

        build_digest("2026-07-14", [], contractors=contractors,
                     output_dir=tmp_output_dir)

        parent = json.loads((tmp_output_dir / "leads_parent.json").read_text())
        summary = parent["blocks"][1]["text"]["text"]
        assert "3 new contractors" in summary
        assert "2 trades" in summary

    def test_contractor_reply_structure(self, tmp_output_dir):
        contractors = [_make_contractor("ABC HVAC", "pg1", "HVAC", relevance=4)]

        build_digest("2026-07-14", [], contractors=contractors,
                     output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "leads_reply_00_hvac.json").read_text())
        assert reply["blocks"][0]["text"]["text"] == "HVAC (1 new)"

        lead_text = reply["blocks"][1]["text"]["text"]
        assert "ABC HVAC" in lead_text
        assert "Phoenix, AZ" in lead_text
        assert "4/5" in lead_text
        assert "(555) 123-4567" in lead_text

    def test_contractor_multifamily_badge(self, tmp_output_dir):
        contractors = [_make_contractor("ABC HVAC", "pg1", "HVAC", serves_multifamily=True)]

        build_digest("2026-07-14", [], contractors=contractors,
                     output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "leads_reply_00_hvac.json").read_text())
        lead_text = reply["blocks"][1]["text"]["text"]
        assert ":office:" in lead_text


class TestOperatorDigest:
    def test_operator_parent_written(self, tmp_output_dir):
        ops = [_make_analysis("MAA", 3, "New leasing campaign", category="operator")]

        result = build_digest("2026-07-14", [], operator_analyses=ops,
                              output_dir=tmp_output_dir)

        assert result is not None
        assert result["operators_active"] == 1
        assert (tmp_output_dir / "operator_parent.json").exists()
        assert (tmp_output_dir / "operator_reply_00_maa.json").exists()

    def test_operator_parent_says_operator_intelligence(self, tmp_output_dir):
        ops = [_make_analysis("MAA", 3, "New leasing campaign", category="operator")]

        build_digest("2026-07-14", [], operator_analyses=ops,
                     output_dir=tmp_output_dir)

        parent = json.loads((tmp_output_dir / "operator_parent.json").read_text())
        assert "Operator intelligence" in parent["blocks"][0]["text"]["text"]
        assert "opportunity" in parent["blocks"][3]["text"]["text"]

    def test_operator_steady_state_skipped(self, tmp_output_dir):
        ops = [_make_analysis("MAA", 1, "steady state, no notable changes.", category="operator")]

        result = build_digest("2026-07-14", [], operator_analyses=ops,
                              output_dir=tmp_output_dir)

        assert result is None
        assert not (tmp_output_dir / "operator_parent.json").exists()


class TestContractorIntelDigest:
    def test_contractor_intel_parent_written(self, tmp_output_dir):
        cts = [_make_analysis("TruGreen", 3, "Spring campaign surge", category="contractor")]

        result = build_digest("2026-07-14", [], contractor_analyses=cts,
                              output_dir=tmp_output_dir)

        assert result is not None
        assert result["contractor_intel_active"] == 1
        assert (tmp_output_dir / "contractor_intel_parent.json").exists()

    def test_contractor_intel_parent_says_vendor_intelligence(self, tmp_output_dir):
        cts = [_make_analysis("TruGreen", 3, "Spring campaign surge", category="contractor")]

        build_digest("2026-07-14", [], contractor_analyses=cts,
                     output_dir=tmp_output_dir)

        parent = json.loads((tmp_output_dir / "contractor_intel_parent.json").read_text())
        assert "Vendor intelligence" in parent["blocks"][0]["text"]["text"]

    def test_all_categories_together(self, tmp_output_dir):
        comps = [_make_analysis("ServiceTitan", 3, "New campaign")]
        ops = [_make_analysis("MAA", 4, "Market expansion", category="operator")]
        cts = [_make_analysis("TruGreen", 2, "Seasonal push", category="contractor")]
        leads = [_make_contractor("ABC HVAC", "pg1", "HVAC")]

        result = build_digest("2026-07-14", comps, contractors=leads,
                              operator_analyses=ops, contractor_analyses=cts,
                              output_dir=tmp_output_dir)

        assert result["active_count"] == 1
        assert result["operators_active"] == 1
        assert result["contractor_intel_active"] == 1
        assert result["contractors_found"] == 1
        assert (tmp_output_dir / "parent.json").exists()
        assert (tmp_output_dir / "operator_parent.json").exists()
        assert (tmp_output_dir / "contractor_intel_parent.json").exists()
        assert (tmp_output_dir / "leads_parent.json").exists()
