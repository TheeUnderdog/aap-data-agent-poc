# Power BI Report Specifications — AAP Rewards & Loyalty POC

**Document Version:** 1.0  
**Last Updated:** 2026-07  
**Status:** Ready for Development  
**Audience:** Power BI Report Developers, Business Analysts

---

## Overview

This document specifies five Power BI reports for the AAP Rewards & Loyalty POC. Each report connects to the Fabric SQL Analytics Endpoint (`semantic` schema) and visualizes data from one or more semantic views. All reports use consistent styling, navigation, and professional design practices suitable for executive and operational stakeholder audiences.

### Data Source Connection — All Reports

- **Endpoint:** Fabric SQL Analytics Endpoint (Lakehouse SQL Endpoint)
- **Schema:** `semantic`
- **Authentication:** Service Principal / Entra ID
- **Refresh Cadence:** Daily (configurable; sample data updates nightly)
- **Visuals:** All pull live data; no static imports

---

## Report 1: Member Insights Dashboard

**Audience:** Loyalty Program Manager, VP of Customer Experience  
**Focus:** Member demographics, tier distribution, engagement health  
**Semantic Views:** `v_member_summary`, `v_member_engagement`

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  MEMBER INSIGHTS DASHBOARD                                      │
├─────────────────────────────────────────────────────────────────┤
│ [Date Range Slicer] | [Tier Filter] | [Refresh Status]          │
├─────────────────────────────────────────────────────────────────┤
│  Active Members (Card)    │    Avg Engagement Score (Card)       │
│  Total Points Outstanding │    YoY Member Growth (Card)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Members by Tier (Stacked Bar Chart)    │  Engagement by Activity │
│  [Platinum | Gold | Silver | Bronze]    │  (Line Chart with Trend)│
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Member Enrollment Trend (Area Chart)   │  Last Visit Distribution│
│  [Monthly enrollments + cumulative]     │  (Donut: 0-30d / 30-60d │
│                                         │  / 60-90d / 90d+)       │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Member Details Table (Sortable)                                │
│  [Member ID] [Name] [Tier] [Join Date] [Lifetime Spend] [Status]│
└─────────────────────────────────────────────────────────────────┘
```

### Key Measures / DAX

```
Active Members = 
  CALCULATE(DISTINCTCOUNT(v_member_summary[member_id]), 
    v_member_summary[status] = "Active")

Avg Engagement Score = 
  AVERAGE(v_member_engagement[engagement_score])

YoY Member Growth % = 
  VAR CurrentYear = YEAR(TODAY())
  VAR PriorYear = CurrentYear - 1
  VAR CurYearMembers = CALCULATE(DISTINCTCOUNT(v_member_summary[member_id]), 
    YEAR(v_member_summary[join_date]) = CurrentYear)
  VAR PriorYearMembers = CALCULATE(DISTINCTCOUNT(v_member_summary[member_id]), 
    YEAR(v_member_summary[join_date]) = PriorYear)
  RETURN DIVIDE(CurYearMembers - PriorYearMembers, PriorYearMembers, 0)

Total Points Outstanding = 
  SUM(v_member_summary[points_balance])

Member Count by Tier = 
  DISTINCTCOUNT(v_member_summary[member_id])

Avg Last Visit (Days Ago) = 
  AVERAGE(v_member_engagement[days_since_last_visit])
