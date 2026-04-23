# AAP Data Agent POC — Data Schema Design

**Document Owner:** Data Engineer  
**Last Updated:** 2025-07  
**Status:** PLACEHOLDER SCHEMA — Awaiting Production Access

> **📋 Update (July 2025):** The real AAP Loyalty Database schema has been received and documented
> in [`docs/aap-schema-reference.md`](aap-schema-reference.md). That document includes the actual
> table structure (8 table groups, 6 source systems), a preliminary mapping to our contract views,
> and a gap analysis. **This placeholder schema remains active** until production database access
> is available and the semantic views are remapped to real tables.

---

## 1. Schema Design Philosophy

### 1.1 This is a PLACEHOLDER Schema

This schema is **NOT** the actual Advanced Auto Parts rewards/loyalty data schema. We are designing this POC without access to the real schema. This placeholder is:

- **Domain-informed:** Based on industry knowledge of auto parts retail and loyalty programs
- **Realistic:** Structured to support the types of queries a marketing team would actually need
- **Complete enough:** Allows us to build and demo the full technical architecture (Fabric mirroring, Data Agent, web app)
- **Temporary:** Will be replaced when AAP provides the actual schema

### 1.2 Swappable Architecture

The critical design principle is **schema independence**. The rest of the system does NOT depend on specific table names or column names. Instead:

- **Contract-based design:** The system interacts through a **VIEW LAYER** that defines a stable query contract
- **Abstraction:** Backend API, web app, and Fabric Data Agent query standardized views, not raw tables
- **Modularity:** When the real schema arrives, we remap the views to new underlying tables — the rest of the system is unaffected
- **Documentation:** All integration points use the contract views documented in section 5

**Key Principle:** *Components depend on the INTERFACE (views), not the IMPLEMENTATION (tables).*

---

## 2. Proposed Placeholder Schema

This schema models a typical auto parts retailer loyalty program with member tiers, points earning/redemption, purchase history, and marketing campaigns.

### 2.1 Schema Overview

**Table Groups:**
1. **Customer/Member** — Loyalty program members and tier definitions
2. **Transaction** — Purchase history and line items
3. **Points/Rewards** — Points ledger, rewards catalog, redemptions
4. **Product/Store** — Product catalog and store locations
5. **Campaign/Marketing** — Marketing campaigns and member responses

### 2.2 Entity Relationship Summary

```
members (1) ──< (M) transactions (1) ──< (M) transaction_items (M) >── (1) products
   |                                                                           |
   |                                                                           |
   ├── member_tiers (lookup)                                    product_categories (lookup)
   |
   ├──< points_ledger (M)
   |
   ├──< reward_redemptions (M) >── rewards (1)
   |
   └──< campaign_responses (M) >── campaigns (1)

transactions (M) >── (1) stores
```

---

## 3. Full DDL (PostgreSQL Syntax)

### 3.1 Customer/Member Tables

```sql
-- Member tier definitions (Silver, Gold, Platinum)
CREATE TABLE member_tiers (
    tier_id SERIAL PRIMARY KEY,
    tier_name VARCHAR(50) NOT NULL UNIQUE,
    tier_level INT NOT NULL UNIQUE, -- 1=Bronze, 2=Silver, 3=Gold, 4=Platinum
    min_annual_spend DECIMAL(10,2) NOT NULL,
    points_multiplier DECIMAL(3,2) NOT NULL, -- 1.0, 1.5, 2.0
    benefits_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tier_level ON member_tiers(tier_level);

COMMENT ON TABLE member_tiers IS 'Loyalty program tier definitions';
COMMENT ON COLUMN member_tiers.points_multiplier IS 'Multiplier for points earned on purchases';

-- Loyalty program members
CREATE TABLE members (
    member_id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE, -- AAP customer ID
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    join_date DATE NOT NULL DEFAULT CURRENT_DATE,
    tier_id INT NOT NULL REFERENCES member_tiers(tier_id),
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, inactive, suspended
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    opt_in_email BOOLEAN DEFAULT TRUE,
    opt_in_sms BOOLEAN DEFAULT FALSE,
    last_purchase_date DATE,
    lifetime_spend DECIMAL(12,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_members_email ON members(email);
CREATE INDEX idx_members_tier ON members(tier_id);
CREATE INDEX idx_members_status ON members(status);
CREATE INDEX idx_members_last_purchase ON members(last_purchase_date);
CREATE INDEX idx_members_zip ON members(zip_code);

COMMENT ON TABLE members IS 'Loyalty program members';
COMMENT ON COLUMN members.external_id IS 'Reference to AAP main customer database';
COMMENT ON COLUMN members.lifetime_spend IS 'Total spend since joining program';
```

