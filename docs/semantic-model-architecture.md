# AAP Rewards Loyalty — Semantic Model Architecture

**Author:** Danny (Lead/Architect)  
**Date:** July 2025  
**Status:** Architecture Review — Actionable Recommendations  
**Requested by:** Dave Grobleski

---

## Executive Summary

The "AAP Rewards Loyalty Model" was deployed as a 1:1 mapping of 10 Lakehouse Delta tables with 7 relationships and 16 DAX measures. This document is the architecture exercise we skipped — a thorough review of the semantic model, its readiness for AI-driven natural language queries via Fabric Data Agent, and the business ontology that underpins it.

**Key findings:**
1. The 1:1 table mapping is structurally sound but needs enrichment (descriptions, synonyms, calculated columns, display folders) to serve AI agents well
2. One shared model is correct for this POC — splitting per-agent would create maintenance burden and break cross-domain queries
3. We need ~20 additional DAX measures, linguistic metadata on every table/column, and a "Prep for AI" configuration pass
4. The agent config files reference SQL view names (`semantic.v_*`) that don't exist in the deployed semantic model — these must be updated to reference actual table names

---

## Part 1: Semantic Model Architecture Review

### 1.1 Current State

**Deployed Model:** AAP Rewards Loyalty Model  
**Source:** Fabric Lakehouse SQL endpoint (dbo schema)

| # | Table | Description | Row Scale |
|---|-------|-------------|-----------|
| 1 | `loyalty_members` | Member profiles, tier, points, contact info | ~5,000 |
| 2 | `transactions` | Purchase/return transactions across channels | ~150,000 |
| 3 | `stores` | Retail store locations (name, region, type) | ~50 |
| 4 | `products` | SKU catalog (category, brand, pricing) | ~200 |
| 5 | `coupons` | Issued coupons (status, dates, redemption) | ~25,000 |
| 6 | `coupon_rules` | Campaign rule definitions (discount, targeting) | ~15 |
| 7 | `points_ledger` | Points earn/burn ledger with running balance | ~100,000 |
| 8 | `csr` | Customer Service Representatives (name, dept) | ~20 |
| 9 | `csr_activities` | CSR interaction log (type, member, details) | ~10,000 |
| 10 | `audit_log` | System audit log (entity changes, actions) | ~50,000 |

**Current Relationships (7):**

| # | From (Many) | To (One) | Join Column |
|---|-------------|----------|-------------|
| 1 | transactions | loyalty_members | member_id |
| 2 | transactions | stores | store_id |
| 3 | points_ledger | loyalty_members | member_id |
| 4 | coupons | loyalty_members | member_id |
| 5 | coupons | coupon_rules | rule_id |
| 6 | csr_activities | csr | csr_id |
| 7 | csr_activities | loyalty_members | member_id |

**Current DAX Measures (16):**

| Table | Measure | Formula |
|-------|---------|---------|
| loyalty_members | Total Members | COUNTROWS(loyalty_members) |
| loyalty_members | Active Members | CALCULATE(COUNTROWS(...), status = "active") |
| loyalty_members | Total Points Balance | SUM(current_points_balance) |
| loyalty_members | Avg Points Balance | AVERAGE(current_points_balance) |
| transactions | Total Revenue | SUM(total) |
| transactions | Total Transactions | COUNTROWS(transactions) |
| transactions | Avg Transaction Value | AVERAGE(total) |
| transactions | Purchase Count | CALCULATE(COUNTROWS(...), type = "purchase") |
| transactions | Return Count | CALCULATE(COUNTROWS(...), type = "return") |
| stores | Total Stores | COUNTROWS(stores) |
| coupons | Coupons Issued | COUNTROWS(coupons) |
| coupons | Coupons Redeemed | CALCULATE(COUNTROWS(...), status = "redeemed") |
| coupons | Coupon Redemption Rate | DIVIDE(redeemed, total, 0) |
| points_ledger | Points Earned | SUM where type = "earn" |
| points_ledger | Points Redeemed | SUM where type = "redeem" |
| csr_activities | Total CSR Interactions | COUNTROWS(csr_activities) |

### 1.2 One Model vs. Multiple Models

**Decision: Keep ONE shared semantic model.**

| Factor | One Model | Multiple (per-agent) |
|--------|-----------|---------------------|
| Cross-domain queries | ✅ Natural joins across tables | ❌ Cannot cross model boundaries |
| Maintenance | ✅ Single source of truth | ❌ 5× measure/relationship duplication |
| Data Agent configuration | ✅ One model reference | ❌ Agent must pick which model to query |
| Consistency | ✅ "Total Revenue" means the same everywhere | ❌ Risk of drift between copies |
| Security/RLS | ✅ Row-level security in one place | ❌ Duplicate RLS definitions |
| POC complexity | ✅ Simple | ❌ Over-engineered for POC |

**Rationale:** All 5 agents query overlapping tables. The Loyalty Program Manager needs transactions for spend analysis. Store Operations needs members for penetration rates. Splitting the model would break these natural cross-domain joins. Instead, we use **display folders** to organize tables/measures by agent domain within the single model.