```

### Visuals

| Visual | Type | Fields | Description |
|--------|------|--------|-------------|
| Active Members | Card | `Active Members` measure | Display current active member count |
| Avg Engagement Score | Card | `Avg Engagement Score` measure | Display average engagement (0-100) |
| Total Points Outstanding | Card | `Total Points Outstanding` measure | Display aggregate liability |
| YoY Member Growth | Card | `YoY Member Growth %` measure | Display percentage growth |
| Members by Tier | Stacked Bar | **Axis:** `member_tier` | **Value:** `Member Count by Tier` | Shows distribution across all tiers |
| Engagement by Activity Level | Line Chart | **Axis:** `v_member_engagement[last_visit]` (binned monthly) | **Value:** `Avg Engagement Score` | Trend of engagement over time |
| Member Enrollment Trend | Area Chart | **Axis:** `v_member_summary[join_date]` (binned monthly) | **Value:** `Member Count by Tier` (stacked by tier) | New enrollments + cumulative |
| Last Visit Distribution | Donut | **Legend:** Binned `days_since_last_visit` (0-30, 30-60, 60-90, 90+) | **Value:** `DISTINCTCOUNT(member_id)` | Member segmentation by recency |
| Member Details Table | Table | `member_id`, `member_name`, `member_tier`, `join_date`, `lifetime_spend`, `status` | Sortable drill-down; sort by `lifetime_spend` DESC default |

### Filters & Slicers

| Slicer | Type | Scope | Default |
|--------|------|-------|---------|
| Date Range | Date | Page-level; affects Enrollment Trend & Engagement by Activity | Last 12 months |
| Member Tier | Dropdown | Page-level; affects all tier-related visuals | All (no filter) |
| Status | Dropdown | Page-level; pre-filters to Active | Active |
| Refresh Indicator | Card/Text | Page-level; displays last refresh time | Automatic |

### Color Theme

- **Primary Accent:** Platinum (Dark Blue #1F77B4)
- **Tier Palette:** 
  - Platinum: #2E5090 (Dark Blue)
  - Gold: #FFD700 (Gold)
  - Silver: #C0C0C0 (Silver)
  - Bronze: #CD7F32 (Bronze)
- **Engagement Score:** Green (#2CA02C) for high, Yellow (#FF7F0E) for medium, Red (#D62728) for low
- **Background:** White (#FFFFFF)
- **Text:** Dark Gray (#333333)

---

## Report 2: Store Performance by Region

**Audience:** Regional Operations Manager, VP of Retail, Store Managers  
**Focus:** Regional revenue comparison, store rankings, transaction analysis  
**Semantic Views:** `v_store_performance`, `v_transaction_history`

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  STORE PERFORMANCE BY REGION                                    │
├─────────────────────────────────────────────────────────────────┤
│ [Region Filter] | [Store Type Filter] | [Date Range Slicer]     │
├─────────────────────────────────────────────────────────────────┤
│  Total Regional Revenue (Card)  │  Avg Transaction Value (Card) │
│  Region Transaction Count       │  Avg Basket Size (Card)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Revenue by Region (Column Chart)  │  Store Rankings (Table)    │
│  [Sorted by revenue desc]          │  Top 20 stores by revenue  │
│                                    │  with avg basket & count   │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Revenue Trend by Region (Line Chart)  │  Transaction Distribution│
│  [Multiple lines, one per region]      │  by Day of Week (Bar)   │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Regional Store Map (Filled Map)                                │
│  [Stores plotted by region; color = revenue]                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Measures / DAX

```
Total Regional Revenue = 
  SUM(v_store_performance[revenue])

Total Transaction Count = 
  SUM(v_store_performance[transaction_count])

Avg Transaction Value = 
  DIVIDE(SUM(v_store_performance[revenue]), 
    SUM(v_store_performance[transaction_count]), 0)

Avg Basket Size = 
  AVERAGE(v_store_performance[avg_basket_size])

YoY Revenue Growth % = 
  VAR CurYear = CALCULATE(SUM(v_store_performance[revenue]), 
    YEAR(TODAY()) = YEAR(TODAY()))
  VAR PriorYear = CALCULATE(SUM(v_store_performance[revenue]), 
    YEAR(TODAY()) = YEAR(TODAY()) - 1)
  RETURN DIVIDE(CurYear - PriorYear, PriorYear, 0)

Stores Above Avg Basket = 
  CALCULATE(DISTINCTCOUNT(v_store_performance[store_id]), 
    v_store_performance[avg_basket_size] > [Avg Basket Size])