### 3.2 Transaction Tables

```sql
-- Stores/locations
CREATE TABLE stores (
    store_id SERIAL PRIMARY KEY,
    store_number VARCHAR(20) UNIQUE NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    address_line1 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    region VARCHAR(50), -- Northeast, Southeast, Midwest, West, etc.
    phone VARCHAR(20),
    manager_name VARCHAR(100),
    opened_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stores_region ON stores(region);
CREATE INDEX idx_stores_state ON stores(state);
CREATE INDEX idx_stores_active ON stores(is_active);

COMMENT ON TABLE stores IS 'Physical store locations';

-- Product categories
CREATE TABLE product_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    parent_category_id INT REFERENCES product_categories(category_id),
    description TEXT,
    display_order INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_parent ON product_categories(parent_category_id);

COMMENT ON TABLE product_categories IS 'Product category hierarchy';

-- Products
CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category_id INT NOT NULL REFERENCES product_categories(category_id),
    brand VARCHAR(100),
    description TEXT,
    unit_price DECIMAL(10,2) NOT NULL,
    cost DECIMAL(10,2), -- For margin analysis
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_active ON products(is_active);

COMMENT ON TABLE products IS 'Product catalog - auto parts and accessories';
COMMENT ON COLUMN products.sku IS 'Stock keeping unit';

-- Purchase transactions
CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    transaction_number VARCHAR(50) UNIQUE NOT NULL,
    member_id INT NOT NULL REFERENCES members(member_id),
    store_id INT NOT NULL REFERENCES stores(store_id),
    transaction_date TIMESTAMP NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    tax DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50), -- credit, debit, cash, gift_card
    points_earned INT DEFAULT 0,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_member ON transactions(member_id);
CREATE INDEX idx_transactions_store ON transactions(store_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_number ON transactions(transaction_number);

COMMENT ON TABLE transactions IS 'Purchase transaction headers';
COMMENT ON COLUMN transactions.points_earned IS 'Loyalty points earned for this transaction';

-- Transaction line items
CREATE TABLE transaction_items (
    item_id SERIAL PRIMARY KEY,
    transaction_id INT NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    line_number INT NOT NULL,
    product_id INT NOT NULL REFERENCES products(product_id),
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    line_total DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(transaction_id, line_number)
);

CREATE INDEX idx_items_transaction ON transaction_items(transaction_id);
CREATE INDEX idx_items_product ON transaction_items(product_id);

COMMENT ON TABLE transaction_items IS 'Individual line items in transactions';
```

### 3.3 Points/Rewards Tables