### 1.3 Relationship Gap Analysis

**Current relationships are correct but incomplete.** Missing relationships:

| # | Proposed Relationship | From → To | Purpose |
|---|----------------------|-----------|---------|
| 8 | coupons → transactions | coupons.redeemed_transaction_id → transactions.transaction_id | Link coupon redemption to the actual transaction — critical for Marketing agent to calculate revenue from coupon-driven purchases |
| 9 | audit_log → loyalty_members | audit_log.entity_id → loyalty_members.member_id (inactive) | Enable audit log filtering by member — useful for Customer Service but must be inactive (audit_log tracks multiple entity types) |

**Relationship #8 is high priority** — without it, the Marketing agent cannot natively traverse from a redeemed coupon to its transaction total. Currently the semantic views handled this with SQL JOINs, but in the semantic model, DAX measures need this relationship.

**Relationship #9 should be deferred** — the audit_log has a polymorphic entity_id column that references different tables depending on entity_type. This is not well-suited for a direct Power BI relationship. Instead, a calculated column or DAX measure should handle this.

### 1.4 DAX Measure Gap Analysis

The 16 existing measures cover basic counts and sums. The agents need significantly more for their stated domains.

#### Missing Measures — By Agent Persona

**Loyalty Program Manager (needs 6 more):**

| Measure | Formula Concept | Why Needed |
|---------|----------------|------------|
| New Members This Month | CALCULATE(COUNTROWS, enrollment_date in current month) | Enrollment trend tracking |
| Churn Risk Members | CALCULATE(COUNTROWS, days_since_last_purchase > 180) | Core churn risk metric |
| Email Opt-In Rate | DIVIDE(SUM(opt_in_email), COUNTROWS) | Communication coverage |
| SMS Opt-In Rate | DIVIDE(SUM(opt_in_sms), COUNTROWS) | Communication coverage |
| Points Liability ($) | SUM(current_points_balance) × 0.01 | Dollar value of outstanding points |
| Avg Lifetime Spend | AVERAGE of member lifetime spend via RELATEDTABLE | Per-member spend for tier analysis |

**Store Operations (needs 4 more):**

| Measure | Formula Concept | Why Needed |
|---------|----------------|------------|
| Return Rate | DIVIDE(Return Count, Purchase Count) | Store return rate comparison |
| Revenue Per Store | DIVIDE(Total Revenue, Total Stores) | Average store performance |
| Unique Members (Transacting) | DISTINCTCOUNT(transactions[member_id]) | Member penetration |
| Avg Items Per Transaction | AVERAGE(transactions[item_count]) | Basket size analysis |

**Marketing & Promotions (needs 4 more):**

| Measure | Formula Concept | Why Needed |
|---------|----------------|------------|
| Coupons Expired | CALCULATE(COUNTROWS, status = "expired") | Funnel: issued → redeemed → expired |
| Coupons Voided | CALCULATE(COUNTROWS, status = "voided") | Funnel completion |
| Outstanding Coupons | CALCULATE(COUNTROWS, status = "issued") | Coupon liability |
| Avg Discount Value | AVERAGE(coupon_rules[discount_value]) | Campaign comparison |

**Merchandising (needs 3 more):**

| Measure | Formula Concept | Why Needed |
|---------|----------------|------------|
| Total Units Sold | SUM via RELATEDTABLE(transaction line items) | Volume metric (requires transaction_items if available) |
| Unique Products Sold | DISTINCTCOUNT of SKU in transactions | Catalog penetration |
| Bonus Eligible Revenue | CALCULATE(Total Revenue, is_bonus_eligible = TRUE) | Loyalty program product impact |

**Customer Service (needs 3 more):**

| Measure | Formula Concept | Why Needed |
|---------|----------------|------------|
| Active CSR Agents | CALCULATE(COUNTROWS(csr), csr_status = "active") | Team size |
| Avg Activities Per CSR | DIVIDE(Total CSR Interactions, Active CSR Agents) | Workload distribution |
| CSR Activities This Month | CALCULATE(COUNTROWS, activity_date in current month) | Current period tracking |

**Total: ~20 additional measures needed** (some may be consolidated).

### 1.5 Calculated Columns & Hierarchies

**Recommended Calculated Columns:**

| Table | Column | Formula | Purpose |
|-------|--------|---------|---------|
| loyalty_members | Full Name | first_name & " " & last_name | Agent-friendly display name |
| loyalty_members | Days Since Last Purchase | DATEDIFF(last_purchase, TODAY()) | Churn risk indicator (requires transaction aggregation) |
| loyalty_members | Member Tenure (Months) | DATEDIFF(enrollment_date, TODAY(), MONTH) | Engagement context |
| transactions | Year-Month | FORMAT(transaction_date, "YYYY-MM") | Time-series grouping |
| coupons | Days to Redemption | DATEDIFF(issued_date, redeemed_date, DAY) | Coupon lifecycle metric |
| coupons | Is Outstanding | IF(status = "issued" && expiry_date >= TODAY(), TRUE, FALSE) | Outstanding coupon flag |

