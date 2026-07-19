# Contractor Research & Monitoring Plan

How to identify, verify, and monitor national service contractors as Vendor Connect anchor targets via the Meta Ads Library pipeline.

---

## Why Monitor Contractors

Contractors are the supply side of VendorBids' Vendor Connect marketplace — the service companies that property managers source through VendorBids. Monitoring their Facebook ads reveals:

1. **How contractors market to PMs** — Messaging, value props, and pain points they address
2. **Service expansion signals** — New service lines or geographic expansion = partnership opportunities
3. **Pricing intelligence** — Promotions and pricing language in ads
4. **Seasonal patterns** — When different trades ramp up advertising (aligns with PM procurement cycles)
5. **Competitive positioning** — How contractors differentiate, which is intel for VendorBids' vendor profiles

---

## Current Contractor Watchlist (as of 2026-07-18)

### Active on Facebook (in `competitors.yaml`, monitored weekly)

| Contractor | Page ID | Trade | Revenue | Why Monitor |
|------------|---------|-------|---------|-------------|
| **ABM Industries** | 372746739468695 | Facility maintenance, janitorial | $8B+ | Dedicated multifamily division serving 65K+ units. Anchor vendor target. |
| **TruGreen** | 209263565751147 | Lawn, landscaping | $1.5B+ | Largest US lawn service. Heavy consumer Meta ad spend, good signal source. |
| **Cintas Corporation** | 10401757259 | Facility services, uniforms, safety | $9B+ | Fortune 500. National presence. Serves multifamily through facility services division. |
| **Terminix** | 508491589196941 | Pest control, home services | $2B+ | National brand with commercial/multifamily contracts. Heavy Meta advertiser. |
| **Stanley Steemer** | 170576306526 | Carpet/floor cleaning | $500M+ | National franchise. Turn/make-ready cleaning is core multifamily need. |
| **Mr. Rooter Plumbing** | 123981044293884 | Plumbing | Franchise | Neighborly brand. Strong local FB ad programs show franchise model marketing. |
| **Davey Tree** | 5846269801 | Tree, landscape | $1.5B+ | National commercial coverage. Grounds maintenance for large portfolios. |

### Not on Facebook (B2B-only or no ads found)

| Contractor | Trade | Notes | Alternative Monitoring |
|------------|-------|-------|----------------------|
| **BrightView** | Landscaping | Largest US commercial landscaper. No FB ads found. | LinkedIn, SEC filings, bid proposals |
| **Comfort Systems USA** | HVAC | NYSE:FIX. B2B/recruiting ads only, not service marketing. | SEC filings, industry events |
| **Lessen (fka SMS Assist)** | Tech-enabled maintenance | More of a platform competitor than a vendor. | LinkedIn, funding news, AppFolio integration |
| **EMCOR Group** | MEP services | Fortune 500 MEP. Purely B2B, no consumer ads. | SEC filings, press releases |

---

## How Contractors Were Selected

### Selection Criteria

1. **Multifamily relevance** — Must serve property management companies, not just residential consumers
2. **National footprint** — Can serve operators across multiple markets (scalable for Vendor Connect)
3. **Trade diversity** — Cover the core maintenance categories: HVAC, plumbing, landscaping, pest control, janitorial, cleaning, electrical
4. **Revenue/scale** — Large enough to be anchor vendors on the platform
5. **Advertising activity** — Running Facebook ads provides monitoring signal

### Trade Coverage Map

| Trade | Monitored | Gap |
|-------|-----------|-----|
| Facility maintenance / janitorial | ABM Industries | — |
| Landscaping / lawn | TruGreen, Davey Tree | BrightView (no FB ads) |
| HVAC | — | Comfort Systems USA (B2B only). Consider: Trane, Carrier franchise networks |
| Plumbing | Mr. Rooter | Consider: Roto-Rooter (only regional pages found) |
| Pest control | Terminix | Consider: Orkin, Rentokil |
| Cleaning (carpet/floor) | Stanley Steemer | — |
| Facility services / safety | Cintas | — |
| Electrical | — | Gap: research ARS/One Hour (Neighborly brands), Mr. Electric |
| Roofing | — | Gap: research national commercial roofers |
| Painting | — | Gap: research CertaPro, Five Star Painting |

### Research Sources

- **Multifamily industry reports** — Which vendors PMs most commonly contract
- **Neighborly/franchise networks** — Brands that operate at national scale via franchises
- **Meta Ads Library** — Verified which contractors actively advertise on Facebook
- **Trade association directories** — BOMA, IREM vendor partners

### Key Finding

National contractors fall into two distinct advertising patterns:
1. **Consumer-facing brands** (TruGreen, Terminix, Stanley Steemer) — Heavy Meta ad spend targeting homeowners. Their ads reveal pricing, seasonal campaigns, and service positioning.
2. **B2B/institutional brands** (BrightView, EMCOR, Comfort Systems) — No Facebook ads. They market through direct sales, RFPs, and trade events.

The consumer-facing brands are more useful for monitoring because their ads reveal market intelligence. The B2B brands need alternative monitoring (LinkedIn, earnings calls, industry events).

---

## How to Get Contractor Facebook Page IDs

### Method: Playwright Scrape of Meta Ads Library

Same approach as competitor and operator scraping:

1. Search `facebook.com/ads/library/?q=CONTRACTOR_NAME&search_type=page&country=US`
2. Wait 6+ seconds for SPA render
3. Extract `"page_id"` + `"page_name"` pairs from page source
4. Match against contractor name

### Common Pitfalls

- **Franchise vs. corporate**: "Roto-Rooter" matched "Roto-Rooter of Northern Michigan" (franchise location), not the national corporate page. Search specifically for "[Brand] corporate" or check if the page ID corresponds to the national account.
- **Brand name collisions**: "Cintas" matched "Cintas Modeladoras" (shapewear company) initially. Use full company names like "Cintas Corporation."
- **Parent company vs. brand**: Some contractors operate multiple brands (e.g., Neighborly owns Mr. Rooter, Mr. Electric, One Hour Heating). Each brand has its own page.

---

## When to Re-Run Contractor Research

- **Quarterly**: Check if B2B-only contractors have started Facebook advertising
- **When filling trade gaps**: Research contractors in HVAC, electrical, roofing, painting
- **When a contractor raises or IPOs**: Growth capital = geographic expansion = more ad spend
- **When VendorBids enters a new trade vertical**: Research the dominant contractors in that trade

## Signals to Watch in Contractor Ads

| Signal | What It Means for VendorBids |
|--------|------------------------------|
| "Commercial services" or "property management" in ads | Actively targeting PM buyers — warm lead for Vendor Connect |
| Geographic expansion campaigns | New market = vendor supply opportunity |
| "24/7 emergency service" messaging | Positioning for maintenance dispatch — competes with Lula model |
| Seasonal campaigns (spring landscaping, winter HVAC) | Aligns with PM procurement cycles — time outreach accordingly |
| Franchise recruitment ads | Growing network = more local coverage for Vendor Connect |
| Pricing/promotion language | Market rate intelligence for VendorBids pricing benchmarks |