```sql
-- Points ledger (all points activity)
CREATE TABLE points_ledger (
    ledger_id SERIAL PRIMARY KEY,
    member_id INT NOT NULL REFERENCES members(member_id),
    transaction_id INT REFERENCES transactions(transaction_id),
    activity_type VARCHAR(50) NOT NULL, -- earned, redeemed, expired, adjusted, bonus
    points_amount INT NOT NULL, -- positive for earn, negative for redeem/expire
    activity_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expiration_date DATE, -- For earned points
    source_description TEXT, -- "Purchase at Store #123", "Birthday bonus", etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ledger_member ON points_ledger(member_id);
CREATE INDEX idx_ledger_transaction ON points_ledger(transaction_id);
CREATE INDEX idx_ledger_date ON points_ledger(activity_date);
CREATE INDEX idx_ledger_type ON points_ledger(activity_type);

COMMENT ON TABLE points_ledger IS 'Complete history of all points activity';
COMMENT ON COLUMN points_ledger.points_amount IS 'Positive = earned/bonus, Negative = redeemed/expired';

-- Rewards catalog
CREATE TABLE rewards (
    reward_id SERIAL PRIMARY KEY,
    reward_code VARCHAR(50) UNIQUE NOT NULL,
    reward_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- discount, free_product, gift_card, service
    points_cost INT NOT NULL,
    cash_value DECIMAL(10,2), -- Equivalent dollar value
    is_active BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    inventory_limit INT, -- NULL = unlimited
    inventory_remaining INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rewards_category ON rewards(category);
CREATE INDEX idx_rewards_active ON rewards(is_active);
CREATE INDEX idx_rewards_points ON rewards(points_cost);

COMMENT ON TABLE rewards IS 'Available rewards in the catalog';

-- Reward redemptions
CREATE TABLE reward_redemptions (
    redemption_id SERIAL PRIMARY KEY,
    member_id INT NOT NULL REFERENCES members(member_id),
    reward_id INT NOT NULL REFERENCES rewards(reward_id),
    redemption_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    points_spent INT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, fulfilled, cancelled
    fulfillment_date TIMESTAMP,
    transaction_id INT REFERENCES transactions(transaction_id), -- If redeemed at POS
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_redemptions_member ON reward_redemptions(member_id);
CREATE INDEX idx_redemptions_reward ON reward_redemptions(reward_id);
CREATE INDEX idx_redemptions_date ON reward_redemptions(redemption_date);
CREATE INDEX idx_redemptions_status ON reward_redemptions(status);

COMMENT ON TABLE reward_redemptions IS 'History of reward redemptions';
```

### 3.4 Campaign/Marketing Tables

```sql
-- Marketing campaigns
CREATE TABLE campaigns (
    campaign_id SERIAL PRIMARY KEY,
    campaign_code VARCHAR(50) UNIQUE NOT NULL,
    campaign_name VARCHAR(255) NOT NULL,
    campaign_type VARCHAR(50), -- email, sms, direct_mail, push, in_store
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    target_tier_id INT REFERENCES member_tiers(tier_id), -- NULL = all tiers
    target_region VARCHAR(50), -- NULL = all regions
    offer_description TEXT,
    discount_type VARCHAR(50), -- percentage, fixed_amount, bonus_points, free_shipping
    discount_value DECIMAL(10,2),
    budget_allocated DECIMAL(12,2),
    created_by VARCHAR(100),
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_campaigns_dates ON campaigns(start_date, end_date);
CREATE INDEX idx_campaigns_type ON campaigns(campaign_type);
CREATE INDEX idx_campaigns_status ON campaigns(status);

COMMENT ON TABLE campaigns IS 'Marketing campaigns targeting loyalty members';

-- Campaign responses/engagement
CREATE TABLE campaign_responses (
    response_id SERIAL PRIMARY KEY,
    campaign_id INT NOT NULL REFERENCES campaigns(campaign_id),
    member_id INT NOT NULL REFERENCES members(member_id),
    sent_date TIMESTAMP,
    opened_date TIMESTAMP,
    clicked_date TIMESTAMP,
    response_type VARCHAR(50), -- sent, opened, clicked, converted, unsubscribed
    transaction_id INT REFERENCES transactions(transaction_id), -- If resulted in purchase
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_responses_campaign ON campaign_responses(campaign_id);
CREATE INDEX idx_responses_member ON campaign_responses(member_id);
CREATE INDEX idx_responses_type ON campaign_responses(response_type);
CREATE INDEX idx_responses_transaction ON campaign_responses(transaction_id);

COMMENT ON TABLE campaign_responses IS 'Member engagement with marketing campaigns';
```

---

## 4. Sample Data Description

When loading sample data for testing, use these distributions to create realistic data:

### 4.1 Data Volume Targets

- **Members:** ~50,000 records
  - 60% Active, 30% Inactive, 10% Suspended
  - Tier distribution: 50% Bronze, 30% Silver, 15% Gold, 5% Platinum
  - Geographic distribution across 5 states (VA, NC, PA, OH, FL)
  - Join dates spread over last 5 years

- **Stores:** 5 locations
  - 2 in Virginia (Richmond, Norfolk)
  - 1 in North Carolina (Charlotte)
  - 1 in Pennsylvania (Philadelphia)
  - 1 in Ohio (Columbus)