```

### Visuals

| Visual | Type | Fields | Description |
|--------|------|--------|-------------|
| Total Regional Revenue | Card | `Total Regional Revenue` measure | Display region-level revenue in millions |
| Total Transaction Count | Card | `Total Transaction Count` measure | Display transaction volume |
| Avg Transaction Value | Card | `Avg Transaction Value` measure | Display average ticket size |
| Avg Basket Size | Card | `Avg Basket Size` measure | Display average items/transaction |
| Revenue by Region | Column | **Axis:** `v_store_performance[region]` | **Value:** `Total Regional Revenue` | Sorted descending; enables drill-through |
| Store Rankings Table | Table | `store_id`, `store_name`, `region`, `revenue`, `transaction_count`, `avg_basket_size` | Top 20 by revenue; sortable; show region column |
| Revenue Trend by Region | Line | **Axis:** `v_store_performance[date]` (binned monthly) | **Legend:** `region` | **Value:** `Total Regional Revenue` | Multi-line trend; shows seasonal patterns |
| Transaction Distribution by Day | Bar | **Axis:** `v_transaction_history[transaction_date]` (day of week) | **Value:** `DISTINCTCOUNT(transaction_id)` | Shows busiest days |
| Regional Store Map | Filled Map | **Location:** `region` | **Value:** `Total Regional Revenue` | Color saturation = revenue |

### Filters & Slicers

| Slicer | Type | Scope | Default |
|--------|------|-------|---------|
| Region | Dropdown | Page-level; impacts all visuals | All |
| Store Type | Dropdown | Page-level; filters store_type column | All |
| Date Range | Date | Page-level; affects trends and YTD comparisons | Last 12 months |

### Color Theme

- **Primary Accent:** Deep Teal #0F7BA7
- **Revenue Scale:** Light Green (#D5E8D4) to Dark Green (#1B4620)
- **Region Palette:** Distinct colors per region (e.g., Northeast: Blue, Southeast: Red, Midwest: Orange, West: Purple)
- **Background:** Off-White (#F5F5F5)
- **Text:** Dark Gray (#2C3E50)

---

## Report 3: Product Mix & Popularity

**Audience:** Merchandising Manager, Category Manager, Buyers  
**Focus:** Category performance, product rankings, ratings, sales velocity  
**Semantic Views:** `v_product_popularity`

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  PRODUCT MIX & POPULARITY                                       │
├─────────────────────────────────────────────────────────────────┤
│ [Category Filter] | [Date Range Slicer] | [Min Rating Filter]   │
├─────────────────────────────────────────────────────────────────┤
│  Total Products (Card)       │  Avg Product Rating (Card)       │
│  Total Sales Volume (Card)   │  Avg Revenue per Product (Card)  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Sales by Category (Donut)          │  Top 15 Products (Table)   │
│  [Category split showing revenue]   │  [Product, Revenue, Rating]│
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Product Sales Ranking (Bar Chart)  │  Avg Rating by Category    │
│  [Top 20 products by volume]        │  (Scatter or Bar)          │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Rating Distribution (Histogram)                                 │
│  [Count of products across 1-5 star range]                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Measures / DAX

```
Total Products = 
  DISTINCTCOUNT(v_product_popularity[product_id])

Total Sales Volume = 
  SUM(v_product_popularity[sales_volume])

Total Revenue = 
  SUM(v_product_popularity[revenue])

Avg Product Rating = 
  AVERAGE(v_product_popularity[avg_rating])

Avg Revenue per Product = 
  DIVIDE(SUM(v_product_popularity[revenue]), 
    DISTINCTCOUNT(v_product_popularity[product_id]), 0)

Top Quartile Products = 
  CALCULATE(DISTINCTCOUNT(v_product_popularity[product_id]), 
    v_product_popularity[revenue] > QUARTILE.INC(
      ALL(v_product_popularity[revenue]), 3))

Highly Rated (4+) = 
  CALCULATE(DISTINCTCOUNT(v_product_popularity[product_id]), 
    v_product_popularity[avg_rating] >= 4)
