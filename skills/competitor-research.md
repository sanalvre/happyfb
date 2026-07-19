# Competitor Research & Facebook Page ID Acquisition

How to identify VendorBids competitors, determine which ones run Facebook ads, and get their page IDs for the monitoring pipeline.

---

## Current Competitor Landscape (as of 2026-07-18)

### Active on Facebook (in `competitors.yaml`, monitored weekly)

| Company | Page ID | Threat | Why monitor |
|---------|---------|--------|-------------|
| **ServiceTitan** | 179317675454866 | watch | Field service mgmt for HVAC/plumbing/electrical trades. Vendor-side platform, heavy Meta ad spend. Shows us how contractors market themselves. |
| **Procore Technologies** | 47927849135 | adjacent | Construction bid management. Overlaps on capital projects. Active advertiser. |
| **AppFolio** | 75233933923 | adjacent | All-in-one PMS with Vendor Portal + Lula partnership. SMB-focused, active Meta advertiser. |
| **Property Meld** | 718426831581337 | adjacent | Maintenance/work-order mgmt with vendor dispatch. Competes for same maintenance-coordination budget. |

### NOT on Facebook (enterprise B2B — monitor via other channels)

These companies were verified to have **no Facebook ad presence** via Playwright scraping of the Meta Ads Library. They use ABM, events, and direct sales.

| Company | Threat | Overlap with VendorBids | Alternative monitoring |
|---------|--------|------------------------|----------------------|
| **NetVendor** | critical | Direct competitor. Compliance-led vendor credentialing for multifamily (100K+ vendor network). Acquired Nov 2025. | LinkedIn, blog comparison pages, G2 |
| **Revyse** | critical | AI vendor intelligence + marketplace for multifamily. $2M seed (RET Ventures). Nearly identical positioning. | LinkedIn ads, blog, PR/funding news |
| **VendorPM** | critical | Software-enabled vendor marketplace for PMs. 50K+ vendors, 100+ PM groups. Closest positioning to VendorBids. | LinkedIn, website changes, G2 |
| **Yardi** | critical | VendorShield credentialing + Procure-to-Pay suite. Enterprise incumbent with platform lock-in. | Industry events, Yardi blog, partner announcements |
| **RealPage** | critical | Vendor Credentialing + Onboarding connecting 12K+ PMs to vendor network. | RealPage blog, SEC filings, press releases |
| **HqO** | adjacent | Tenant experience platform with dedicated Vendor product (discovery, compliance, contracting). CRE-focused. | LinkedIn, product page changes |
| **Entrata** | adjacent | Procure-to-Pay module via NetVendor integration (Oct 2024). | Entrata blog, partner announcements |
| **Jones (getjones.com)** | adjacent | AI COI/insurance compliance for CRE. Narrower scope (compliance only, not sourcing/bidding). | LinkedIn, website |
| **Tailorbird** | adjacent | AI capital projects/bidding for multifamily + affordable housing. Competes on capex/turn work. | LinkedIn, funding news |
| **Lula** | adjacent | Vendor network for maintenance dispatch. AppFolio Smart Maintenance partner. 9K+ vetted pros, 50+ markets. | App store listings, AppFolio integration page |

### Suggested additions to monitor (if they start running Facebook ads)

- **illumend (fka myCOI)** — AI-driven COI/insurance compliance. Rebranded 2026. Same space as Jones.
- **Buildium** — PMS with vendor management features. Mid-market multifamily.
- **Rent Manager** — PMS with maintenance management. Integrates with Property Meld.

---

## How to get a Facebook Page ID

### Method 1: Meta Ads Library (best for companies that run ads)

1. Go to https://www.facebook.com/ads/library/
2. Set country to "United States", ad type to "All ads"
3. Search the company name
4. If results appear, click "See all ads from this Page"
5. The URL will contain `view_all_page_id=XXXXXXXXXXXX` — that number is the page ID

**Limitation:** If the company doesn't run Facebook ads, no results appear and you can't find their page.

### Method 2: Facebook Page source (if you know their FB page URL)

1. Go to the company's Facebook page (e.g., facebook.com/ServiceTitan)
2. View Page Source (Ctrl+U)
3. Search for `"pageID"` — the value is their page ID
4. Alternative: search for `"page_id"` or `"entity_id"`

### Method 3: Playwright automation (what we used)

Run a Playwright script that:
1. Navigates to `facebook.com/ads/library/?q=COMPANY_NAME&search_type=page`
2. Waits for the SPA to render (6+ seconds)
3. Regex-extracts `"page_id":"XXXX"` and `"page_name":"YYYY"` pairs from the page source
4. Matches the company name against results

**Key finding from our scrape:** The Ads Library renders page_id/page_name in embedded JSON in the HTML source, even without login. The `view_all_page_id` links only render for logged-in users, but the raw data is in the source.

**Script location:** Not committed (scratchpad only). The approach is:
```python
content = await page.content()
for m in re.finditer(r'"page_id"\s*:\s*"(\d+)"', content):
    pid = m.group(1)
    # Look for page_name within 500 chars
    ctx = content[max(0,m.start()-500):m.end()+500]
    name = re.search(r'"page_name"\s*:\s*"([^"]+)"', ctx)
```

### Method 4: Graph API (requires token)

Once you have META_ACCESS_TOKEN, you can verify page IDs:
```bash
curl "https://graph.facebook.com/v21.0/PAGE_ID?fields=name,website,fan_count&access_token=TOKEN"
```

---

## When to re-run competitor research

- **Quarterly:** Check if any of the "no Facebook ads" companies have started advertising (especially Revyse, VendorPM, and Lula — growth-stage startups most likely to start paid social)
- **When a competitor raises funding:** Fundraising usually leads to increased ad spend within 3-6 months
- **When a competitor launches a new product:** New feature launches often have ad campaigns
- **When you hear about a new competitor:** Add them to the monitoring list

## Threat level definitions

| Level | Meaning | Examples |
|-------|---------|---------|
| **critical** | Direct competitor for the same buyer (multifamily PM) and same use case (vendor sourcing/procurement) | NetVendor, Revyse, VendorPM, Yardi, RealPage |
| **adjacent** | Overlapping product or buyer, but different primary use case | Procore (construction), AppFolio (PMS), HqO (CRE), Property Meld (maintenance) |
| **watch** | Shares the vendor/contractor ecosystem but different buyer or approach | ServiceTitan (vendor-side), Lula (dispatch) |