**Recommended Hierarchies:**

| Hierarchy | Levels | Table |
|-----------|--------|-------|
| Geography | Region → State → City → Store | stores |
| Product Category | Category → Subcategory → Brand → Product | products |
| Time | Year → Quarter → Month → Day | transactions (or Date table) |
| Member Tier | Tier | loyalty_members |

**Date Table Recommendation:** The current model lacks a dedicated Date dimension table. For a POC, using the transaction_date column directly is acceptable. For production, a proper Date table should be added and marked as the Date table in the model, enabling time intelligence functions (YTD, QoQ, etc.).

### 1.6 Display Folders

Organize measures into agent-aligned display folders so the Data Agent and any Power BI consumers can find relevant metrics:

| Display Folder | Measures |
|----------------|----------|
| 📊 Membership | Total Members, Active Members, New Members This Month, Email Opt-In Rate, SMS Opt-In Rate, Avg Lifetime Spend |
| 💰 Revenue & Transactions | Total Revenue, Total Transactions, Avg Transaction Value, Purchase Count, Return Count, Return Rate, Avg Items Per Transaction |
| 🏪 Store Performance | Total Stores, Revenue Per Store, Unique Members (Transacting) |
| 🎟️ Coupons & Campaigns | Coupons Issued, Coupons Redeemed, Coupons Expired, Coupons Voided, Outstanding Coupons, Coupon Redemption Rate, Avg Discount Value |
| ⭐ Points & Rewards | Total Points Balance, Avg Points Balance, Points Earned, Points Redeemed, Points Liability ($) |
| 🛡️ Service & Audit | Total CSR Interactions, Active CSR Agents, Avg Activities Per CSR, CSR Activities This Month |
| 📦 Product Performance | Unique Products Sold, Bonus Eligible Revenue |

---

## Part 2: Prep for AI — Making the Model Agent-Ready

### 2.1 What Fabric Data Agent Needs

The Fabric Data Agent translates natural language into DAX queries against a semantic model. Its accuracy depends entirely on how well the model communicates its meaning. A "raw" model with technical column names and no descriptions forces the AI to guess — and it will guess wrong.

**Three pillars of AI readiness:**
1. **Descriptions** — Every table, column, and measure needs a plain-English description
2. **Synonyms** — Alternative names users might say ("revenue" = "sales" = "income")
3. **AI Instructions** — Business context the AI cannot infer from the schema alone

### 2.2 Descriptions Checklist

Every object in the semantic model should have a description. The current model has descriptions on tables and measures but is **missing descriptions on most columns**.

#### Table Descriptions (Current — need review)

| Table | Current Description | Recommended Enhancement |
|-------|-------------------|------------------------|
| loyalty_members | "Loyalty program members — profiles, tiers, contact info, and points balances" | ✅ Good — add: "Each row is one rewards program member. The member_id is the primary key used across all tables." |
| transactions | "Purchase and return transactions across all channels" | ✅ Good — add: "Includes in-store, online, and phone channels. transaction_type is either 'purchase' or 'return'." |
| stores | "Retail store locations — name, address, region, and type" | ✅ Good — add: "store_type is either 'hub' (full-service) or 'satellite' (smaller format)." |
| products | "Product catalog — SKU, category, pricing, and bonus eligibility" | Rename table description to: "Auto parts product catalog. is_bonus_eligible means the product earns bonus loyalty points. is_skip_sku means the product is excluded from points earning." |
| coupons | "Issued coupons — status, dates, and redemption tracking" | Add: "Coupon lifecycle: issued → redeemed/expired/voided. Each coupon is linked to one member and one coupon_rule." |
| coupon_rules | "Coupon campaign rules — discount type, value, targeting, and validity" | Add: "Each rule defines a campaign. target_tier restricts the coupon to members of that tier (or NULL for all tiers). discount_type is 'percent' or 'fixed_dollar'." |
| points_ledger | "Points earn/burn ledger — every points transaction with running balance" | Add: "activity_type values: 'earn', 'redeem', 'adjust', 'expire'. Positive points_amount = earned, negative = redeemed/expired." |
| csr | "Customer Service Representatives — name, department, status" | Add: "Each CSR agent who handles member interactions. csr_status is 'active' or 'inactive'." |
| csr_activities | "CSR interaction log — activity type, member context, and details" | Add: "Every time a CSR agent interacts with a member's account. activity_type values: 'Member Lookup', 'Points Adjustment', 'Coupon Void', 'Tier Inquiry', 'Status Change', 'Enrollment Assist'." |
| audit_log | "System audit log — entity changes, user actions, and timestamps" | Add: "Tracks all system-level changes. entity_type identifies what was changed (member, coupon, transaction, etc.)." |

#### Column Descriptions (Priority — Currently Missing)

Every column needs a description. Here are the high-priority ones that will most impact AI accuracy:

