# Pivot: Contractor Lead Discovery + Viral Ad Tracking

**Date:** 2026-07-16
**Status:** Planned

---

## What's changing

The pipeline is expanding from pure competitor monitoring into two tracks:

### Track 1: Contractor Lead Discovery (new, primary focus)

**Goal:** Find small-to-midsize contractors (HVAC, plumbing, electrical, landscaping, etc.) who could be onboarded into the VendorBids Vendor Connect network.

**Why Meta Ads Library:** Contractors who are actively advertising on Facebook are growth-oriented, have marketing budget, and are actively seeking new clients — exactly the profile that benefits from being listed on a procurement platform like VendorBids. The Ads Library is free and gives us their Facebook Page ID, which we can use to find contact info.

**How it works:**

1. **Search by trade keywords** — Query the Meta Ads Library API with `search_terms` like "HVAC contractor", "plumbing services", "commercial landscaping", etc. Filter to US ads.
2. **Deduplicate** — Track discovered contractors in a new `contractors` table. Only surface new finds each week.
3. **Enrich with LLM** — Send ad creatives to Claude Haiku to extract: company size signals, service area, specialties, and whether they serve commercial/multifamily properties (vs. residential-only).
4. **Extract contact info** — Pull publicly available contact details from their Facebook Page (website, phone, email) via the Graph API's Page endpoint.
5. **Deliver to Slack** — Weekly digest of new contractor leads with contact info, trade category, and relevance score.

**Target trades** (aligned with VendorBids service categories):

| Trade | Search terms |
|-------|-------------|
| HVAC | "HVAC contractor", "heating and cooling", "air conditioning service" |
| Plumbing | "plumbing contractor", "plumbing services", "commercial plumber" |
| Electrical | "electrical contractor", "electrician services", "commercial electrician" |
| Landscaping | "landscaping company", "commercial landscaping", "property maintenance" |
| Painting | "painting contractor", "commercial painting", "interior painting" |
| Roofing | "roofing contractor", "commercial roofing", "roof repair" |
| Cleaning | "janitorial services", "commercial cleaning", "property cleaning" |
| General maintenance | "property maintenance", "building maintenance", "facility services" |

### Track 2: Competitor Viral Ad Tracking (modified existing)

**Goal:** Keep tracking competitor ads, but shift the analysis from "threat assessment" to "virality and creative quality" so marketing can identify which competitor campaigns are performing well and mirror the approach.

**What changes:**

- **LLM prompt**: Instead of threat_assessment (1-5), analyze for creative_quality (1-5), estimated_engagement (low/medium/high), and what makes the ad compelling
- **Digest format**: Highlight "top creatives to study" instead of "threats to respond to"
- **New fields**: `creative_quality`, `engagement_signal`, `why_it_works` (LLM-generated explanation of what makes the ad effective)

---

## New files

| File | Purpose |
|------|---------|
| `config/trades.yaml` | Trade categories and search terms for contractor discovery |
| `src/discover.py` | Searches Ads Library by trade keywords, deduplicates, returns new contractor leads |
| `src/enrich.py` | Extracts contact info from Facebook Pages via Graph API, LLM enrichment for lead scoring |

## Modified files

| File | Change |
|------|--------|
| `schema.sql` | Add `contractors` table and `contractor_leads` FTS index |
| `src/analyze.py` | Update prompt to include virality/creative analysis alongside existing fields |
| `src/digest.py` | Add contractor leads section to Slack digest |
| `src/main.py` | Add contractor discovery phase to pipeline orchestration |
| `config/competitors.yaml` | No changes (keep existing competitor list) |

---

## Schema additions

```sql
CREATE TABLE IF NOT EXISTS contractors (
  page_id TEXT PRIMARY KEY,
  page_name TEXT NOT NULL,
  trade TEXT NOT NULL,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',    -- 'new' | 'contacted' | 'qualified' | 'skip'
  website TEXT,
  phone TEXT,
  email TEXT,
  city TEXT,
  state TEXT,
  ad_count INTEGER DEFAULT 0,
  relevance_score INTEGER,               -- 1-5, LLM-assessed fit for VendorBids
  serves_multifamily BOOLEAN,            -- LLM-detected from ad copy
  company_size_signal TEXT,              -- 'small' | 'midsize' | 'large' | 'unknown'
  sample_ad_text TEXT,
  notes TEXT,
  raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_contractors_trade ON contractors(trade);
CREATE INDEX IF NOT EXISTS idx_contractors_status ON contractors(status);
```

## Analysis prompt changes

The competitor analysis prompt gets two new output fields:

```json
{
  "headline": "...",
  "themes": ["..."],
  "messaging_shift": "...",
  "icp_signal": "...",
  "threat_assessment": 3,
  "creative_quality": 4,
  "engagement_signal": "high",
  "why_it_works": "Strong social proof with customer count, clear ROI claim, urgency via limited-time pricing",
  "notable_creatives": ["ad_001"],
  "suggested_action": "..."
}
```

The existing `threat_assessment` stays for internal tracking. The new `creative_quality` and `why_it_works` fields are what surfaces in the Slack digest for marketing.

---

## Slack digest changes

The weekly digest becomes two sections:

**Section 1: New Contractor Leads** (primary)

> **New contractor leads: week of 2026-07-21**
>
> **12 new contractors found across 5 trades.**
>
> ---
> **HVAC (4 new)**
> - ABC Heating & Cooling — Phoenix, AZ — abcheating.com — Relevance: 4/5
>   _"Serving multifamily properties since 2018. 24/7 emergency service."_
> - ...
>
> **Plumbing (3 new)**
> - ...

**Section 2: Competitor Creative Watch** (secondary, threaded)

> **Top competitor creatives this week**
>
> :star: **NetVendor** — Creative quality: 4/5
> _"Reduce vendor costs by 30% — join 500+ properties"_
> **Why it works:** Strong social proof (500+ properties), specific ROI claim (30%), addresses pain point directly
>
> **Revyse** — Creative quality: 3/5
> _"AI-powered vendor discovery for property managers"_
> **Why it works:** Clear AI differentiation, targets specific ICP

---

## Cost impact

| Item | Before | After | Notes |
|------|--------|-------|-------|
| Meta Ads Library API | Free | Free | More queries (trade searches), but still free |
| Graph API (page info) | N/A | Free | Basic page public info |
| OpenRouter (Claude Haiku) | ~$0.50/mo | ~$2-5/mo | More LLM calls for contractor enrichment |
| **Total** | **~$0.50/mo** | **~$2-5/mo** | Still negligible |

The main cost increase is LLM calls for contractor lead enrichment. Each new contractor gets one Haiku call to assess relevance and extract signals from their ad copy. With ~50-100 new contractors per week across all trades, that's ~$2-5/month.

---

## Implementation order

1. Add `contractors` table to schema
2. Create `config/trades.yaml` with search terms
3. Build `src/discover.py` — search + deduplicate
4. Build `src/enrich.py` — contact info + LLM scoring
5. Update `src/analyze.py` — add virality fields to competitor prompt
6. Update `src/digest.py` — two-section digest (leads + creatives)
7. Update `src/main.py` — orchestrate both tracks
8. Add tests for new modules
9. Update workflow if needed