- **Products:** ~500 products
  - Categories: Batteries (10%), Engine Parts (25%), Brakes (15%), Fluids/Chemicals (15%), Electrical (10%), Body/Trim (10%), Tools (10%), Accessories (5%)
  - Price range: $5 - $500
  - Brands: AAP house brands + national brands (Duralast, Bosch, Mobil 1, Castrol, etc.)

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
- **Points Earned:** Base rate = $1 spent = 1 point, multiplied by tier bonus
- **Campaign Codes:** Format `{YEAR}{QUARTER}-{TYPE}-{SEQ}` (e.g., `2024Q2-EMAIL-003`)

---

## 5. Schema Contract (View Layer)

This is the **CRITICAL INTERFACE** that the rest of the system depends on. All consuming components (Fabric Data Agent, Backend API, Web App) query these views, NOT the raw tables.

### 5.1 Contract Views DDL

```sql
-- Member summary with current points balance
CREATE OR REPLACE VIEW v_member_summary AS
SELECT 
    m.member_id,
    m.external_id,
    m.first_name,
    m.last_name,
    m.email,
    m.phone,
    m.join_date,
    m.status,
    mt.tier_name,
    mt.tier_level,
    mt.points_multiplier,
    m.last_purchase_date,
    m.lifetime_spend,
    COALESCE(SUM(pl.points_amount), 0) AS current_points_balance,
    DATEDIFF(day, m.last_purchase_date, CURRENT_DATE) AS days_since_last_purchase,
    m.city,
    m.state,
    m.zip_code
FROM members m
JOIN member_tiers mt ON m.tier_id = mt.tier_id
LEFT JOIN points_ledger pl ON m.member_id = pl.member_id 
    AND (pl.expiration_date IS NULL OR pl.expiration_date > CURRENT_DATE)
GROUP BY m.member_id, m.external_id, m.first_name, m.last_name, m.email, m.phone,
    m.join_date, m.status, mt.tier_name, mt.tier_level, mt.points_multiplier,
    m.last_purchase_date, m.lifetime_spend, m.city, m.state, m.zip_code;

COMMENT ON VIEW v_member_summary IS 'CONTRACT VIEW: Member profile with current points and tier';

-- Transaction history with enriched details
CREATE OR REPLACE VIEW v_transaction_history AS
SELECT 
    t.transaction_id,
    t.transaction_number,
    t.transaction_date,
    t.member_id,
    m.first_name || ' ' || m.last_name AS member_name,
    m.email AS member_email,
    mt.tier_name AS member_tier,
    t.store_id,
    s.store_name,
    s.city AS store_city,
    s.state AS store_state,
    s.region AS store_region,
    t.subtotal,
    t.tax,
    t.total,
    t.discount_amount,
    t.payment_method,
    t.points_earned,
    COUNT(ti.item_id) AS item_count,
    SUM(ti.quantity) AS total_quantity
FROM transactions t
JOIN members m ON t.member_id = m.member_id
JOIN member_tiers mt ON m.tier_id = mt.tier_id
JOIN stores s ON t.store_id = s.store_id
LEFT JOIN transaction_items ti ON t.transaction_id = ti.transaction_id
GROUP BY t.transaction_id, t.transaction_number, t.transaction_date, t.member_id,
    m.first_name, m.last_name, m.email, mt.tier_name, t.store_id, s.store_name,
    s.city, s.state, s.region, t.subtotal, t.tax, t.total, t.discount_amount,
    t.payment_method, t.points_earned;

COMMENT ON VIEW v_transaction_history IS 'CONTRACT VIEW: Complete transaction details with member and store info';

-- Points activity timeline
CREATE OR REPLACE VIEW v_points_activity AS
SELECT 
    pl.ledger_id,
    pl.member_id,
    m.first_name || ' ' || m.last_name AS member_name,
    m.email AS member_email,
    mt.tier_name AS member_tier,
    pl.activity_type,
    pl.points_amount,
    pl.activity_date,
    pl.expiration_date,
    pl.source_description,
    pl.transaction_id,
    t.transaction_number,
    CASE 
        WHEN pl.expiration_date IS NOT NULL AND pl.expiration_date <= CURRENT_DATE THEN 'expired'
        WHEN pl.expiration_date IS NOT NULL AND pl.expiration_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'expiring_soon'
        ELSE 'active'
    END AS points_status
FROM points_ledger pl
JOIN members m ON pl.member_id = m.member_id
JOIN member_tiers mt ON m.tier_id = mt.tier_id
LEFT JOIN transactions t ON pl.transaction_id = t.transaction_id;

COMMENT ON VIEW v_points_activity IS 'CONTRACT VIEW: All points activity with expiration tracking';

-- Reward catalog with availability
CREATE OR REPLACE VIEW v_reward_catalog AS
SELECT 
    r.reward_id,
    r.reward_code,
    r.reward_name,
    r.description,
    r.category,
    r.points_cost,
    r.cash_value,
    r.is_active,
    r.start_date,
    r.end_date,
    r.inventory_limit,
    r.inventory_remaining,
    CASE 
        WHEN r.is_active = FALSE THEN 'inactive'
        WHEN r.end_date IS NOT NULL AND r.end_date < CURRENT_DATE THEN 'expired'
        WHEN r.start_date IS NOT NULL AND r.start_date > CURRENT_DATE THEN 'upcoming'
        WHEN r.inventory_limit IS NOT NULL AND r.inventory_remaining <= 0 THEN 'out_of_stock'
        ELSE 'available'
    END AS availability_status,
    COUNT(rr.redemption_id) AS total_redemptions
FROM rewards r
LEFT JOIN reward_redemptions rr ON r.reward_id = rr.reward_id AND rr.status = 'fulfilled'
GROUP BY r.reward_id, r.reward_code, r.reward_name, r.description, r.category,
    r.points_cost, r.cash_value, r.is_active, r.start_date, r.end_date,
    r.inventory_limit, r.inventory_remaining;

COMMENT ON VIEW v_reward_catalog IS 'CONTRACT VIEW: Available rewards with redemption counts';

-- Store performance metrics
CREATE OR REPLACE VIEW v_store_performance AS
SELECT 
    s.store_id,
    s.store_number,
    s.store_name,
    s.city,
    s.state,
    s.region,
    COUNT(DISTINCT t.transaction_id) AS transaction_count,
    COUNT(DISTINCT t.member_id) AS unique_members,
    SUM(t.total) AS total_revenue,
    AVG(t.total) AS avg_transaction_value,
    SUM(t.points_earned) AS total_points_issued,
    COUNT(DISTINCT ti.product_id) AS unique_products_sold,
    SUM(ti.quantity) AS total_units_sold
FROM stores s
LEFT JOIN transactions t ON s.store_id = t.store_id
LEFT JOIN transaction_items ti ON t.transaction_id = ti.transaction_id
GROUP BY s.store_id, s.store_number, s.store_name, s.city, s.state, s.region;

COMMENT ON VIEW v_store_performance IS 'CONTRACT VIEW: Store-level performance metrics';

-- Campaign effectiveness
CREATE OR REPLACE VIEW v_campaign_effectiveness AS
SELECT 
    c.campaign_id,
    c.campaign_code,
    c.campaign_name,
    c.campaign_type,
    c.start_date,
    c.end_date,
    c.status,
    mt.tier_name AS target_tier,
    c.offer_description,
    COUNT(DISTINCT cr.member_id) AS members_targeted,
    SUM(CASE WHEN cr.response_type = 'opened' THEN 1 ELSE 0 END) AS opens,
    SUM(CASE WHEN cr.response_type = 'clicked' THEN 1 ELSE 0 END) AS clicks,
    COUNT(DISTINCT cr.transaction_id) AS conversions,
    SUM(t.total) AS revenue_generated,
    c.budget_allocated,
    CASE 
        WHEN COUNT(DISTINCT cr.member_id) > 0 
        THEN CAST(SUM(CASE WHEN cr.response_type = 'opened' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(DISTINCT cr.member_id) 
        ELSE 0 
    END AS open_rate,
    CASE 
        WHEN COUNT(DISTINCT cr.member_id) > 0 
        THEN CAST(COUNT(DISTINCT cr.transaction_id) AS FLOAT) / COUNT(DISTINCT cr.member_id) 
        ELSE 0 
    END AS conversion_rate
FROM campaigns c
LEFT JOIN member_tiers mt ON c.target_tier_id = mt.tier_id
LEFT JOIN campaign_responses cr ON c.campaign_id = cr.campaign_id
LEFT JOIN transactions t ON cr.transaction_id = t.transaction_id
GROUP BY c.campaign_id, c.campaign_code, c.campaign_name, c.campaign_type,
    c.start_date, c.end_date, c.status, mt.tier_name, c.offer_description, c.budget_allocated;

COMMENT ON VIEW v_campaign_effectiveness IS 'CONTRACT VIEW: Campaign performance and ROI metrics';

-- Product popularity and performance
CREATE OR REPLACE VIEW v_product_popularity AS
SELECT 
    p.product_id,
    p.sku,
    p.product_name,
    p.brand,
    pc.category_name,
    p.unit_price,
    COUNT(DISTINCT ti.transaction_id) AS times_purchased,
    SUM(ti.quantity) AS total_units_sold,
    SUM(ti.line_total) AS total_revenue,
    AVG(ti.quantity) AS avg_quantity_per_transaction,
    COUNT(DISTINCT t.member_id) AS unique_buyers,
    MAX(t.transaction_date) AS last_sold_date
FROM products p
JOIN product_categories pc ON p.category_id = pc.category_id
LEFT JOIN transaction_items ti ON p.product_id = ti.product_id
LEFT JOIN transactions t ON ti.transaction_id = t.transaction_id
GROUP BY p.product_id, p.sku, p.product_name, p.brand, pc.category_name, p.unit_price;

COMMENT ON VIEW v_product_popularity IS 'CONTRACT VIEW: Product sales performance and popularity';
```

