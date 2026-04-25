# AAP Data Agent POC — Data Schema Design

**Document Owner:** Data Engineer  
**Last Updated:** 2025-01 (Reconciled with actual Lakehouse schema)  
**Status:** ACTIVE POC SCHEMA — Mirrored from Sample Data Generator

> **📋 Important:** This document describes the **actual schema** created by `notebooks/01-create-sample-data.py`
> and deployed in the Fabric Lakehouse. This is NOT a design spec — it documents what EXISTS.
> When AAP provides production database access, this schema will be replaced and the semantic
> layer remapped. See [`docs/aap-schema-reference.md`](aap-schema-reference.md) for preliminary
> production schema mapping (when available).

---

## 1. Schema Design Philosophy

### 1.1 This is the POC Schema

This schema represents the **actual data structure** deployed in the Fabric Lakehouse for POC purposes. It is:

- **Domain-informed:** Based on industry knowledge of auto parts retail and loyalty programs
- **Realistic:** Structured to support the types of queries a marketing team would actually need
- **Generated data:** Created by `notebooks/01-create-sample-data.py` with realistic distributions and relationships
- **Complete enough:** Allows us to build and demo the full technical architecture (Fabric mirroring, Data Agent, web app)
- **Temporary:** Will be replaced when AAP provides production database access

### 1.2 Swappable Architecture

The critical design principle is **schema independence**. The rest of the system does NOT depend on specific table names or column names. Instead:

- **Contract-based design:** The system interacts through a **VIEW LAYER** that defines a stable query contract
- **Abstraction:** Backend API, web app, and Fabric Data Agent query standardized views, not raw tables
- **Modularity:** When the real schema arrives, we remap the views to new underlying tables — the rest of the system is unaffected
- **Documentation:** All integration points use the contract views documented in section 5

**Key Principle:** *Components depend on the INTERFACE (views), not the IMPLEMENTATION (tables).*

---

## 2. POC Schema — Actual Lakehouse Tables

This schema is defined by `notebooks/01-create-sample-data.py` and represents what is **actually deployed** in the Fabric Lakehouse.

### 2.1 Schema Overview

**10 Delta Tables** (no schema prefix — Fabric Lakehouse Spark default database):

| Table | Rows | Description |
|-------|------|-------------|
| `stores` | 500 | Store reference data |
| `sku_reference` | 5,000 | Auto parts product catalog |
| `loyalty_members` | 50,000 | Member profiles and tier info |
| `transactions` | 500,000 | 3 years of purchase/return transactions |
| `transaction_items` | ~1,500,000 | Line items per transaction (~3 avg) |
| `member_points` | 500,000 | Points activity ledger |
| `coupon_rules` | 100 | Campaign-aware coupon rule definitions |
| `coupons` | 200,000 | Coupon issuance and redemption |
| `csr` | 500 | Customer Service Rep profiles |
| `csr_activities` | 50,000 | CSR audit trail |

**Data Span:** 2023-01-01 to 2026-04-01 (3+ years of activity)  
**Generation:** Deterministic (fixed random seed 42 for reproducibility)

### 2.2 Entity Relationship Summary

```
loyalty_members (1) ──< (M) transactions (M) >── (1) stores
      |                      |
      |                      └──< transaction_items (M) >── (1) sku_reference
      |
      ├──< member_points (M)
      ├──< coupons (M) >── (1) coupon_rules
      └──< csr_activities (M) >── (1) csr

Notes:
- loyalty_members.tier is denormalized (no separate tier table)
- No separate product_categories table (category is a column in sku_reference)
- Coupons link to coupon_rules (not a separate rewards catalog)
- CSR activities track member lifecycle events
```

---

## 3. Full Schema Definition (PySpark Types)

The tables below are created using PySpark DataFrames with `StructType` schemas and written as Delta tables. Column types are shown as PySpark types.

### 3.1 Stores — Reference data for transaction locations

**Table:** `stores`  
**Rows:** 500  
**Written by:** `notebooks/01-create-sample-data.py` line 114

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `store_id` | IntegerType | False | Primary key |
| `store_name` | StringType | False | Display name (e.g., "AAP Store #4123") |
| `city` | StringType | True | City name |
| `state` | StringType | True | 2-letter state code |
| `zip_code` | StringType | True | 5-digit ZIP code |
| `region` | StringType | True | Northeast, Southeast, Midwest, Southwest, West |
| `store_type` | StringType | True | "retail" (85%) or "hub" (15%) |
| `opened_date` | DateType | True | Store opening date (2005-01-01 to 2023-06-01) |