```

### Visuals

| Visual | Type | Fields | Description |
|--------|------|--------|-------------|
| Total Products | Card | `Total Products` measure | Distinct product count |
| Total Sales Volume | Card | `Total Sales Volume` measure | Unit sales aggregate |
| Total Revenue | Card | `Total Revenue` measure | Revenue by product mix |
| Avg Product Rating | Card | `Avg Product Rating` measure | 1-5 scale average |
| Sales by Category | Donut | **Legend:** `category` | **Value:** `Total Sales Volume` or `Total Revenue` | Proportional breakdown |
| Top 15 Products Table | Table | `product_name`, `category`, `sales_volume`, `revenue`, `avg_rating` | Sort by revenue DESC; show top 15 |
| Product Sales Ranking | Horizontal Bar | **Axis:** `product_name` (top 20 by volume) | **Value:** `Total Sales Volume` | Sorted descending |
| Avg Rating by Category | Scatter or Bar | **Axis:** `category` | **Value:** `Avg Product Rating` | Shows rating quality per category |
| Rating Distribution | Histogram | **Axis:** Binned `avg_rating` (1-2, 2-3, 3-4, 4-5) | **Value:** `Total Products` | Shows rating spread |

### Filters & Slicers

| Slicer | Type | Scope | Default |
|--------|------|-------|---------|
| Category | Dropdown | Page-level; filters all visuals | All |
| Date Range | Date | Page-level; affects sales volume & revenue trends | Last 12 months |
| Minimum Rating | Slider | Page-level; filters products with rating >= threshold | 3.0 |

### Color Theme

- **Primary Accent:** Warm Orange #FF8C00
- **Category Palette:** Distinct colors per category (e.g., Auto Parts: Red, Maintenance: Yellow, Tools: Blue, Accessories: Green)
- **Rating Scale:** Red (#D62728) for low ratings, Yellow (#FF7F0E) for medium, Green (#2CA02C) for high
- **Background:** White (#FFFFFF)
- **Text:** Dark Charcoal (#1C1C1C)

---

## Report 4: Coupon Campaign Effectiveness

**Audience:** Marketing Manager, Promotions Manager, VP of Marketing  
**Focus:** Campaign ROI, redemption rates, member tier targeting, promotion performance  
**Semantic Views:** `v_campaign_effectiveness`, `v_coupon_activity`

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  COUPON CAMPAIGN EFFECTIVENESS                                  │
├─────────────────────────────────────────────────────────────────┤
│ [Campaign Filter] | [Date Range] | [Tier Filter]                │
├─────────────────────────────────────────────────────────────────┤
│  Campaign ROI % (Card)      │  Total Redemptions (Card)         │
│  Total Spend (Card)         │  Avg Discount per Coupon (Card)   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Campaign ROI Ranking (Bar Chart)   │  Redemption Rate % by Tier │
│  [Sorted by ROI desc]               │  (Grouped Bar or Stacked)  │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Campaign Timeline (Area Chart)     │  Spend vs. Revenue Impact  │
│  [Spend + revenue by campaign date] │  (Scatter: Spend axis /    │
│                                     │   Revenue axis)             │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Campaign Details (Table)                                        │
│  [Campaign Name | ROI% | Spend | Redemptions | Avg Discount]    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Measures / DAX

```
Total Campaign Spend = 
  SUM(v_campaign_effectiveness[total_spend])

Total Revenue Impact = 
  SUM(v_campaign_effectiveness[revenue_impact])

Campaign ROI % = 
  DIVIDE(
    ([Total Revenue Impact] - [Total Campaign Spend]),
    [Total Campaign Spend],
    0) * 100

Total Coupons Issued = 
  DISTINCTCOUNT(v_coupon_activity[coupon_id])

Total Coupons Redeemed = 
  CALCULATE(DISTINCTCOUNT(v_coupon_activity[coupon_id]), 
    v_coupon_activity[is_redeemed] = TRUE)

Redemption Rate % = 
  DIVIDE([Total Coupons Redeemed], [Total Coupons Issued], 0) * 100

Avg Discount per Coupon = 
  AVERAGE(v_coupon_activity[discount_amount])

Best Performing Campaign = 
  TOPN(1, 
    SUMMARIZE(v_campaign_effectiveness, 
      v_campaign_effectiveness[campaign_id], 
      v_campaign_effectiveness[campaign_name],
      "ROI", [Campaign ROI %]),
    [ROI], DESC)

Redemption by Tier = 
  CALCULATE([Total Coupons Redeemed], 
    v_coupon_activity[member_tier] = SELECTEDVALUE(v_coupon_activity[member_tier]))