**loyalty_members:**
| Column | Description |
|--------|-------------|
| member_id | Unique identifier for each loyalty program member |
| tier | Current loyalty tier: Bronze, Silver, Gold, or Platinum. Higher tiers earn more points per dollar. |
| member_status | Account status: 'active' or 'inactive'. Only active members can earn/redeem points. |
| enrollment_source | How the member joined: 'in-store', 'website', 'mobile_app', or 'csr_assisted' |
| opt_in_email | Whether the member has opted in to receive email marketing communications |
| opt_in_sms | Whether the member has opted in to receive SMS/text marketing messages |
| diy_account_id | Link to the member's DIY (Do-It-Yourself) commercial account, if any |
| current_points_balance | Member's current available points balance (earned minus redeemed minus expired) |
| lifetime_points_earned | Total points ever earned by this member since enrollment |
| lifetime_points_redeemed | Total points ever redeemed (spent) by this member |

**transactions:**
| Column | Description |
|--------|-------------|
| transaction_type | Either 'purchase' (sale) or 'return' (refund). Revenue calculations should filter to purchases only. |
| total | Transaction total amount in USD including tax |
| subtotal | Transaction amount before tax |
| channel | Sales channel: 'in-store', 'online', or 'phone' |
| item_count | Number of line items (products) in this transaction |

**coupons:**
| Column | Description |
|--------|-------------|
| status | Coupon lifecycle state: 'issued' (active), 'redeemed' (used), 'expired' (past expiry date), or 'voided' (cancelled by CSR) |
| discount_type | Inherited from rule — not on coupon table directly. See coupon_rules. |
| redeemed_transaction_id | Links to the transaction where this coupon was used. NULL if not yet redeemed. |
| source_system | System that issued the coupon: 'GK_Coupon_Mgmt', 'POS', 'Ecomm', 'Customer_First' |

### 2.3 Synonyms / Linguistic Schema

Synonyms tell the AI what alternative names users might use for tables, columns, and values. This is **critical** for natural language accuracy.

#### Table Synonyms

| Table | Synonyms |
|-------|----------|
| loyalty_members | members, customers, loyalty customers, rewards members, program members, enrollees |
| transactions | sales, purchases, orders, transaction history, purchase history |
| stores | locations, shops, retail locations, branches, store locations |
| products | items, SKUs, parts, auto parts, merchandise, catalog |
| coupons | vouchers, discount codes, promo codes, promotions, offers |
| coupon_rules | campaigns, coupon campaigns, promotion rules, discount rules |
| points_ledger | points history, points transactions, rewards points, points log, points activity |
| csr | agents, service reps, customer service agents, support agents, representatives |
| csr_activities | service calls, CSR actions, agent activity, support interactions, service log |
| audit_log | audit trail, change log, activity log, system log |

#### Column Synonyms (High-Impact)

| Table.Column | Synonyms |
|-------------|----------|
| loyalty_members.tier | loyalty tier, member tier, rewards tier, membership level, tier level |
| loyalty_members.member_status | status, account status, membership status |
| loyalty_members.enrollment_date | join date, signup date, registration date, member since |
| loyalty_members.current_points_balance | points, points balance, available points, reward points |
| transactions.total | amount, sale amount, transaction amount, order total, revenue |
| transactions.transaction_date | date, sale date, purchase date, order date |
| transactions.channel | sales channel, purchase channel, order channel |
| transactions.transaction_type | type, sale type |
| stores.region | area, territory, district, market |
| stores.store_type | type, format, store format |
| products.category | product category, part category, department |
| products.brand | manufacturer, make, brand name |
| products.is_bonus_eligible | bonus eligible, bonus points eligible, earns bonus points |
| coupons.status | coupon status, redemption status, state |
| coupon_rules.rule_name | campaign name, promotion name, coupon name |
| coupon_rules.discount_type | discount kind, offer type |
| coupon_rules.target_tier | targeted tier, tier targeting, eligible tier |
| points_ledger.activity_type | point type, points action, earn or redeem |
| csr.csr_name | agent name, rep name, CSR agent |
| csr_activities.activity_type | action type, interaction type, service type |

#### Value Synonyms

| Value | Synonyms |
|-------|----------|
| "purchase" (transaction_type) | sale, buy, bought |
| "return" (transaction_type) | refund, returned |
| "in-store" (channel) | store, brick and mortar, in person, walk-in |
| "online" (channel) | web, website, ecommerce, digital |
| "phone" (channel) | call, telephone, phone order |
| "Bronze" (tier) | basic, starter, entry level |
| "Silver" (tier) | second tier, mid-tier |
| "Gold" (tier) | third tier, premium |
| "Platinum" (tier) | top tier, highest tier, VIP, elite |
| "active" (member_status) | current, enrolled, participating |
| "inactive" (member_status) | churned, lapsed, dormant, cancelled |
| "redeemed" (coupon status) | used, applied, claimed |
| "expired" (coupon status) | lapsed, timed out |
| "voided" (coupon status) | cancelled, removed, revoked |
| "earn" (points activity_type) | earned, accrual, credit |
| "redeem" (points activity_type) | redeemed, spent, burned, used |
| "hub" (store_type) | full-service store, main store |
| "satellite" (store_type) | small format, mini store |

