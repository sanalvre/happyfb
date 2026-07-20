# Category-Aware Pipeline Plan

Fixes needed after adding operators/contractors to `competitors.yaml` with the `category` field.

---

## Problems Found

### 1. LLM prompt is competitor-only
`prompts/weekly_analysis.md` says "You review a competitor's Meta advertising activity" and asks for `threat_assessment`. For operators (VendorBids buyers), the analysis should be about **buyer intelligence** — growth signals, pain points, vendor needs. For contractors, it should be about **vendor intelligence** — how they market to PMs, pricing, service expansion.

### 2. Digest labels everything as "competitors"
`digest.py` parent message says "X of Y competitors had notable activity". With 8 operators and 7 contractors mixed in, this produces a confusing Slack message.

### 3. No CLI category filter
`--competitor` filters by name, but there's no way to run just one category (e.g., only competitors for a quick check).

---

## Implementation

### Step 1: Category-aware prompts
- Add `prompts/operator_analysis.md` — buyer intelligence framing: growth signals, vendor need signals, tech adoption, instead of threat assessment
- Add `prompts/contractor_analysis.md` — vendor intelligence framing: how they market to PMs, service positioning, pricing signals
- Modify `analyze.py` to select prompt by category, default to existing competitor prompt

### Step 2: Category-aware digest
- Group analyses by category in `digest.py`
- Separate parent messages: "Competitor creative watch", "Operator intelligence", "Vendor intelligence"
- Separate reply files per category (e.g., `operator_parent.json`, `operator_reply_00_*.json`)

### Step 3: Workflow + CLI updates
- Add `--category` CLI flag to filter by category
- Update `weekly-digest.yml` to handle operator/contractor Slack messages

### Step 4: Tests
- Update `test_integration.py` for category-aware behavior
- Update `test_digest.py` for segmented output

---

## Analysis field mapping by category

| Field | Competitor | Operator | Contractor |
|-------|-----------|----------|------------|
| `headline` | Competitive threat summary | Buyer activity summary | Vendor marketing summary |
| `threat_assessment` | 1-5 threat to VendorBids | 1-5 sales opportunity score | 1-5 partnership opportunity score |
| `icp_signal` | Who they target | What services they need | Who they target (PMs vs consumers) |
| `themes` | Messaging themes | Growth/pain themes | Service/pricing themes |
| `suggested_action` | Competitive response | Sales outreach action | Partnership outreach action |