```

### Visuals

| Visual | Type | Fields | Description |
|--------|------|--------|-------------|
| Campaign ROI % | Card | `Campaign ROI %` measure | Overall portfolio ROI |
| Total Spend | Card | `Total Campaign Spend` measure | Sum of all campaign budgets |
| Total Redemptions | Card | `Total Coupons Redeemed` measure | Count of redeemed coupons |
| Avg Discount per Coupon | Card | `Avg Discount per Coupon` measure | Average face value |
| Campaign ROI Ranking | Bar | **Axis:** `v_campaign_effectiveness[campaign_name]` (top 15 by ROI) | **Value:** `Campaign ROI %` | Sorted descending; shows best/worst |
| Redemption Rate by Tier | Grouped Bar | **Axis:** `v_coupon_activity[member_tier]` | **Legend:** `v_campaign_effectiveness[campaign_name]` (top 5 campaigns) | **Value:** `Redemption Rate %` | Shows tier-specific targeting |
| Campaign Timeline | Area | **Axis:** `v_campaign_effectiveness[campaign_start_date]` (binned monthly) | **Value (1):** `Total Campaign Spend` (stacked) | **Value (2):** `Total Revenue Impact` (overlay line) | Shows spend/revenue correlation |
| Spend vs. Revenue Impact | Scatter | **X-Axis:** `Total Campaign Spend` | **Y-Axis:** `Total Revenue Impact` | **Bubble Size:** `Total Coupons Redeemed` | Each campaign is a bubble; efficiency diagonal visible |
| Campaign Details Table | Table | `campaign_name`, `campaign_start_date`, `campaign_end_date`, `total_spend`, `revenue_impact`, `redemption_rate_%` | Sortable; default sort by ROI DESC |

### Filters & Slicers

| Slicer | Type | Scope | Default |
|--------|------|-------|---------|
| Campaign | Dropdown | Page-level; can select multiple | All |
| Date Range | Date | Page-level; affects campaign timeline | Last 12 months |
| Member Tier | Dropdown | Page-level; impacts redemption rate visual | All |

### Color Theme

- **Primary Accent:** Forest Green #228B22
- **ROI Scale:** Red (#D62728) for negative/low, Yellow (#FFD700) for neutral, Green (#2CA02C) for strong ROI
- **Campaign Palette:** Distinct color per campaign (auto-assign if 10+ campaigns)
- **Emphasis:** High-ROI campaigns highlighted with bold green tint
- **Background:** Subtle gray (#F0F0F0)
- **Text:** Dark Blue (#0F3B6E)

---

## Report 5: Operational Deep Dive

**Audience:** Store Operations Manager, CSR Manager, VP of Customer Service, Compliance Officer  
**Focus:** Transaction patterns, CSR audit trail, points economy, operational efficiency  
**Semantic Views:** `v_transaction_history`, `v_coupon_activity`, `v_audit_trail`, `v_points_activity`

### Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  OPERATIONAL DEEP DIVE                                          │
├─────────────────────────────────────────────────────────────────┤
│ [Store Filter] | [CSR Filter] | [Date Range] | [Event Type]     │
├─────────────────────────────────────────────────────────────────┤
│  Total Transactions (Card)   │  Total Points Issued (Card)      │
│  Total CSR Events (Card)     │  Avg Transaction Value (Card)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Transactions by Store (Map)       │  CSR Activity (Table)      │
│  [Heatmap of transaction count]    │  [Top 20 CSRs by events]   │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Points Balance Distribution (Histogram)  │  Audit Events by Type│
│  [Member points balance ranges]          │  (Donut)             │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Transaction Trend (Line Chart)    │  Points Earned vs Redeemed │
│  [Daily transaction count + avg val]│  (Dual-axis area chart)   │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  Audit Trail (Table)                                             │
│  [Event Date | Event Type | CSR Name | Member ID | Details]     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Measures / DAX

```
Total Transactions = 
  DISTINCTCOUNT(v_transaction_history[transaction_id])

Total Transaction Value = 
  SUM(v_transaction_history[transaction_amount])

Avg Transaction Value = 
  DIVIDE([Total Transaction Value], [Total Transactions], 0)

Total CSR Events = 
  DISTINCTCOUNT(v_audit_trail[event_id])

Total Points Issued = 
  CALCULATE(SUM(v_points_activity[points_earned]), 
    v_points_activity[activity_type] = "Earn")

Total Points Redeemed = 
  CALCULATE(SUM(v_points_activity[points_redeemed]), 
    v_points_activity[activity_type] = "Redeem")

Avg Points per Transaction = 
  DIVIDE(
    CALCULATE(SUM(v_points_activity[points_earned]), 
      v_points_activity[activity_type] = "Earn"),
    [Total Transactions], 0)

