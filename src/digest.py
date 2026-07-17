import json
import os
from pathlib import Path

from .logging_config import get_logger

log = get_logger("digest")

OUTPUT_DIR = Path(os.environ.get("DIGEST_OUTPUT_DIR", "state/slack_payloads"))


def build_digest(week_of: str, analyses: list[dict], output_dir: Path | None = None) -> dict | None:
    """Build Slack Block Kit payloads and write as JSON files.

    Returns summary dict with counts, or None if no activity.
    """
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    active = [a for a in analyses if a["headline"] != "steady state, no notable changes."]

    if not active:
        log.info("No notable activity across %d competitors, creating skip flag", len(analyses))
        (out / "skip.flag").touch()
        return None

    max_threat = max(a["threat_assessment"] for a in active)
    log.info("Building digest: %d/%d active competitors, max threat %d/5",
             len(active), len(analyses), max_threat)

    parent = _build_parent(week_of, analyses, active, max_threat)
    (out / "parent.json").write_text(json.dumps(parent, indent=2))

    for i, a in enumerate(active):
        reply = _build_reply(a)
        slug = a["competitor"]["name"].lower().replace(" ", "_")
        (out / f"reply_{i:02d}_{slug}.json").write_text(json.dumps(reply, indent=2))

    files_written = 1 + len(active)
    log.info("Wrote %d digest files to %s", files_written, out)
    return {
        "active_count": len(active),
        "total_count": len(analyses),
        "max_threat": max_threat,
        "files_written": files_written,
    }


def _build_parent(week_of: str, all_analyses: list[dict],
                  active: list[dict], max_threat: int) -> dict:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Competitive watch: week of {week_of}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{len(active)} of {len(all_analyses)} competitors had notable activity.*\n"
                    f"Highest threat score: *{max_threat}/5*"
                ),
            },
        },
        {"type": "divider"},
    ]

    for a in active:
        alert = ":rotating_light: " if a["threat_assessment"] >= 4 else ""
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{alert}*{a['competitor']['name']}* ({a['threat_assessment']}/5): {a['headline']}",
            },
        })

    return {
        "text": f"VendorBids competitive watch, week of {week_of}",
        "blocks": blocks,
    }


def _build_reply(analysis: dict) -> dict:
    score = analysis["threat_assessment"]
    threat_bar = ":red_circle:" * score + ":white_circle:" * (5 - score)

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": analysis["competitor"]["name"]},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Threat:* {threat_bar}\n"
                    f"*Targeting:* {analysis['icp_signal']}\n"
                    f"*New ads:* {analysis['new_count']}  |  "
                    f"*Ended:* {analysis['ended_count']}  |  "
                    f"*Active:* {analysis['active_count']}"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Themes:* {' · '.join(analysis['themes'])}",
            },
        },
    ]

    if analysis.get("messaging_shift"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Shift:* {analysis['messaging_shift']}"},
        })

    if analysis.get("suggested_action"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":arrow_right: *Action:* {analysis['suggested_action']}"},
        })

    return {
        "text": f"{analysis['competitor']['name']} analysis",
        "blocks": blocks,
    }