### 2.4 AI Instructions

These are natural language instructions added to the semantic model's "Prep for AI" configuration. They provide business context the AI cannot infer from the data.

**Recommended AI Instructions:**

```
BUSINESS CONTEXT:
This is the AAP (Advanced Auto Parts) Rewards & Loyalty program database.
AAP is a national auto parts retailer with approximately 500 stores across the United States.
The rewards program has ~5,000 members across four tiers: Bronze, Silver, Gold, and Platinum.

TIER DEFINITIONS:
- Bronze: Entry level. All new members start at Bronze. 1× points multiplier.
- Silver: $500+ annual spend. 1.5× points multiplier.
- Gold: $1,500+ annual spend. 2× points multiplier.
- Platinum: $3,000+ annual spend. 3× points multiplier.

POINTS SYSTEM:
- Members earn 1 base point per dollar spent (before multiplier).
- Points value: approximately $0.01 per point for liability calculations.
- Points can expire after 12 months of account inactivity.

IMPORTANT CALCULATION RULES:
- Revenue should ALWAYS filter to transaction_type = 'purchase'. Returns should not be included in revenue.
- Return Rate = Return Count / Purchase Count (not total transactions).
- Coupon Redemption Rate = Redeemed / Issued (not expired or voided in denominator).
- "Active members" means member_status = 'active'.
- Churn risk: members with 180+ days since last purchase are considered at risk.

DATA TIME RANGE:
- Transaction data spans January 2025 through April 2026.
- Always mention the date range when reporting trends.

PRODUCT CONTEXT:
- "Skip SKU" (is_skip_sku = true) means the product is excluded from earning loyalty points.
- "Bonus eligible" (is_bonus_eligible = true) means the product earns extra bonus points.
- Auto parts categories include: Batteries, Oil & Fluids, Brakes, Filters, Wipers, Spark Plugs, Lighting, Coolant, Accessories, Electrical.

COUPON SYSTEM:
- Coupons are issued under campaign rules (coupon_rules table).
- discount_type is 'percent' (percentage off) or 'fixed_dollar' (flat amount off).
- target_tier restricts the campaign to members of a specific tier. NULL means all tiers.
- Coupon lifecycle: issued → redeemed OR expired OR voided.

STORE TYPES:
- "hub" stores are full-service, larger format stores.
- "satellite" stores are smaller neighborhood format.
```

### 2.5 Verified Answers

For high-stakes business questions, configure verified answers so the Data Agent returns a specific, validated DAX query instead of generating one:

| Business Question | Verified DAX | Why |
|------------------|-------------|-----|
| "How many active members do we have?" | [Active Members] measure | Prevents AI from using total members |
| "What's our total revenue?" | CALCULATE([Total Revenue], transactions[transaction_type] = "purchase") | Ensures returns are excluded |
| "What's the coupon redemption rate?" | [Coupon Redemption Rate] measure | Prevents incorrect denominator |
| "What's our points liability?" | [Points Liability ($)] measure | Ensures correct dollar conversion |

### 2.6 Prep for AI Configuration Checklist

| # | Task | Status | Priority |
|---|------|--------|----------|
| 1 | Add descriptions to ALL columns (see §2.2) | ❌ Not done | 🔴 Critical |
| 2 | Add synonyms to all tables (see §2.3) | ❌ Not done | 🔴 Critical |
| 3 | Add synonyms to high-impact columns (see §2.3) | ❌ Not done | 🔴 Critical |
| 4 | Add value synonyms for filter values (see §2.3) | ❌ Not done | 🟡 High |
| 5 | Write AI Instructions in Prep for AI pane (see §2.4) | ❌ Not done | 🔴 Critical |
| 6 | Configure verified answers for top 4 business questions (see §2.5) | ❌ Not done | 🟡 High |
| 7 | Add ~20 missing DAX measures (see §1.4) | ❌ Not done | 🔴 Critical |
| 8 | Add calculated columns (Full Name, Days Since, etc.) (see §1.5) | ❌ Not done | 🟡 High |
| 9 | Create display folders for measures (see §1.6) | ❌ Not done | 🟢 Medium |
| 10 | Add Geography and Product hierarchies (see §1.5) | ❌ Not done | 🟢 Medium |
| 11 | Add relationship: coupons → transactions (see §1.3) | ❌ Not done | 🔴 Critical |
| 12 | Test 25 sample questions against the model | ❌ Not done | 🟡 High |
| 13 | Review and iterate based on test results | ❌ Not done | 🟡 High |
| 14 | Configure AI Data Schema (minimize exposed fields) | ❌ Not done | 🟢 Medium |

---

## Part 3: Business Ontology

### 3.1 Domain: AAP Rewards & Loyalty Program

The AAP Rewards program is a **tiered loyalty program** for an auto parts retailer. The core business concepts, their definitions, and their relationships are documented below.

