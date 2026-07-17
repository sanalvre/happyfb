import json
import os

import requests

from .logging_config import get_logger

try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3

log = get_logger("enrich")

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-haiku-4.5")

ENRICHMENT_PROMPT = """You are a lead qualification analyst for VendorBids, a procurement platform
that connects multifamily property management companies with service contractors
(HVAC, plumbing, electrical, landscaping, etc.).

Analyze this contractor's Facebook ad to assess whether they would be a good fit
for the VendorBids Vendor Connect network.

## Contractor info
Page name: {page_name}
Trade: {trade}
Number of active ads: {ad_count}
Sample ad text: {sample_ad_text}

## Your task
Return ONLY a JSON object with these fields:

1. `relevance_score` - integer 1-5, where 1 is poor fit and 5 is ideal fit for
   VendorBids. Score higher if they serve commercial or multifamily properties.
   Score lower if they are clearly residential-only or a national franchise.

2. `serves_multifamily` - boolean. Based on the ad copy, do they appear to serve
   multifamily, commercial, or property management clients? If unclear, false.

3. `company_size_signal` - one of: "small", "midsize", "large", "unknown".
   Infer from ad copy, branding, service area mentions.

4. `city` - city name if mentioned or inferrable from the ad. null if unknown.

5. `state` - US state abbreviation if mentioned or inferrable. null if unknown.

6. `notes` - one sentence: why is this contractor a good or bad fit for VendorBids?

Do not use em dashes. Use commas or parentheses instead.
"""


def enrich_contractor(contractor: dict, api_key: str | None = None) -> dict:
    """Use LLM to score and enrich a contractor lead."""
    key = api_key or OPENROUTER_KEY
    if not key:
        raise ValueError("OPENROUTER_KEY is required")

    prompt = ENRICHMENT_PROMPT.format(
        page_name=contractor["page_name"],
        trade=contractor["trade"],
        ad_count=contractor.get("ad_count", 1),
        sample_ad_text=contractor.get("sample_ad_text", "N/A"),
    )

    log.debug("Enriching %s (%s)", contractor["page_name"], contractor["trade"])

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        },
        timeout=60,
    )
    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    log.debug("Enrichment result for %s: relevance=%s, multifamily=%s",
              contractor["page_name"],
              parsed.get("relevance_score"),
              parsed.get("serves_multifamily"))
    return parsed


def fetch_page_contact(page_id: str, access_token: str | None = None) -> dict:
    """Fetch publicly available contact info from a Facebook Page."""
    token = access_token or ACCESS_TOKEN
    if not token:
        raise ValueError("META_ACCESS_TOKEN is required")

    fields = "name,website,phone,emails,single_line_address,category"
    url = f"https://graph.facebook.com/v21.0/{page_id}"

    log.debug("Fetching contact info for page %s", page_id)

    response = requests.get(
        url,
        params={"access_token": token, "fields": fields},
        timeout=30,
    )

    if response.status_code == 400:
        log.debug("Page %s not accessible (may require permissions)", page_id)
        return {}

    response.raise_for_status()
    data = response.json()

    contact = {}
    if data.get("website"):
        contact["website"] = data["website"]
    if data.get("phone"):
        contact["phone"] = data["phone"]
    if data.get("emails"):
        contact["email"] = data["emails"][0]
    if data.get("single_line_address"):
        contact["address"] = data["single_line_address"]

    log.debug("Contact info for %s: %s", page_id, list(contact.keys()))
    return contact


def enrich_contractors(contractors: list[dict], db: sqlite3.Connection,
                       api_key: str | None = None,
                       access_token: str | None = None) -> list[dict]:
    """Enrich a batch of contractors with LLM scoring and contact info."""
    enriched = []

    for c in contractors:
        try:
            analysis = enrich_contractor(c, api_key=api_key)

            try:
                relevance = int(float(analysis.get("relevance_score", 1)))
            except (ValueError, TypeError):
                relevance = 1
            relevance = max(1, min(5, relevance))

            contact = {}
            try:
                contact = fetch_page_contact(c["page_id"], access_token=access_token)
            except Exception as e:
                log.warning("Could not fetch contact for %s: %s", c["page_name"], e)

            db.execute("""
                UPDATE contractors SET
                    relevance_score = ?,
                    serves_multifamily = ?,
                    company_size_signal = ?,
                    city = ?,
                    state = ?,
                    notes = ?,
                    website = ?,
                    phone = ?,
                    email = ?
                WHERE page_id = ?
            """, (
                relevance,
                analysis.get("serves_multifamily", False),
                analysis.get("company_size_signal", "unknown"),
                analysis.get("city"),
                analysis.get("state"),
                analysis.get("notes"),
                contact.get("website"),
                contact.get("phone"),
                contact.get("email"),
                c["page_id"],
            ))

            c.update({
                "relevance_score": relevance,
                "serves_multifamily": analysis.get("serves_multifamily", False),
                "company_size_signal": analysis.get("company_size_signal", "unknown"),
                "city": analysis.get("city"),
                "state": analysis.get("state"),
                "notes": analysis.get("notes"),
                "website": contact.get("website"),
                "phone": contact.get("phone"),
                "email": contact.get("email"),
            })
            enriched.append(c)

        except Exception as e:
            log.error("Enrichment failed for %s: %s", c.get("page_name", "?"), e)
            enriched.append(c)

    db.commit()
    log.info("Enriched %d contractors", len(enriched))
    return enriched