### 5.2 Contract View Descriptions

| View Name | Purpose | Primary Consumers |
|-----------|---------|------------------|
| `v_member_summary` | Complete member profile with tier and current points balance | Web App (member dashboard), Data Agent, Backend API |
| `v_transaction_history` | Enriched transaction view with member/store context | Data Agent (purchase queries), Web App (order history) |
| `v_points_activity` | Points earned/redeemed timeline with expiration tracking | Web App (points history), Data Agent (points queries) |
| `v_reward_catalog` | Available rewards with redemption stats | Web App (rewards page), Data Agent (reward queries) |
| `v_store_performance` | Store-level aggregated metrics | Data Agent (store analysis), Power BI reports |
| `v_campaign_effectiveness` | Campaign ROI and engagement metrics | Data Agent (marketing analysis), Power BI reports |
| `v_product_popularity` | Product sales performance | Data Agent (product queries), Power BI reports |

### 5.3 Why This Abstraction Works

1. **Decoupling:** Consumer code doesn't know or care about underlying table names/structure
2. **Stability:** View signatures remain constant even when tables change
3. **Enrichment:** Views join and aggregate data, providing ready-to-use business entities
4. **Performance:** Views can be optimized, indexed, or materialized independently
5. **Security:** Views can filter sensitive columns without exposing raw tables
6. **Migration Path:** When real schema arrives, redefine views to point to new tables — zero code changes elsewhere

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

