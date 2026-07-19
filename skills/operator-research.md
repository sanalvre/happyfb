# Operator Research & Monitoring Plan

How to identify, verify, and monitor multifamily property management companies (operators) as VendorBids buyer personas via the Meta Ads Library pipeline.

---

## Why Monitor Operators

Operators are VendorBids' primary buyer persona — the property management companies that would use VendorBids to source, vet, and manage their vendor relationships. Monitoring their Facebook ads reveals:

1. **Growth signals** — New market leasing campaigns = new maintenance vendor needs
2. **Pain point language** — How they describe operational challenges (maintenance, turns, vendor management)
3. **Hiring patterns** — Recruiting for maintenance roles signals growing vendor spend
4. **Technology adoption** — Ads mentioning "smart home," "resident portal," etc. indicate proptech openness
5. **Budget cycles** — Seasonal ad patterns correlate with budget allocation timing

---

## Current Operator Watchlist (as of 2026-07-18)

### Active on Facebook (in `competitors.yaml`, monitored weekly)

| Operator | Page ID | Units | Focus | Why Monitor |
|----------|---------|-------|-------|-------------|
| **MAA Communities** | 103664019160 | ~100K | Sun Belt REIT | High unit count, tech-forward operations, active leasing advertiser |
| **Bozzuto** | 7401734044 | ~80K+ | East Coast | Known early-adopter profile, polished marketing = tech-forward |
| **Cushman & Wakefield** | 100880444424 | Enterprise | Commercial + multifamily | Major PM with centralized procurement — enterprise deal potential |
| **Morgan Properties** | 107607564525212 | Large | East Coast | Active Meta advertiser, growing portfolio |
| **Brookfield Properties** | 104231984825455 | Institutional | Multi-sector | Institutional owner, large maintenance budgets |
| **Equity Residential** | 24542358504 | ~80K | Urban/coastal REIT | REIT scale, active leasing ads reveal market strategy |
| **Cortland Living** | 219314998208128 | ~86K | Sun Belt | Fast-growing, industry-known proptech early adopter |
| **RPM Living** | 311212508919910 | ~241K | Sun Belt | Aggressive growth, tech-modernization narrative |

### Not on Facebook (enterprise operators — monitor elsewhere)

| Operator | Units | Notes | Alternative Monitoring |
|----------|-------|-------|----------------------|
| **Greystar** | ~1M | Largest US PM. No corporate FB ad page. | LinkedIn, NMHC reports, press releases |
| **Lincoln Property** | Large | Private. Unverifiable FB presence. | LinkedIn, industry events |
| **Camden Property Trust** | ~60K | REIT. Only individual community pages (not corporate). | SEC filings, LinkedIn |
| **AvalonBay Communities** | ~90K | REIT. Only individual community pages. | SEC filings, LinkedIn |
| **Alliance Residential** | Mid-size | No corporate FB page found. | LinkedIn, industry events |
| **Avenue5 Residential** | ~100K | No FB page found. Growing 3rd-party PM. | LinkedIn, hiring activity |
| **ZRS Management** | ~97K | No FB page found. Sun Belt focused. | LinkedIn, property listing sites |

---

## How Operators Were Selected

### Selection Criteria

1. **Unit count** — Target operators managing 50K+ units (enterprise deal size for VendorBids)
2. **Growth trajectory** — Actively expanding portfolios = growing vendor needs
3. **Geographic focus** — Sun Belt and urban/coastal markets have highest construction/maintenance activity
4. **Technology posture** — Operators known for proptech adoption are better early targets
5. **Advertising activity** — Running Facebook ads indicates marketing sophistication and budget

### Research Sources

- **NMHC Top 50** — National Multifamily Housing Council rankings by units managed
- **REIT investor relations** — Public portfolio and growth metrics
- **Industry press** — Multifamily Executive, GlobeSt, Multi-Housing News
- **Meta Ads Library** — Verified which operators actively advertise on Facebook

### Key Finding

Most large operators run Facebook ads at the **individual community level** (e.g., "Camden Crossings Apartments") rather than at the **corporate level**. This means:
- Corporate brand-level monitoring catches leasing campaigns and employer branding
- Individual community pages (thousands of them) are NOT practical to monitor
- The operators in our watchlist are the ones with **active corporate-level** ad accounts

---

## How to Get Operator Facebook Page IDs

### Method: Playwright Scrape of Meta Ads Library

1. Search `facebook.com/ads/library/?q=OPERATOR_NAME&search_type=page&country=US`
2. Wait 6+ seconds for SPA to render
3. Extract `"page_id"` and `"page_name"` pairs from page source via regex
4. Match against operator name (watch for local community pages with similar names)

### Common Pitfalls

- **Community vs. corporate pages**: "Camden" matches "Camden Crossings Apartments" (local community), not Camden Property Trust (corporate). Always verify the match is the national/corporate entity.
- **Franchise brands**: Some operators run multiple regional brands under one parent company.
- **Name collisions**: "Cortland" matched "Cortland Line" (fishing company) initially. Use specific search terms like "Cortland Apartments" or "Cortland Living."

---

## When to Re-Run Operator Research

- **Quarterly**: Check if operators without FB pages have started advertising
- **When a target operator acquires portfolios**: M&A activity = vendor procurement changes
- **When entering a new market**: Research the dominant operators in that geography
- **NMHC Top 50 release**: Compare against watchlist for new entrants

## Signals to Watch in Operator Ads

| Signal | What It Means for VendorBids |
|--------|------------------------------|
| Leasing ads in new markets | Expansion = new vendor sourcing needs |
| "Now hiring maintenance" | Growing in-house team OR can't find good vendors |
| "Smart home" / "AI" messaging | Tech-forward, likely to adopt proptech tools |
| Renovation/upgrade campaigns | Capital projects = contractor bidding opportunity |
| Brand refresh / rebrand | New leadership, often comes with vendor re-evaluation |