### 3.2 Business Concept Hierarchy

```
AAP REWARDS & LOYALTY PROGRAM
│
├── MEMBERS (Who)
│   ├── Member Profile — name, contact info, enrollment source, DIY account
│   ├── Tier Status — Bronze → Silver → Gold → Platinum (based on annual spend)
│   ├── Points Balance — current available points, lifetime earned/redeemed
│   ├── Communication Preferences — email opt-in, SMS opt-in
│   └── Engagement Status — active, at-risk (180+ days), inactive/churned
│
├── TRANSACTIONS (What happened)
│   ├── Purchases — member bought auto parts (revenue-generating)
│   ├── Returns — member returned auto parts (revenue-reducing)
│   ├── Channels — in-store, online, phone
│   └── Basket — items, subtotal, tax, total
│
├── PRODUCTS (What was bought)
│   ├── Catalog — SKU, name, brand, category, subcategory
│   ├── Pricing — list price
│   ├── Loyalty Attributes — bonus eligible, skip SKU
│   └── Categories — Batteries, Oil, Brakes, Filters, Wipers, Spark Plugs,
│                     Lighting, Coolant, Accessories, Electrical
│
├── STORES (Where)
│   ├── Location — city, state, ZIP, region
│   ├── Format — hub (full-service) or satellite (smaller)
│   └── Performance — revenue, transactions, member penetration
│
├── COUPONS & CAMPAIGNS (Promotions)
│   ├── Campaign Rules — discount type/value, minimum purchase, tier targeting, validity
│   ├── Coupon Lifecycle — issued → redeemed / expired / voided
│   ├── Redemption — linked to a specific transaction
│   └── Source Systems — GK Coupon Management, POS, Ecomm, Customer First
│
├── POINTS & REWARDS (Loyalty currency)
│   ├── Earning — points earned per purchase (base rate × tier multiplier)
│   ├── Redemption — points spent on rewards or discounts
│   ├── Adjustments — manual corrections by CSR agents
│   ├── Expiration — points expire after 12 months of inactivity
│   └── Liability — outstanding points balance valued at $0.01/point
│
└── SERVICE & AUDIT (Operations)
    ├── CSR Agents — name, department (Customer Support / Loyalty Services)
    ├── Interactions — member lookups, points adjustments, coupon voids,
    │                  tier inquiries, status changes, enrollment assists
    └── Audit Trail — system-level entity changes with timestamps
```

### 3.3 Entity Relationship Map (Business Terms)

```
                                    ┌─────────────┐
                                    │   MEMBER     │
                                    │  (customer)  │
                                    └──────┬───────┘
                           ┌───────────────┼────────────────┬──────────────┐
                           │               │                │              │
                    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌────▼─────┐
                    │ TRANSACTIONS │ │   POINTS    │ │   COUPONS   │ │   CSR    │
                    │  (shopping)  │ │  (rewards)  │ │  (promos)   │ │ACTIVITY  │
                    └──────┬───┬──┘ └─────────────┘ └──────┬──────┘ └──────────┘
                           │   │                           │
                    ┌──────▼──┐└──────────┐         ┌──────▼──────┐
                    │  STORE  │           │         │  CAMPAIGN   │
                    │ (where) │    ┌──────▼──────┐  │   RULES     │
                    └─────────┘    │  PRODUCTS   │  │ (promotion  │
                                   │  (what)     │  │  definitions)│
                                   └─────────────┘  └─────────────┘

Relationship Key (in business terms):
─────────────────────────────────────
• A MEMBER makes many TRANSACTIONS at different STORES
• A MEMBER earns and redeems POINTS through their purchases
• A MEMBER receives COUPONS issued under CAMPAIGN RULES
• A MEMBER is served by CSR AGENTS who log their ACTIVITIES
• A TRANSACTION happens at one STORE and contains multiple PRODUCTS
• A COUPON, when redeemed, is linked to the TRANSACTION where it was used
• CAMPAIGN RULES define the terms of COUPON promotions (targeting, discount, validity)
```

### 3.4 Domain Vocabulary / Glossary