## 7. Sample Queries (Natural Language → SQL)

These queries demonstrate the types of questions AAP's marketing team would ask. Use these to configure and test the Fabric Data Agent.

### 7.1 Member Queries

**Q1: "How many active loyalty members do we have?"**
```sql
SELECT COUNT(*) AS active_members
FROM v_member_summary
WHERE status = 'active';
```

**Q2: "Show me members who haven't made a purchase in 90 days"**
```sql
SELECT member_id, first_name, last_name, email, tier_name, 
       last_purchase_date, days_since_last_purchase
FROM v_member_summary
WHERE status = 'active' 
  AND days_since_last_purchase > 90
ORDER BY days_since_last_purchase DESC;
```

**Q3: "How many members are in each tier?"**
```sql
SELECT tier_name, COUNT(*) AS member_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM v_member_summary
WHERE status = 'active'
GROUP BY tier_name, tier_level
ORDER BY tier_level;
```

**Q4: "Who are our top 10 members by lifetime spend?"**
```sql
SELECT first_name, last_name, email, tier_name, 
       lifetime_spend, current_points_balance
FROM v_member_summary
WHERE status = 'active'
ORDER BY lifetime_spend DESC
LIMIT 10;
```

**Q5: "How many members joined in the last 30 days?"**
```sql
SELECT COUNT(*) AS new_members
FROM v_member_summary
WHERE join_date >= CURRENT_DATE - INTERVAL '30 days';
```