---

### 3.2 SKU Reference — Auto parts product catalog

**Table:** `sku_reference`  
**Rows:** 2,000  
**Written by:** `notebooks/01-create-sample-data.py` line 203

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `sku` | StringType | False | Primary key, format: "AAP-XXX-#####" |
| `product_name` | StringType | True | Brand + product name |
| `category` | StringType | True | Batteries, Engine Oil, Brakes, Filters, Wipers, Spark Plugs, Lighting, Coolant, Accessories, Electrical |
| `subcategory` | StringType | True | Sub-category within main category |
| `brand` | StringType | True | Brand name |
| `unit_price` | DoubleType | True | Unit price in dollars |
| `is_bonus_eligible` | BooleanType | True | Eligible for bonus points (15% of SKUs) |
| `is_skip_sku` | BooleanType | True | Excluded from points earning (5% of SKUs) |
| `created_at` | TimestampType | True | Fixed timestamp: 2026-04-01 00:00:00 |

**Categories and Price Ranges:**
- Batteries: $89.99 - $249.99
- Engine Oil: $4.99 - $42.99
- Brakes: $12.99 - $189.99
- Filters: $5.99 - $34.99
- Wipers: $3.99 - $29.99
- Spark Plugs: $2.99 - $18.99
- Lighting: $4.99 - $79.99
- Coolant: $6.99 - $44.99
- Accessories: $2.99 - $89.99
- Electrical: $3.99 - $299.99

---

### 3.3 Loyalty Members — 5,000 member profiles with tier distribution

