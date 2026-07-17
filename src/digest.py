import json
import os
from pathlib import Path

from .logging_config import get_logger

log = get_logger("digest")

OUTPUT_DIR = Path(os.environ.get("DIGEST_OUTPUT_DIR", "state/slack_payloads"))


def build_digest(week_of: str, analyses: list[dict],
                 contractors: list[dict] | None = None,
                 output_dir: Path | None = None) -> dict | None:
    """Build Slack Block Kit payloads and write as JSON files.

    Returns summary dict with counts, or None if no activity at all.
    """
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    active = [a for a in analyses if a["headline"] != "steady state, no notable changes."]
    has_contractors = bool(contractors)
    has_competitors = bool(active)

    if not has_contractors and not has_competitors:
        log.info("No notable activity and no new contractors, creating skip flag")
        (out / "skip.flag").touch()
        return None

    files_written = 0

    if has_contractors:
        leads_msg = _build_contractor_parent(week_of, contractors)
        (out / "leads_parent.json").write_text(json.dumps(leads_msg, indent=2))
        files_written += 1

        trade_groups = {}
        for c in contractors:
            trade_groups.setdefault(c["trade"], []).append(c)

        for i, (trade, leads) in enumerate(sorted(trade_groups.items())):
            reply = _build_contractor_reply(trade, leads)
            slug = trade.lower().replace(" ", "_")
            (out / f"leads_reply_{i:02d}_{slug}.json").write_text(json.dumps(reply, indent=2))
            files_written += 1

        log.info("Built contractor digest: %d leads across %d trades",
                 len(contractors), len(trade_groups))

    if has_competitors:
        max_threat = max(a["threat_assessment"] for a in active)
        parent = _build_creative_parent(week_of, analyses, active, max_threat)
        (out / "parent.json").write_text(json.dumps(parent, indent=2))
        files_written += 1

        for i, a in enumerate(active):
            reply = _build_creative_reply(a)
            slug = a["competitor"]["name"].lower().replace(" ", "_")
            (out / f"reply_{i:02d}_{slug}.json").write_text(json.dumps(reply, indent=2))
            files_written += 1

        log.info("Built competitor digest: %d/%d active, max threat %d/5",
                 len(active), len(analyses), max_threat)
    else:
        max_threat = 0

    log.info("Wrote %d digest files to %s", files_written, out)
    return {
        "active_count": len(active),
        "total_count": len(analyses),
        "max_threat": max_threat,
        "contractors_found": len(contractors) if contractors else 0,
        "files_written": files_written,
    }


def _build_contractor_parent(week_of: str, contractors: list[dict]) -> dict:
    trade_counts = {}
    for c in contractors:
        trade_counts[c["trade"]] = trade_counts.get(c["trade"], 0) + 1

    summary_lines = [f"*{trade}:* {count}" for trade, count in sorted(trade_counts.items())]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"New contractor leads: week of {week_of}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{len(contractors)} new contractors found across "
                    f"{len(trade_counts)} trades.*\n"
                    + " | ".join(summary_lines)
                ),
            },
        },
    ]

    return {
        "text": f"VendorBids contractor leads, week of {week_of}",
        "blocks": blocks,
    }


def _build_contractor_reply(trade: str, leads: list[dict]) -> dict:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{trade} ({len(leads)} new)"},
        },
    ]

    for lead in leads[:10]:
        location = ""
        if lead.get("city") and lead.get("state"):
            location = f" — {lead['city']}, {lead['state']}"
        elif lead.get("state"):
            location = f" — {lead['state']}"

        website = ""
        if lead.get("website"):
            website = f" — {lead['website']}"

        relevance = lead.get("relevance_score", "?")
        multifamily = " :office:" if lead.get("serves_multifamily") else ""

        line = f"*{lead['page_name']}*{location}{website}{multifamily} (fit: {relevance}/5)"

        contact_parts = []
        if lead.get("phone"):
            contact_parts.append(lead["phone"])
        if lead.get("email"):
            contact_parts.append(lead["email"])
        if contact_parts:
            line += f"\n    :phone: {' | '.join(contact_parts)}"

        if lead.get("sample_ad_text"):
            snippet = lead["sample_ad_text"][:120]
            if len(lead["sample_ad_text"]) > 120:
                snippet += "..."
            line += f"\n    _{snippet}_"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": line},
        })

    if len(leads) > 10:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_{len(leads) - 10} more not shown_"}],
        })

    return {
        "text": f"{trade} contractor leads",
        "blocks": blocks,
    }


def _build_creative_parent(week_of: str, all_analyses: list[dict],
                           active: list[dict], max_threat: int) -> dict:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Competitor creative watch: week of {week_of}"},
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
        star = ":star: " if a.get("creative_quality", 0) >= 4 else ""
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{alert}{star}*{a['competitor']['name']}* "
                    f"(threat: {a['threat_assessment']}/5, "
                    f"creative: {a.get('creative_quality', '?')}/5): "
                    f"{a['headline']}"
                ),
            },
        })

    return {
        "text": f"VendorBids competitive creative watch, week of {week_of}",
        "blocks": blocks,
    }


def _build_creative_reply(analysis: dict) -> dict:
    score = analysis["threat_assessment"]
    threat_bar = ":red_circle:" * score + ":white_circle:" * (5 - score)

    creative_q = analysis.get("creative_quality", 0)
    creative_bar = ":star:" * creative_q + ":white_circle:" * (5 - creative_q)

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
                    f"*Creative quality:* {creative_bar}\n"
                    f"*Engagement:* {analysis.get('engagement_signal', 'unknown')}\n"
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

    if analysis.get("why_it_works"):
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f":bulb: *Why it works:* {analysis['why_it_works']}"},
        })

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
        "text": f"{analysis['competitor']['name']} creative analysis",
        "blocks": blocks,
    }