### 7.2 Transaction Queries

**Q6: "What are the top 10 products by revenue this quarter?"**
```sql
SELECT product_name, brand, category_name, 
       total_revenue, total_units_sold, times_purchased
FROM v_product_popularity
WHERE last_sold_date >= DATE_TRUNC('quarter', CURRENT_DATE)
ORDER BY total_revenue DESC
LIMIT 10;
```

**Q7: "Which store has the highest average transaction value?"**
```sql
SELECT store_name, city, state, 
       transaction_count, avg_transaction_value, total_revenue
FROM v_store_performance
WHERE transaction_count > 100
ORDER BY avg_transaction_value DESC
LIMIT 1;
```

**Q8: "Show me daily revenue for the last 7 days"**
```sql
SELECT DATE(transaction_date) AS sale_date,
       COUNT(*) AS transaction_count,
       SUM(total) AS daily_revenue,
       AVG(total) AS avg_ticket
FROM v_transaction_history
WHERE transaction_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(transaction_date)
ORDER BY sale_date DESC;
```

**Q9: "What's the total revenue by region this month?"**
```sql
SELECT store_region,
       SUM(total) AS region_revenue,
       COUNT(*) AS transaction_count,
       COUNT(DISTINCT store_id) AS stores_in_region
FROM v_transaction_history
WHERE transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY store_region
ORDER BY region_revenue DESC;
```

**Q10: "What percentage of transactions used each payment method last month?"**
```sql
SELECT payment_method,
       COUNT(*) AS transaction_count,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage,
       SUM(total) AS total_revenue
FROM v_transaction_history
WHERE transaction_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
  AND transaction_date < DATE_TRUNC('month', CURRENT_DATE)
GROUP BY payment_method
ORDER BY transaction_count DESC;
```

### 7.3 Points & Rewards Queries

**Q11: "What's our points redemption rate by tier?"**
```sql
WITH earned AS (
    SELECT member_tier, SUM(points_amount) AS total_earned
    FROM v_points_activity
    WHERE activity_type = 'earned'
      AND activity_date >= DATE_TRUNC('year', CURRENT_DATE)
    GROUP BY member_tier
),
redeemed AS (
    SELECT member_tier, ABS(SUM(points_amount)) AS total_redeemed
    FROM v_points_activity
    WHERE activity_type = 'redeemed'
      AND activity_date >= DATE_TRUNC('year', CURRENT_DATE)
    GROUP BY member_tier
)
SELECT e.member_tier,
       e.total_earned,
       COALESCE(r.total_redeemed, 0) AS total_redeemed,
       ROUND(COALESCE(r.total_redeemed, 0) * 100.0 / NULLIF(e.total_earned, 0), 2) AS redemption_rate_pct
FROM earned e
LEFT JOIN redeemed r ON e.member_tier = r.member_tier
ORDER BY e.member_tier;
```

**Q12: "Show me members with points expiring in the next 30 days"**
```sql
SELECT member_id, member_name, member_email, member_tier,
       SUM(points_amount) AS expiring_points,
       MIN(expiration_date) AS earliest_expiration
FROM v_points_activity
WHERE points_status = 'expiring_soon'
  AND activity_type = 'earned'
GROUP BY member_id, member_name, member_email, member_tier
HAVING SUM(points_amount) > 0
ORDER BY expiring_points DESC;
```

**Q13: "What are the most popular rewards by redemption count?"**
```sql
SELECT reward_name, category, points_cost, 
       cash_value, total_redemptions
FROM v_reward_catalog
WHERE total_redemptions > 0
ORDER BY total_redemptions DESC
LIMIT 10;
```

**Q14: "How many points were issued vs redeemed last month?"**
```sql
SELECT 
    activity_type,
    SUM(points_amount) AS total_points,
    COUNT(*) AS transaction_count
FROM v_points_activity
WHERE activity_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
  AND activity_date < DATE_TRUNC('month', CURRENT_DATE)
  AND activity_type IN ('earned', 'redeemed')
GROUP BY activity_type;
```

### 7.4 Campaign Queries

