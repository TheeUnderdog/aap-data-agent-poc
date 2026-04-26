# LoyaltyOverview Report — PBIR Definition

**Type:** Power BI Report (PBIR format for Fabric git integration)  
**Semantic Model:** `RewardsLoyaltyData.SemanticModel`  
**Pages:** 1 — "Loyalty Program Overview"

---

## What's in the Report

A single-page dashboard with 8 visuals showing top-line loyalty KPIs:

| # | Visual | Type | Source Table(s) | DAX Measure / Column |
|---|--------|------|----------------|---------------------|
| 1 | Total Active Members | Card | `loyalty_members` | `[Active Members]` (member_status = "active") |
| 2 | Points Outstanding (Liability) | Card | `loyalty_members` | `[Total Points Balance]` (SUM current_points_balance) |
| 3 | Avg Lifetime Spend per Member | Card | `loyalty_members` | `[Avg Lifetime Spend]` (AVERAGEX over transactions) |
| 4 | Total Revenue | Card | `transactions` | `[Total Revenue]` (SUM total where type = "purchase") |
| 5 | Member Count by Tier | Bar Chart | `loyalty_members` | Count by `tier` column |
| 6 | Transaction Channel Mix | Donut Chart | `transactions` | Count by `channel` column |
| 7 | Monthly Enrollment Trend | Line Chart | `loyalty_members` | Count by `enrollment_date` month |
| 8 | Top Members by Lifetime Spend | Table | `loyalty_members` | first_name, last_name, tier, current_points_balance, [Avg Lifetime Spend] |

---

## How to Deploy

### Option A: Fabric Git Sync (Recommended)

1. Ensure this repo is connected to your Fabric workspace via git integration
2. The `reports/LoyaltyOverview.Report/` folder will sync as a Power BI report item
3. The `definition.pbir` links to `../RewardsLoyaltyData.SemanticModel` — the semantic model must exist in the same workspace
4. After sync, open the report in Fabric and verify visuals render correctly
5. Minor adjustments to visual sizing or data bindings may be needed in the Power BI editor

### Option B: Manual Upload

1. Open your Fabric workspace in the browser
2. Create a new Power BI report connected to the `RewardsLoyaltyData` semantic model
3. Recreate the 8 visuals described above using the table/column references in this README
4. Save as "LoyaltyOverview"

---

## Verified Answer Visual Mapping

Each visual can serve as the anchor for a Fabric Data Agent verified answer. Select the visual, then use **"Set up a verified answer"** with the trigger phrases below.

| Visual | Suggested Verified Answer Trigger Phrases | Source Agent |
|--------|------------------------------------------|-------------|
| **Total Active Members** (Card) | "how many active members", "total active members", "member count" | Loyalty Program Manager |
| **Points Outstanding** (Card) | "total points outstanding", "points liability", "how many points are unredeemed" | Loyalty Program Manager |
| **Avg Lifetime Spend** (Card) | "average lifetime spend", "avg spend per member", "member lifetime value" | Loyalty Program Manager |
| **Total Revenue** (Card) | "total revenue", "how much revenue", "total sales" | Store Operations |
| **Member Count by Tier** (Bar Chart) | "how are the membership tiers structured", "tier distribution", "members by tier", "how many platinum members" | Loyalty Program Manager |
| **Transaction Channel Mix** (Donut Chart) | "what channels are tracked", "channel mix", "in-store vs online", "transaction channel breakdown" | Store Operations |
| **Monthly Enrollment Trend** (Line Chart) | "enrollment trend", "new members per month", "member growth trend", "sign-up trend" | Loyalty Program Manager |
| **Top Members by Lifetime Spend** (Table) | "top members", "highest spending members", "top 10 members by spend", "best customers" | Loyalty Program Manager |

---

## PBIR Format Notes

- **Format:** PBIR enhanced report format (Fabric git integration native)
- **Canvas:** 1280×720 pixels (standard Power BI desktop canvas)
- **Theme:** Uses CY24SU06 base theme with AAP accent colors (#2E5090 Platinum, #1F77B4 Primary)
- **Visual configs:** Each visual's `config` is a JSON string containing visual type, data projections, prototype queries, and formatting objects
- **Known limitation:** The `prototypeQuery` structures use Power BI's internal query format. After initial git sync import, Fabric may regenerate these queries. Visual data bindings should be verified in the report editor.
- **Table relationships:** The table visual uses only the `loyalty_members` table (first_name, last_name, tier, current_points_balance, lifetime_points_earned). No cross-table joins needed.

---

## Color Reference

| Element | Color | Usage |
|---------|-------|-------|
| `#2E5090` | Platinum Blue | Table headers, points card accent |
| `#1F77B4` | Primary Accent | Card values, chart data points |
| `#333333` | Text Dark | Titles, labels |
| `#E0E0E0` | Grid Lines | Table grid |
| `#F5F5F5` | Alternating Row | Table rows |
| `#FFFFFF` | Background | Page background |