**Table:** `loyalty_members`  
**Rows:** 5,000  
**Written by:** `notebooks/01-create-sample-data.py` line 284

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `member_id` | LongType | False | Primary key |
| `first_name` | StringType | True | Member first name |
| `last_name` | StringType | True | Member last name |
| `email` | StringType | True | Email address |
| `phone` | StringType | True | Phone number (###-###-####) |
| `enrollment_date` | DateType | True | Enrollment date (2020-01-01 to 2026-03-01) |
| `enrollment_source` | StringType | True | "POS", "Ecomm", or "CustomerFirst" |
| `member_status` | StringType | True | "active" (88%), "inactive" (9%), or "suspended" (3%) |
| `tier` | StringType | True | "Bronze" (60%), "Silver" (25%), "Gold" (10%), "Platinum" (5%) |
| `opt_in_email` | BooleanType | True | Email opt-in flag (72% true) |
| `opt_in_sms` | BooleanType | True | SMS opt-in flag (45% true) |
| `diy_account_id` | StringType | True | DIY account link (35% of members have one, format: "DIY-######") |
| `created_at` | TimestampType | True | Created timestamp (enrollment date + random hour) |
| `updated_at` | TimestampType | True | Last updated timestamp (random date after enrollment) |

**Tier Distribution:**
- Bronze: 60%
- Silver: 25%
- Gold: 10%
- Platinum: 5%

---

### 3.4 Transactions — 50,000 transactions with seasonal patterns

**Table:** `transactions`  
**Rows:** 50,000  
**Written by:** `notebooks/01-create-sample-data.py` line 344

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `transaction_id` | LongType | False | Primary key |
| `member_id` | LongType | True | Foreign key → loyalty_members |
| `store_id` | IntegerType | True | Foreign key → stores |
| `transaction_date` | DateType | True | Transaction date (weighted seasonally: spring/summer heavier) |
| `transaction_type` | StringType | True | "purchase" (92%) or "return" (8%) |
| `subtotal` | DoubleType | True | Subtotal before tax (negative for returns) |
| `tax` | DoubleType | True | Tax amount (5-10% of subtotal, negative for returns) |
| `total` | DoubleType | True | Total amount (subtotal + tax, negative for returns) |
| `item_count` | IntegerType | True | Number of line items (1-6, weighted toward 1-3) |
| `channel` | StringType | True | "in-store" (70%), "online" (20%), "mobile" (10%) |
| `order_id` | StringType | True | Order ID for online/mobile orders (format: "ORD-########") |
| `created_at` | TimestampType | True | Created timestamp (transaction date + random hour 7-20) |

**Seasonal Weights (by month):**
- Jan-Feb: 0.7 (winter low)
- Mar: 0.9 (spring ramp-up)
- Apr-Jun: 1.2-1.3 (spring/summer peak)
- Jul-Sep: 1.2-1.0 (summer decline)
- Oct-Dec: 0.9-0.8 (fall/winter low)

---

### 3.5 Transaction Items — ~150,000 line items (3 per transaction avg)

**Table:** `transaction_items`  
**Rows:** ~150,000 (varies based on transaction.item_count)  
**Written by:** `notebooks/01-create-sample-data.py` line 376

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `item_id` | LongType | False | Primary key |
| `transaction_id` | LongType | True | Foreign key → transactions |
| `sku` | StringType | True | Foreign key → sku_reference |
| `product_name` | StringType | True | Denormalized product name |
| `category` | StringType | True | Denormalized category |
| `quantity` | IntegerType | True | Quantity purchased (1-4, weighted toward 1) |
| `unit_price` | DoubleType | True | Unit price at time of transaction |
| `line_total` | DoubleType | True | unit_price × quantity (negative for returns) |
| `is_return` | BooleanType | True | True if parent transaction is a return |

---

### 3.6 Member Points — ~100,000 points activity records

**Table:** `member_points`  
**Rows:** 100,000  
**Written by:** `notebooks/01-create-sample-data.py` line 454

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `point_id` | LongType | False | Primary key |
| `member_id` | LongType | True | Foreign key → loyalty_members |
| `activity_date` | DateType | True | Date of points activity |
| `activity_type` | StringType | True | "earn" (55%), "redeem" (20%), "expire" (10%), "adjust" (5%), "bonus" (10%) |
| `points_amount` | IntegerType | True | Points change (positive for earn/bonus, negative for redeem/expire) |
| `balance_after` | IntegerType | True | Points balance after this activity (simulated, not cumulative query) |
| `source` | StringType | True | "purchase", "campaign", "bonus_activity", or "manual_adjust" |
| `reference_id` | StringType | True | Transaction ID, campaign ID, or ticket ID |
| `description` | StringType | True | Human-readable description |
| `created_at` | TimestampType | True | Created timestamp (activity date + random hour 6-22) |

**Points Rules (by tier):**
- Bronze/Silver: 1.0× multiplier (base: 5-250 pts)
- Gold: 1.5× multiplier
- Platinum: 2.0× multiplier

---

### 3.7 Coupon Rules — 100 campaign-aware rule definitions

**Table:** `coupon_rules`  
**Rows:** 100  
**Written by:** `notebooks/01-create-sample-data.py`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `rule_id` | LongType | False | Primary key |
| `rule_name` | StringType | True | Display name (e.g., "Holiday % Off #1") |
| `description` | StringType | True | Human-readable description |
| `discount_type` | StringType | True | "percentage", "fixed", or "bogo" |
| `discount_value` | DoubleType | True | Percentage (5-50) or fixed dollar amount (3-75); 0 for BOGO |
| `min_purchase` | DoubleType | True | Minimum purchase required (0, 10, 15, 20, 25, 30, or 50) |
| `valid_days` | IntegerType | True | Validity period in days (7, 14, 30, 60, or 90) |
| `is_active` | BooleanType | True | Active flag (80% true) |
| `target_tier` | StringType | True | Tier restriction (NULL for all tiers, or "Gold", "Platinum", "Silver") |
| `campaign_name` | StringType | True | Campaign grouping (e.g., "Holiday Blitz", "Premium Member Exclusive") |
| `created_at` | TimestampType | True | Fixed timestamp: 2026-04-01 00:00:00 |

**Campaigns** (rules are distributed proportionally by campaign weight):
- Holiday Blitz (Nov 15–Dec 31, weight 3.0), New Year Kickoff (Jan, weight 1.5), Spring Tune-Up (Mar–Apr, weight 2.0), Summer Road Trip (Jun–Jul, weight 2.0), Back to School (Aug–Sep 15, weight 1.5), Premium Member Exclusive (year-round, Gold/Platinum only), Silver+ Appreciation (year-round, Silver+), Welcome Offer (year-round), Flash Sale (random 2-week windows), Birthday Reward (year-round)

---

### 3.8 Coupons — 20,000 issued coupons with redemption tracking

**Table:** `coupons`  
**Rows:** 20,000  
**Written by:** `notebooks/01-create-sample-data.py` line 552

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `coupon_id` | LongType | False | Primary key |
| `coupon_code` | StringType | True | Unique coupon code (format: "AAP-X####-#####") |
| `coupon_rule_id` | LongType | True | Foreign key → coupon_rules |
| `member_id` | LongType | True | Foreign key → loyalty_members (NULL for 15% of coupons) |
| `issued_date` | DateType | True | Date issued |
| `expiry_date` | DateType | True | Expiry date (issued_date + rule.valid_days) |
| `status` | StringType | True | "issued" (30%), "redeemed" (35%), "expired" (30%), "voided" (5%) |
| `redeemed_date` | DateType | True | Date redeemed (NULL unless status = "redeemed") |
| `redeemed_transaction_id` | LongType | True | Transaction where redeemed (NULL unless status = "redeemed") |
| `discount_type` | StringType | True | Denormalized from coupon_rule |
| `discount_value` | DoubleType | True | Denormalized from coupon_rule |
| `source_system` | StringType | True | "GK", "POS", or "Ecomm" |
| `created_at` | TimestampType | True | Created timestamp (issued date + random hour) |

---

### 3.9 CSR — 200 Customer Service Rep profiles

**Table:** `csr`  
**Rows:** 200  
**Written by:** `notebooks/01-create-sample-data.py` line 578

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `csr_id` | LongType | False | Primary key |
| `csr_name` | StringType | True | Full name |
| `csr_email` | StringType | True | Email (@advanceautoparts.com) |
| `department` | StringType | True | "Customer Service", "Loyalty Support", "Fraud Prevention", "Tier Management", "Escalations" |
| `is_active` | BooleanType | True | Active flag (90% true) |
| `created_at` | TimestampType | True | Fixed timestamp: 2026-04-01 00:00:00 |

---

### 3.10 CSR Activities — 10,000 audit trail records

**Table:** `csr_activities`  
**Rows:** 10,000  
**Written by:** `notebooks/01-create-sample-data.py` line 631

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `activity_id` | LongType | False | Primary key |
| `csr_id` | LongType | True | Foreign key → csr |
| `member_id` | LongType | True | Foreign key → loyalty_members |
| `activity_type` | StringType | True | "enrollment", "status_change", "coupon_adjust", "tier_override" |
| `activity_date` | DateType | True | Date of activity |
| `details` | StringType | True | JSON string with activity details |
| `created_at` | TimestampType | True | Created timestamp |

**Activity Types:**
- `enrollment`: New member enrollment actions
- `status_change`: Member status changes (active ↔ inactive ↔ suspended)
- `coupon_adjust`: Coupon void/extend/reissue actions
- `tier_override`: Manual tier adjustments

- `tier_override`: Manual tier adjustments

---

## 3.11 Schema Gap Analysis

This section documents differences between the original design spec and the actual implemented schema.

**Tables in original spec NOT implemented:**
- `member_tiers` — Tier info is denormalized into loyalty_members.tier column
- `products` — Renamed to `sku_reference` with simpler structure
- `product_categories` — Eliminated; category is a column in sku_reference
- `points_ledger` — Renamed to `member_points` with different columns
- `rewards` — Not implemented (coupons serve this purpose in POC)
- `reward_redemptions` — Not implemented
- `campaigns` — Not implemented (out of POC scope)
- `campaign_responses` — Not implemented

**Tables implemented NOT in original spec:**
- `coupon_rules` — Defines reusable coupon templates
- `coupons` — Coupon issuance and redemption tracking
- `csr` — Customer service rep profiles
- `csr_activities` — Audit trail for CSR actions

**Key structural differences:**
1. **Denormalization:** Tier info embedded in loyalty_members instead of separate tier table
2. **Simplified products:** Single sku_reference table instead of products + product_categories
3. **Coupon-centric rewards:** Coupons replace the separate rewards catalog concept
4. **CSR audit trail:** Added CSR tracking for member lifecycle events
5. **No campaigns:** Marketing campaign tracking deferred to production phase

---

## 4. Sample Data Description

### 4.1 Data Volume (Actual)

- **Transactions:** ~500,000 records
  - Date range: Last 2 years
  - Average ticket: $85
  - Seasonal patterns: Higher in spring/summer
  - 70% of members have 1-5 transactions, 20% have 6-20, 10% have 20+

- **Transaction Items:** ~2,000,000 line items
  - Average 4 items per transaction
  - Top-selling categories: Fluids (oil, coolant), Batteries, Filters

- **Points Ledger:** ~600,000 records
  - Mostly "earned" from purchases (1 point per $1 spent)
  - 10% are redemptions
  - 2% are expirations (points expire after 24 months)
  - 3% are bonuses (birthday, tier upgrade, special promotions)

- **Rewards:** ~50 rewards
  - Range from 500 points ($5 discount) to 50,000 points ($500 discount)
  - Mix of: Discounts (60%), Free products (20%), Gift cards (15%), Free services (5%)

- **Reward Redemptions:** ~50,000 records
  - Most common: $10-$25 discounts
  - 90% fulfilled, 8% pending, 2% cancelled

- **Campaigns:** ~20 campaigns per year (40 total for 2-year period)
  - Types: Email (50%), SMS (20%), Push (20%), In-store (10%)
  - Success varies: 30% open rate, 5% click rate, 1-2% conversion rate

- **Campaign Responses:** ~300,000 records
  - Sent to 10,000-30,000 members per campaign
  - Response tracking for email/SMS/push only

### 4.2 Data Generation Notes

- **Member Names:** Use realistic US first/last name distributions
- **Emails:** Format as `firstname.lastname{random}@{domain}.com`
- **Phone Numbers:** Valid US format (10 digits)
- **Addresses:** Real cities/states, fictional street addresses
- **Transaction Dates:** Weighted toward recent dates, with seasonal patterns
- **Product SKUs:** Format `AAP-{CATEGORY}-{NUMBER}` (e.g., `AAP-BAT-1001`)
### 4.1 Data Volume (Actual)

Generated by `notebooks/01-create-sample-data.py`:

| Table | Rows | Notes |
|-------|------|-------|
| `stores` | 500 | National distribution across 5 regions, 46 states |
| `sku_reference` | 5,000 | 10 product categories, realistic pricing |
| `loyalty_members` | 50,000 | Tier distribution: 60% Bronze, 25% Silver, 10% Gold, 5% Platinum |
| `transactions` | 500,000 | Seasonal weighting (spring/summer + holiday peaks), tier-correlated frequency |
| `transaction_items` | ~1,500,000 | Avg 3 items per transaction |
| `member_points` | 500,000 | Activity types: 55% earn, 20% redeem, 10% expire, 10% bonus, 5% adjust |
| `coupon_rules` | 100 | 10 named campaigns, percentage/fixed/BOGO discount types |
| `coupons` | 200,000 | 70% campaign-aware; tier-based redemption rates (Platinum 55%→Bronze 25%) |
| `csr` | 500 | 5 departments, 90% active |
| `csr_activities` | 50,000 | Enrollment, status changes, coupon adjustments, tier overrides |
| **TOTAL** | **~2,800,000+ rows** | |

**Date Range:** 2023-01-01 to 2026-04-01 (3+ years)  
**Deterministic:** Fixed random seed (42) for reproducibility

### 4.2 Data Generation Notes

- **Seasonal patterns:** Transactions weighted toward spring/summer months (April-July) to simulate auto maintenance seasonality
- **Realistic distributions:** Member tier follows loyalty program norms; transaction channels reflect retail dominance (70% in-store)
- **Relational integrity:** All foreign keys valid; member_points references real transactions when applicable
- **Price ranges:** SKU pricing based on actual auto parts market ranges per category
- **Geographic diversity:** Stores span 5 US regions with realistic city/state/ZIP combinations

---

## 5. Schema Contract (View Layer)

This is the **CRITICAL INTERFACE** that the rest of the system depends on. All consuming components (Fabric Data Agent, Backend API, Web App) should query standardized views, NOT raw tables.

**Current Status:** The semantic model currently uses **DirectLake mode** which queries the Delta tables directly. SQL views have NOT been deployed yet. This section documents the **intended abstraction layer** for when SQL endpoint views are implemented.

### 5.1 Proposed Contract Views (Not Yet Deployed)

These views will provide a stable query interface when implemented. For now, components query the raw tables listed below.

#### v_member_summary — Member profile with current points and tier

**Purpose:** Single-row summary of each member's current state  
**Underlying tables:** `loyalty_members`, `member_points`

```sql
-- PROPOSED (not yet deployed)
CREATE OR REPLACE VIEW v_member_summary AS
SELECT 
    m.member_id,
    m.first_name,
    m.last_name,
    m.email,
    m.phone,
    m.enrollment_date,
    m.member_status,
    m.tier,
    m.opt_in_email,
    m.opt_in_sms,
    m.diy_account_id,
    -- Current points balance (latest balance_after per member)
    (SELECT mp.balance_after 
     FROM member_points mp 
     WHERE mp.member_id = m.member_id 
     ORDER BY mp.activity_date DESC, mp.point_id DESC 
     LIMIT 1) AS current_points_balance,
    m.updated_at AS last_profile_update
FROM loyalty_members m;
```

**DirectLake equivalent:** Query `loyalty_members` and aggregate `member_points` manually

---

#### v_transaction_history — Transaction details with member and store info

**Purpose:** Complete transaction view with denormalized member and store details  
**Underlying tables:** `transactions`, `loyalty_members`, `stores`, `transaction_items`

```sql
-- PROPOSED (not yet deployed)
CREATE OR REPLACE VIEW v_transaction_history AS
SELECT 
    t.transaction_id,
    t.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    m.email AS member_email,
    m.tier AS member_tier,
    t.store_id,
    s.store_name,
    s.city AS store_city,
    s.state AS store_state,
    s.region AS store_region,
    t.transaction_date,
    t.transaction_type,
    t.subtotal,
    t.tax,
    t.total,
    t.item_count,
    t.channel,
    t.order_id
FROM transactions t
JOIN loyalty_members m ON t.member_id = m.member_id
JOIN stores s ON t.store_id = s.store_id;
```

**DirectLake equivalent:** Query `transactions`, `loyalty_members`, and `stores` with relationships

---

#### v_points_activity — Points ledger with member context

**Purpose:** All points activity with member details  
**Underlying tables:** `member_points`, `loyalty_members`

```sql
-- PROPOSED (not yet deployed)
CREATE OR REPLACE VIEW v_points_activity AS
SELECT 
    mp.point_id,
    mp.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    m.email AS member_email,
    m.tier AS member_tier,
    mp.activity_date,
    mp.activity_type,
    mp.points_amount,
    mp.balance_after,
    mp.source,
    mp.reference_id,
    mp.description
FROM member_points mp
JOIN loyalty_members m ON mp.member_id = m.member_id;
```

**DirectLake equivalent:** Query `member_points` and `loyalty_members` with relationship

---

#### v_coupon_catalog — Active coupons with rule details

**Purpose:** Available coupons with their redemption rules  
**Underlying tables:** `coupons`, `coupon_rules`, `loyalty_members`

```sql
-- PROPOSED (not yet deployed)
CREATE OR REPLACE VIEW v_coupon_catalog AS
SELECT 
    c.coupon_id,
    c.coupon_code,
    c.member_id,
    m.first_name + ' ' + m.last_name AS member_name,
    cr.rule_name,
    cr.description AS rule_description,
    c.discount_type,
    c.discount_value,
    cr.min_purchase,
    c.issued_date,
    c.expiry_date,
    c.status,
    c.redeemed_date,
    c.redeemed_transaction_id,
    c.source_system
FROM coupons c
JOIN coupon_rules cr ON c.coupon_rule_id = cr.rule_id
LEFT JOIN loyalty_members m ON c.member_id = m.member_id;
```

**DirectLake equivalent:** Query `coupons`, `coupon_rules`, and `loyalty_members` with relationships

---

#### v_store_performance — Store transaction aggregates

**Purpose:** Store-level sales and activity metrics  
**Underlying tables:** `stores`, `transactions`

```sql
-- PROPOSED (not yet deployed)
CREATE OR REPLACE VIEW v_store_performance AS
SELECT 
    s.store_id,
    s.store_name,
    s.city,
    s.state,
    s.region,
    s.store_type,
    COUNT(DISTINCT t.transaction_id) AS total_transactions,
    COUNT(DISTINCT t.member_id) AS unique_members,
    SUM(CASE WHEN t.transaction_type = 'purchase' THEN t.total ELSE 0 END) AS total_sales,
    SUM(CASE WHEN t.transaction_type = 'return' THEN ABS(t.total) ELSE 0 END) AS total_returns,
    AVG(CASE WHEN t.transaction_type = 'purchase' THEN t.total ELSE NULL END) AS avg_transaction_value
FROM stores s
LEFT JOIN transactions t ON s.store_id = t.store_id
GROUP BY s.store_id, s.store_name, s.city, s.state, s.region, s.store_type;
```

**DirectLake equivalent:** Query `stores` and aggregate `transactions` measures in Power BI/semantic model

---

#### v_product_popularity — Product sales by category

**Purpose:** Product performance metrics  
**Underlying tables:** `sku_reference`, `transaction_items`

```sql
-- PROPOSED (not yet deployed)
CREATE OR REPLACE VIEW v_product_popularity AS
SELECT 
    sr.sku,
    sr.product_name,
    sr.category,
    sr.subcategory,
    sr.brand,
    sr.unit_price,
    COUNT(ti.item_id) AS times_sold,
    SUM(ti.quantity) AS total_quantity_sold,
    SUM(ti.line_total) AS total_revenue
FROM sku_reference sr
LEFT JOIN transaction_items ti ON sr.sku = ti.sku
GROUP BY sr.sku, sr.product_name, sr.category, sr.subcategory, sr.brand, sr.unit_price;
```

**DirectLake equivalent:** Query `sku_reference` and aggregate `transaction_items` measures

---

### 5.2 Contract View Descriptions

| View Name | Purpose | Primary Consumers | Status |
|-----------|---------|-------------------|--------|
| `v_member_summary` | Complete member profile with current points balance | Web App, Data Agent, Backend API | **Not deployed** — query `loyalty_members` + `member_points` |
| `v_transaction_history` | Enriched transaction view with member/store context | Data Agent, Web App | **Not deployed** — query `transactions` + `loyalty_members` + `stores` |
| `v_points_activity` | Points earned/redeemed timeline | Web App, Data Agent | **Not deployed** — query `member_points` + `loyalty_members` |
| `v_coupon_catalog` | Available coupons with rule details | Web App, Data Agent | **Not deployed** — query `coupons` + `coupon_rules` + `loyalty_members` |
| `v_store_performance` | Store-level aggregated metrics | Data Agent, Power BI reports | **Not deployed** — aggregate `stores` + `transactions` in semantic model |
| `v_product_popularity` | Product sales performance | Data Agent, Power BI reports | **Not deployed** — aggregate `sku_reference` + `transaction_items` in semantic model |

### 5.3 Why This Abstraction Works

1. **Decoupling:** Consumer code doesn't know or care about underlying table names/structure
2. **Stability:** View signatures remain constant even when tables change
3. **Enrichment:** Views join and aggregate data, providing ready-to-use business entities
4. **Performance:** Views can be optimized, indexed, or materialized independently
5. **Security:** Views can filter sensitive columns without exposing raw tables
6. **Migration Path:** When real schema arrives, redefine views to point to new tables — zero code changes elsewhere

**Current Reality:** DirectLake mode bypasses SQL views for performance. The semantic model defines relationships and measures directly on the Delta tables. When migrating to production, we can either:
- Deploy SQL views on the Lakehouse SQL endpoint and update the semantic model to query them
- Keep DirectLake mode and update table/relationship definitions in the semantic model
- Hybrid: Use DirectLake for performance-critical paths, SQL views for complex aggregations

---

## 6. Schema Swap Procedure

When AAP provides the real rewards/loyalty schema, follow this procedure to swap it in:

### 6.1 Pre-Swap Assessment

**STEP 1: Analyze Real Schema**
- Document all tables, columns, relationships
- Identify naming conventions and data types
- Map real tables to placeholder concepts
- Note any missing entities or unexpected structures

**STEP 2: Create Mapping Document**
- For each contract view, document how it will be rebuilt from real tables
- Identify gaps where real data doesn't match our assumptions
- Plan for data transformations needed

### 6.2 Schema Swap Steps

**STEP 3: Set Up Mirroring with Real Schema**
- Update Fabric mirroring configuration to point to real AAP PostgreSQL database
- Verify all real tables are mirrored to OneLake
- Validate data replication is working

**STEP 4: Redefine Contract Views**
- Create new view definitions that query the real tables
- Maintain exact same view names and column signatures
- Add data transformations as needed to match contract interface
- Test each view independently

**STEP 5: Validation**
- Run all sample queries (section 7) against new views
- Compare result structures (column names, types) — values will differ but structure must match
- Test Data Agent against new views — queries should work unchanged
- Verify Web App and Backend API function correctly

**STEP 6: Update Documentation**
- Mark this document as **ARCHIVED**
- Create new `data-schema-REAL.md` documenting the actual AAP schema
- Update any Data Agent prompts/instructions if real schema has different business terminology
- Update Power BI reports if semantic layer needs adjustments

**STEP 7: Cleanup**
- Drop placeholder tables (keep for 30 days as backup)
- Archive sample data
- Update team documentation

### 6.3 Files That Change vs. Don't Change

**✅ Files That DO NOT Change:**
- `backend/api/routes/*.js` — API endpoints still query same views
- `web-app/src/components/*.jsx` — UI components use same data contracts
- `web-app/src/services/api.js` — API client unchanged
- Fabric Data Agent instructions (unless business terminology differs significantly)
- Power BI reports (unless semantic model needs updates)

**⚠️ Files That CHANGE:**
- `docs/data-schema.md` — Archive this, create new version
- Fabric SQL scripts that define contract views — complete rewrite
- Sample data scripts (if needed for continued testing)
- Any scripts that directly query raw tables (should be rare)

### 6.4 Rollback Plan

If issues arise after swap:
1. Repoint Fabric mirroring back to placeholder database
2. Restore placeholder view definitions
3. System returns to working state immediately
4. Debug and retry swap

### 6.5 Testing Checklist

Before declaring swap complete:

- [ ] All 7 contract views return results
- [ ] View column names and types match original contract
- [ ] Sample queries (section 7) execute successfully
- [ ] Data Agent responds to natural language queries
- [ ] Web App loads member dashboard
- [ ] Web App displays transaction history
- [ ] Web App shows rewards catalog
- [ ] Backend API health check passes
- [ ] Power BI reports refresh successfully
- [ ] No errors in application logs
- [ ] Performance is acceptable (query times < 3 seconds)

---

## 7. Next Steps

### 7.1 Immediate Actions (POC Phase)
1. **Load Sample Data:** Generate and load realistic sample data following section 4 distributions
2. **Test Views:** Validate all contract views return expected results
3. **Configure Data Agent:** Train Fabric Data Agent on data schema and business domain
4. **Document API:** Create OpenAPI spec for backend that references contract views
5. **Build Web App:** Implement UI components that query contract views

### 7.2 Pre-Production Actions (Before Real Deployment)
1. **Get Real Schema:** Request actual schema from AAP's database team
2. **Execute Swap:** Follow section 6 procedure to replace placeholder with real schema
3. **Validate Queries:** Ensure all queries still work with real data
4. **Performance Tune:** Add indexes, optimize views based on real data volumes
5. **Security Review:** Implement row-level security if needed

### 7.3 Ongoing Maintenance
- Monitor view performance and optimize as needed
- Version control all view definitions
- Document any new views added to the contract
- Maintain mapping between contract views and underlying tables

---

## Appendix A: Design Decisions

### A.1 Why PostgreSQL?
- AAP's existing data is in Azure PostgreSQL
- Fabric supports native mirroring from PostgreSQL
- Strong support for complex queries, views, and indexes

### A.2 Why View-Based Abstraction?
- Enables schema swapping without code changes
- Provides stable API for consumers
- Allows query optimization at view level
- Simplifies security and access control

### A.3 Key Assumptions
- Marketing team needs historical purchase data (2 years)
- Points have expiration dates (common in loyalty programs)
- Multi-tier program (Bronze/Silver/Gold/Platinum)
- Campaign tracking with email/SMS/push channels
- Product categorization by auto parts type

### A.4 What We Don't Know (Yet)
- Exact AAP table/column names
- Real data volumes (estimated 50K members, could be 500K or 5M)
- Actual tier structure and benefits
- Points earning rules (assumed 1 point per $1)
- Integration points with AAP's main systems

---

**END OF DOCUMENT**

---

**Revision History:**
- v1.0 (Initial) — Placeholder schema designed for POC development
