import json
import pytest
from src.digest import build_digest


def _make_analysis(name, threat, headline, threat_level="critical"):
    return {
        "competitor": {"name": name, "threat_level": threat_level},
        "headline": headline,
        "themes": ["theme1", "theme2"],
        "messaging_shift": "Shifted to new messaging" if threat >= 3 else None,
        "icp_signal": "operators",
        "threat_assessment": threat,
        "notable_creatives": [],
        "suggested_action": "Review this" if threat >= 4 else None,
        "new_count": 2,
        "ended_count": 1,
        "active_count": 5,
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

    def test_reply_message_structure(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 4, "New campaign launched")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        assert reply["text"] == "NetVendor analysis"
        assert reply["blocks"][0]["type"] == "header"
        assert reply["blocks"][0]["text"]["text"] == "NetVendor"

        # Should have header, stats, themes, shift, action = 5 blocks
        assert len(reply["blocks"]) == 5

    def test_reply_omits_optional_blocks_when_empty(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 2, "Minor update")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        # header, stats, themes only (no shift, no action)
        assert len(reply["blocks"]) == 3

    def test_threat_bar_rendering(self, tmp_output_dir):
        analyses = [_make_analysis("NetVendor", 3, "Medium threat")]

        build_digest("2026-07-14", analyses, output_dir=tmp_output_dir)

        reply = json.loads((tmp_output_dir / "reply_00_netvendor.json").read_text())
        stats_text = reply["blocks"][1]["text"]["text"]
        assert ":red_circle::red_circle::red_circle:" in stats_text
        assert ":white_circle::white_circle:" in stats_text