| Term | Definition | Where in Model |
|------|-----------|----------------|
| **Member** | A person enrolled in the AAP Rewards loyalty program. Identified by member_id. | loyalty_members |
| **Tier** | Loyalty level based on annual spend. Four tiers: Bronze ($0+), Silver ($500+), Gold ($1,500+), Platinum ($3,000+). Higher tiers earn more points per dollar. | loyalty_members.tier |
| **Active Member** | A member with member_status = 'active'. Can earn and redeem points. | loyalty_members.member_status |
| **Churned/Lapsed Member** | A member with member_status = 'inactive' or 180+ days since last purchase. | Calculated from transactions |
| **Points** | The loyalty currency. Members earn points on purchases (1 point per $1 × tier multiplier). Points can be redeemed for rewards. | points_ledger |
| **Points Liability** | The total dollar value of unredeemed points across all members. Valued at $0.01 per point. | Calculated measure |
| **Points Multiplier** | Tier benefit: Bronze 1×, Silver 1.5×, Gold 2×, Platinum 3×. Applied to base points earn rate. | Business rule (not in data) |
| **Transaction** | A purchase or return event. Always linked to one member and one store. | transactions |
| **Purchase** | A revenue-generating transaction (transaction_type = 'purchase'). | transactions |
| **Return** | A refund transaction (transaction_type = 'return'). Reduces revenue. | transactions |
| **Channel** | How the transaction occurred: in-store, online, or phone. | transactions.channel |
| **Store** | A physical AAP retail location. Either "hub" (full-service) or "satellite" (smaller format). | stores |
| **Region** | Geographic grouping of stores (e.g., Northeast, Southeast, Midwest, Southwest, West). | stores.region |
| **SKU** | Stock Keeping Unit — unique product identifier. | products.sku |
| **Bonus Eligible** | A product that earns extra bonus loyalty points when purchased. | products.is_bonus_eligible |
| **Skip SKU** | A product excluded from earning any loyalty points (e.g., gift cards, services). | products.is_skip_sku |
| **Coupon** | A discount offer issued to a specific member under a campaign rule. | coupons |
| **Campaign Rule** | The definition of a coupon promotion — discount type, value, minimum purchase, tier targeting, validity period. | coupon_rules |
| **Redemption Rate** | Percentage of issued coupons that were redeemed. Denominator = issued (not total including expired). | Calculated: redeemed / issued |
| **Discount Type** | How the discount is applied: 'percent' (e.g., 15% off) or 'fixed_dollar' (e.g., $10 off). | coupon_rules.discount_type |
| **Target Tier** | The member tier a campaign is restricted to. NULL means available to all tiers. | coupon_rules.target_tier |
| **CSR** | Customer Service Representative — an agent who handles member interactions. | csr |
| **CSR Activity** | A logged interaction between a CSR agent and a member's account. Types: Member Lookup, Points Adjustment, Coupon Void, Tier Inquiry, Status Change, Enrollment Assist. | csr_activities |
| **Audit Trail** | System-level log of all entity changes (who changed what, when, and what the change was). | audit_log |
| **DIY Account** | "Do-It-Yourself" commercial account — links a rewards member to their commercial/pro account. | loyalty_members.diy_account_id |
| **Enrollment Source** | How a member joined the program: in-store (POS), website, mobile app, or CSR-assisted. | loyalty_members.enrollment_source |
| **Source System** | The system that originated a data record: POS, Ecomm, Sterling (OMS), Customer First, CrowdTwist, GK Coupon Management. | Various tables |

### 3.5 Ontology → Semantic Model Mapping

| Business Concept | Model Table(s) | Key Columns | Primary Agent(s) |
|-----------------|----------------|-------------|-------------------|
| Member Profile | loyalty_members | member_id, name, email, tier, status | Loyalty Program Manager, Customer Service |
| Member Engagement | loyalty_members + transactions + points_ledger | Computed: spend, frequency, recency | Loyalty Program Manager |
| Purchase History | transactions + stores | transaction_id, date, total, channel, store | Store Operations, Merchandising |
| Product Performance | products (+ transaction_items if available) | sku, category, brand, price | Merchandising |
| Store Performance | stores + transactions | store_id, region, type + aggregated metrics | Store Operations |
| Coupon Lifecycle | coupons + coupon_rules | coupon_id, status, rule_name, discount | Marketing & Promotions |
| Campaign Effectiveness | coupon_rules + coupons + transactions | rule metrics + revenue from redemptions | Marketing & Promotions |
| Points Economy | points_ledger + loyalty_members | points earned/redeemed/balance | Loyalty Program Manager |
| CSR Operations | csr + csr_activities | agent, activity type, member context | Customer Service |
| Audit & Compliance | audit_log + csr_activities | entity changes, timestamps, who | Customer Service |

---

## Part 4: Agent-to-Model Mapping

### 4.1 Agent → Table Access Matrix

This table shows which semantic model tables each agent persona needs:

| Table | Customer Service | Loyalty Manager | Marketing | Merchandising | Store Ops |
|-------|:---:|:---:|:---:|:---:|:---:|
| loyalty_members | 🟢 Primary | 🟢 Primary | 🔵 Secondary | ⚪ Rare | 🔵 Secondary |
| transactions | 🔵 Secondary | 🔵 Secondary | 🔵 Secondary | 🟢 Primary | 🟢 Primary |
| stores | ⚪ — | ⚪ — | ⚪ — | 🔵 Secondary | 🟢 Primary |
| products | ⚪ — | ⚪ — | ⚪ — | 🟢 Primary | ⚪ — |
| coupons | 🔵 Secondary | 🔵 Secondary | 🟢 Primary | ⚪ — | ⚪ — |
| coupon_rules | ⚪ — | ⚪ — | 🟢 Primary | ⚪ — | ⚪ — |
| points_ledger | 🔵 Secondary | 🟢 Primary | ⚪ — | ⚪ — | ⚪ — |
| csr | 🟢 Primary | ⚪ — | ⚪ — | ⚪ — | ⚪ — |
| csr_activities | 🟢 Primary | ⚪ — | ⚪ — | ⚪ — | 🔵 Secondary |
| audit_log | 🟢 Primary | ⚪ — | ⚪ — | ⚪ — | ⚪ — |

