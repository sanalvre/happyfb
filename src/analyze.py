import json
import os

import requests
from pathlib import Path

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-haiku-4.5")
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "weekly_analysis.md"


def analyze_competitor(competitor: dict, diff: dict, prior_themes: list,
                       api_key: str | None = None) -> dict:
    """Send competitor diff to LLM for theme extraction and threat assessment."""
    key = api_key or OPENROUTER_KEY
    if not key:
        raise ValueError("OPENROUTER_KEY is required")

    prompt = PROMPT_PATH.read_text().format(
        competitor_name=competitor["name"],
        threat_level=competitor["threat_level"],
        competitor_notes=competitor.get("notes", ""),
        week_of=diff["week_of"],
        new_ads_count=diff["new_count"],
        ended_ads_count=diff["ended_count"],
        active_count=diff["active_count"],
        prev_active_count=diff["prev_active_count"],
        new_ads_json=json.dumps(diff["new"], indent=2, default=str),
        ended_ads_json=json.dumps(diff["ended"], indent=2, default=str),
        prior_themes=json.dumps(prior_themes, indent=2, default=str),
    )

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        },
        timeout=60,
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def build_analysis_result(competitor: dict, diff: dict, analysis: dict) -> dict:
    """Merge competitor info, diff stats, and LLM analysis into one result."""
    return {
        "competitor": competitor,
        "headline": analysis.get("headline", "steady state, no notable changes."),
        "themes": analysis.get("themes", []),
        "messaging_shift": analysis.get("messaging_shift"),
        "icp_signal": analysis.get("icp_signal", "unclear"),
        "threat_assessment": analysis.get("threat_assessment", 1),
        "notable_creatives": analysis.get("notable_creatives", []),
        "suggested_action": analysis.get("suggested_action"),
        "new_count": diff["new_count"],
        "ended_count": diff["ended_count"],
        "active_count": diff["active_count"],
        "diff": diff,
    }