**Q15: "Show me campaign performance for email campaigns this year"**
```sql
SELECT campaign_name, start_date, end_date,
       members_targeted, opens, clicks, conversions,
       ROUND(open_rate * 100, 2) AS open_rate_pct,
       ROUND(conversion_rate * 100, 2) AS conversion_rate_pct,
       revenue_generated
FROM v_campaign_effectiveness
WHERE campaign_type = 'email'
  AND start_date >= DATE_TRUNC('year', CURRENT_DATE)
  AND status = 'completed'
ORDER BY conversion_rate DESC;
```

**Q16: "Which campaign generated the most revenue?"**
```sql
SELECT campaign_name, campaign_type, target_tier,
       members_targeted, conversions, revenue_generated,
       budget_allocated,
       ROUND((revenue_generated - budget_allocated) / NULLIF(budget_allocated, 0) * 100, 2) AS roi_pct
FROM v_campaign_effectiveness
WHERE status = 'completed'
  AND revenue_generated IS NOT NULL
ORDER BY revenue_generated DESC
LIMIT 1;
```

### 7.5 Advanced Analytics Queries

**Q17: "What's the customer retention rate by tier?"**
```sql
WITH recent_buyers AS (
    SELECT DISTINCT member_id, member_tier
    FROM v_transaction_history
    WHERE transaction_date >= CURRENT_DATE - INTERVAL '90 days'
),
total_by_tier AS (
    SELECT tier_name, COUNT(*) AS total_members
    FROM v_member_summary
    WHERE status = 'active'
    GROUP BY tier_name
)
SELECT t.tier_name,
       t.total_members,
       COUNT(rb.member_id) AS active_buyers_90d,
       ROUND(COUNT(rb.member_id) * 100.0 / t.total_members, 2) AS retention_rate_pct
FROM total_by_tier t
LEFT JOIN recent_buyers rb ON t.tier_name = rb.member_tier
GROUP BY t.tier_name, t.total_members
ORDER BY retention_rate_pct DESC;
```

**Q18: "Show me product category performance by revenue"**
```sql
SELECT category_name,
       COUNT(DISTINCT product_id) AS products_in_category,
       SUM(total_units_sold) AS total_units,
       SUM(total_revenue) AS category_revenue,
       AVG(unit_price) AS avg_product_price
FROM v_product_popularity
GROUP BY category_name
ORDER BY category_revenue DESC;
```

**Q19: "What's the average customer lifetime value by acquisition year?"**
```sql
SELECT EXTRACT(YEAR FROM join_date) AS join_year,
       COUNT(*) AS members_acquired,
       AVG(lifetime_spend) AS avg_lifetime_value,
       AVG(DATEDIFF(day, join_date, COALESCE(last_purchase_date, CURRENT_DATE))) AS avg_days_active
FROM v_member_summary
WHERE status = 'active'
GROUP BY EXTRACT(YEAR FROM join_date)
ORDER BY join_year DESC;
```

**Q20: "Show me purchase frequency by member tier"**
```sql
WITH member_txn_counts AS (
    SELECT member_id, member_tier, COUNT(*) AS txn_count
    FROM v_transaction_history
    WHERE transaction_date >= DATE_TRUNC('year', CURRENT_DATE)
    GROUP BY member_id, member_tier
)
SELECT member_tier,
       COUNT(*) AS members,
       AVG(txn_count) AS avg_transactions_per_member,
       MIN(txn_count) AS min_transactions,
       MAX(txn_count) AS max_transactions
FROM member_txn_counts
GROUP BY member_tier
ORDER BY avg_transactions_per_member DESC;
```

---

## 8. Next Steps

### 8.1 Immediate Actions (POC Phase)
1. **Load Sample Data:** Generate and load realistic sample data following section 4 distributions
2. **Test Views:** Validate all contract views return expected results
3. **Configure Data Agent:** Input sample queries into Fabric Data Agent training
4. **Document API:** Create OpenAPI spec for backend that references contract views
5. **Build Web App:** Implement UI components that query contract views

### 8.2 Pre-Production Actions (Before Real Deployment)
1. **Get Real Schema:** Request actual schema from AAP's database team
2. **Execute Swap:** Follow section 6 procedure to replace placeholder with real schema
3. **Validate Queries:** Ensure all queries still work with real data
4. **Performance Tune:** Add indexes, optimize views based on real data volumes
5. **Security Review:** Implement row-level security if needed

### 8.3 Ongoing Maintenance
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