Legend: 🟢 Primary (core to agent's job) | 🔵 Secondary (needed for context) | ⚪ Not used

### 4.2 Agent → Measure Mapping

| Measure | Cust Svc | Loyalty | Marketing | Merch | Store Ops |
|---------|:---:|:---:|:---:|:---:|:---:|
| Total Members | ✓ | ✓ | | | |
| Active Members | ✓ | ✓ | | | |
| New Members This Month | | ✓ | | | |
| Churn Risk Members | | ✓ | | | |
| Email/SMS Opt-In Rate | | ✓ | | | |
| Points Liability ($) | | ✓ | | | |
| Total Revenue | | | | ✓ | ✓ |
| Total Transactions | | | | | ✓ |
| Avg Transaction Value | | | | | ✓ |
| Purchase/Return Count | | | | | ✓ |
| Return Rate | | | | ✓ | ✓ |
| Total Stores | | | | | ✓ |
| Revenue Per Store | | | | | ✓ |
| Coupons Issued/Redeemed | ✓ | | ✓ | | |
| Coupon Redemption Rate | | | ✓ | | |
| Coupons Expired/Voided | | | ✓ | | |
| Points Earned/Redeemed | | ✓ | | | |
| Total CSR Interactions | ✓ | | | | |
| Active CSR Agents | ✓ | | | | |
| Avg Activities Per CSR | ✓ | | | | |

---

## Part 5: Prioritized Recommendations

### Phase 1 — Critical (Do Immediately)

| # | Action | Owner | Effort |
|---|--------|-------|--------|
| 1 | Add relationship: coupons → transactions via redeemed_transaction_id | Data Engineer | 15 min |
| 2 | Add column descriptions to all tables (see §2.2 templates) | Data Engineer | 2 hours |
| 3 | Add table and column synonyms (see §2.3) | Data Engineer | 1 hour |
| 4 | Write AI Instructions in Prep for AI pane (see §2.4) | Lead Architect | 30 min |
| 5 | Add 20 missing DAX measures (see §1.4) | Data Engineer | 3 hours |
| 6 | Update agent config.json files to reference actual table names | Backend Dev | 30 min |
| 7 | Add calculated column: Full Name on loyalty_members | Data Engineer | 15 min |

### Phase 2 — High Priority (This Sprint)

| # | Action | Owner | Effort |
|---|--------|-------|--------|
| 8 | Configure verified answers for top business questions | Lead Architect | 1 hour |
| 9 | Add remaining calculated columns (see §1.5) | Data Engineer | 1 hour |
| 10 | Create display folders for measures (see §1.6) | Data Engineer | 30 min |
| 11 | Run 25 sample questions and validate answers | QA/Lead | 2 hours |
| 12 | Iterate synonyms and descriptions based on test results | Data Engineer | 1 hour |

### Phase 3 — Medium Priority (Next Sprint)

| # | Action | Owner | Effort |
|---|--------|-------|--------|
| 13 | Add Geography and Product hierarchies | Data Engineer | 1 hour |
| 14 | Add a proper Date dimension table | Data Engineer | 2 hours |
| 15 | Configure AI Data Schema to minimize exposed fields | Lead Architect | 1 hour |
| 16 | Add value synonyms for filter values (see §2.3) | Data Engineer | 1 hour |

---

## Appendix A: Current vs. Recommended View-to-Table Mapping

The agent configs previously referenced SQL views (`semantic.v_*`). The semantic model contains the raw tables. This mapping shows the correspondence:

| Old View Name | Semantic Model Table(s) | Notes |
|--------------|------------------------|-------|
| semantic.v_member_summary | loyalty_members + points_ledger + transactions | View aggregated data; in semantic model, use relationships + measures |
| semantic.v_member_engagement | loyalty_members + transactions + points_ledger + coupons | Computed engagement metrics; needs calculated columns or measures |
| semantic.v_transaction_history | transactions + loyalty_members + stores | Use model relationships for joins |
| semantic.v_points_activity | points_ledger + loyalty_members | Direct relationship exists |
| semantic.v_coupon_activity | coupons + coupon_rules + loyalty_members | Direct relationships exist |
| semantic.v_campaign_effectiveness | coupon_rules + coupons + transactions | Needs new relationship (coupons → transactions) |
| semantic.v_store_performance | stores + transactions | Use model relationships for aggregation |
| semantic.v_product_popularity | products (+ transactions if line items available) | Products table exists in model |
| semantic.v_audit_trail | csr_activities + csr + loyalty_members | Direct relationships exist |

---

*This document is the authoritative architecture reference for the AAP Rewards Loyalty semantic model. All changes to the model should be reviewed against this document.*