High-Value Transactions (>$100) = 
  CALCULATE([Total Transactions], 
    v_transaction_history[transaction_amount] > 100)

CSR Exception Events = 
  CALCULATE([Total CSR Events], 
    v_audit_trail[event_type] IN {"Override", "Exception", "Return", "Manual_Adjustment"})

Points Float = 
  SUM(v_points_activity[running_balance])
```

### Visuals

| Visual | Type | Fields | Description |
|--------|------|--------|-------------|
| Total Transactions | Card | `Total Transactions` measure | Daily transaction count or period total |
| Total Points Issued | Card | `Total Points Issued` measure | Aggregate points earned |
| Total CSR Events | Card | `Total CSR Events` measure | Audit trail event count |
| Avg Transaction Value | Card | `Avg Transaction Value` measure | Average ticket |
| Transactions by Store | Filled Map | **Location:** `v_transaction_history[store_region]` or store geo data | **Color Saturation:** `Total Transactions` | Heatmap showing transaction density |
| CSR Activity Table | Table | `csr_name`, `store_id`, `event_count`, `avg_events_per_day`, `last_activity_date` | Top 20 by event count; sortable |
| Points Balance Distribution | Histogram | **Axis:** Binned `v_points_activity[running_balance]` (0-100, 100-500, 500-1K, 1K+) | **Value:** `DISTINCTCOUNT(member_id)` | Shows member point holdings |
| Audit Events by Type | Donut | **Legend:** `v_audit_trail[event_type]` | **Value:** `Total CSR Events` | Breakdown of audit categories |
| Transaction Trend | Line | **Axis:** `v_transaction_history[transaction_date]` (binned daily) | **Value (Primary):** `Total Transactions` (count) | **Value (Secondary):** `Avg Transaction Value` (dual axis) | Identifies spikes/dips |
| Points Earned vs Redeemed | Dual-Axis Area | **Axis:** `v_points_activity[activity_date]` (binned weekly) | **Area 1:** `Total Points Issued` (green) | **Area 2:** `Total Points Redeemed` (red) | Shows liquidity/run-rate |
| Audit Trail Table | Table | `event_date`, `event_type`, `csr_name`, `member_id`, `details`, `store_id` | Sortable; default sort by event_date DESC; allow drill-down to specific CSR/store |

### Filters & Slicers

| Slicer | Type | Scope | Default |
|--------|------|-------|---------|
| Store | Dropdown | Page-level; impacts store map, transaction trend, CSR activity | All |
| CSR Name | Dropdown | Page-level; impacts audit trail, CSR activity | All |
| Date Range | Date | Page-level; affects all trends and counts | Last 30 days |
| Event Type | Dropdown | Page-level; filters audit trail | All |
| Exception Events Only | Toggle | Page-level; hides routine events, shows only "Exception", "Override", "Return", "Manual_Adjustment" | Off |

### Color Theme

- **Primary Accent:** Royal Blue #4169E1
- **Transaction Scale:** Light Yellow (#FFFACD) to Orange (#FF8C00)
- **Points Scale:** Light Green (#90EE90) for issued, Light Red (#FFB6C1) for redeemed
- **Exception Alert:** Red (#DC143C) for exception events, Gray (#A9A9A9) for routine
- **CSR Activity:** Blue (#0047AB) for high activity, Gray (#D3D3D3) for low
- **Background:** Very Light Gray (#FAFAFA)
- **Text:** Dark Slate Gray (#2F4F4F)

---

## Common Specifications

### Navigation & Interactivity

All reports include:

1. **Report-Level Navigation Button** (top-left)
   - Bookmark navigation to other reports (Member Insights → Store Performance → Products → Campaigns → Operational)
   - Mobile-friendly dropdown menu on mobile devices

2. **Drill-Through Enabled**
   - Member Insights → Member Details Table → drill through to Store Performance (filtered by that member's visits)
   - Store Performance → Store Rankings → drill through to Transaction Details
   - Product Mix → Top Products → drill through to Transaction history for that product
   - Campaign Effectiveness → Campaign Details → drill through to Coupon Activity by redemption status

3. **Bookmark Snapshots**
   - "This Month" (filters to current calendar month)
   - "Last Quarter" (filters to prior quarter)
   - "Top 10 Only" (enables top-N filter)
   - "Export Ready" (hides slicers, shows full table view for export)

4. **Export Options**
   - All tables support "Export to Excel" button
   - Reports support "Print to PDF" with custom branding

### Data Refresh Strategy

- **Incremental Refresh:** Sample data refreshes nightly at 02:00 UTC; reports show last-refresh timestamp in footer
- **Scheduled Refresh:** Power BI service set to refresh 2x daily (06:00 UTC, 14:00 UTC) when deployed to AAP production
- **Composite Models:** If combining real data + calculated tables, use DirectQuery for fact tables, Import for dimension tables

### Visual Accessibility

All reports comply with:

1. **Color Blindness:** Avoid red-green combinations without secondary cues (use patterns, icons, or labels)
2. **High Contrast:** Text minimum 4.5:1 contrast ratio against backgrounds
3. **Readable Fonts:** Segoe UI (default Power BI font) at 9pt+ for labels, 11pt+ for content
4. **Alt Text:** All visuals include descriptive alt text for screen readers

### Report Performance

- **Query Optimization:** Leverage Fabric semantic views (not raw tables) — views pre-compute common aggregations
- **Visual Limits:** Tables capped at 10K rows (paginated); enable drill-down for detail beyond top 10K
- **Refresh Time Target:** Each report refreshes in <2 minutes
- **Mobile Rendering:** All reports responsive; tested on tablet (iPad) and mobile (iPhone 12+) screens

### Branding & Layout

- **Report Header:** AAP logo (top-left), report title (center), refresh timestamp (top-right)
- **Footer:** Copyright "© 2026 Advanced Auto Parts", page number, data source attribution ("Powered by Microsoft Fabric")
- **Font Family:** Segoe UI (headings), Segoe UI Light (body text)
- **Page Size:** 16:9 widescreen (standard Power BI); single-page layouts optimized for printing at A4 landscape
- **Tab Colors:** Each report uses distinct tab color for visual separation

---

## Implementation Checklist

- [ ] **Data Connectivity:** Verify SQL Analytics Endpoint connection with Service Principal credentials
- [ ] **Semantic Views:** Confirm all 9 views deployed and queryable from Power BI Desktop
- [ ] **DAX Measures:** Validate all measure calculations with sample data; check for correct aggregations and DIVIDE safety
- [ ] **Visuals:** Build each visual per spec; verify field mappings and data types
- [ ] **Slicers:** Configure page-level and visual-level filters; test filter propagation
- [ ] **Drill-Throughs:** Set up drill-through actions between reports; test round-trip navigation
- [ ] **Color Theme:** Apply consistent color palette; validate contrast ratios
- [ ] **Performance:** Run Performance Analyzer on each report; check for slow visuals or expensive DAX
- [ ] **Testing:** Validate each visual with sample data; test edge cases (empty results, large datasets, date boundaries)
- [ ] **Documentation:** Capture report source files, DAX libraries, and theme definitions in version control
- [ ] **Sign-Off:** Present to business stakeholders (Loyalty Manager, Ops Manager, Merch Manager, Marketing, CSR Manager); gather approval

---

## Future Enhancements

These items are out of scope for POC but valuable for production:

1. **Mobile-Optimized Reports** — Dedicated mobile-friendly layouts for tablets/phones
2. **Real-Time Dashboards** — Switch v_transaction_history to push-based refresh for live transaction streaming
3. **Predictive Analytics** — Add forecasting visuals (Prophet or SARIMA) for revenue/member churn
4. **Drill-Through to Data Agent** — Allow business users to ask natural language questions from within Power BI (e.g., "Why did Q2 revenue drop?")
5. **Workspaces & Row-Level Security (RLS)** — Restrict data by region (regional manager sees only their region) or store (store manager sees only their store)
6. **Custom Visuals** — Advanced waterfall charts, org charts for CSR hierarchy, custom KPI gauges
7. **Paginated Reports** — PDF-optimized reports for executive mailing or compliance archives

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07 | Danny (Lead) | Initial comprehensive specification for 5 reports |

---

**Questions or clarifications?** Contact Danny (Lead) or the Business Intelligence Team.
