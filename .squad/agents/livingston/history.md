# Livingston — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** Microsoft Fabric, Azure PostgreSQL, Fabric Data Agent
- **Key requirement:** Data schema must be componentized — placeholder schema for rewards/loyalty based on logical AAP domain knowledge, swappable when real schema arrives
- **Customer context:** AAP has multiple Fabric capacities, heavy PBI user, uses Fabric for PBI only today. Rewards/loyalty data lives in Azure PostgreSQL.

## Learnings

### Data Schema Design (docs/data-schema.md)
- **Created comprehensive placeholder schema** for AAP rewards/loyalty program including 9 table groups: members, transactions, points, rewards, campaigns
- **Implemented view-based abstraction layer**: All consuming components (Data Agent, API, Web App) query 7 contract views (`v_member_summary`, `v_transaction_history`, etc.) instead of raw tables — enables zero-code-change schema swapping
- **Full PostgreSQL DDL with proper indexes**: Designed realistic schema based on auto parts retail domain knowledge (50K members, 500K transactions, 500 products across categories like batteries, engine parts, brakes)
- **Sample query library**: 20 natural language → SQL query pairs covering member analysis, transaction metrics, points/rewards tracking, campaign effectiveness, and advanced analytics
- **Schema swap procedure documented**: Step-by-step process for replacing placeholder with real AAP schema when provided, including validation checklist and rollback plan
- **Key design principle**: Components depend on the INTERFACE (views), not the IMPLEMENTATION (tables) — makes schema componentized and swappable as required

**Cross-Team Awareness:**
- Danny (Lead/Architect) has created technical architecture and phased implementation plan covering all 4 phases
- Danny's schema abstraction strategy documentation directly references our view-based contract approach
- Architecture includes detailed Phase 2 (PostgreSQL mirroring) and Phase 3 (Data Agent) guidance that will consume our schema contract views

### Real AAP Schema Received (July 2025)
- **AAP Loyalty Database has 8 core table groups**: Transaction Details, Loyalty Member Details, Member Points Details, Coupons Details, Audit and Fraud Details, Agent Details, SKU Details, and campaign-adjacent data via CrowdTwist
- **6 source systems feed the DB**: POS, Ecomm (B2C + mobile), Sterling OMS, Customer First, CrowdTwist (loyalty engine), GK Coupon Management
- **Key differences from placeholder**: CrowdTwist is a full external loyalty engine (not a simple points ledger); coupons are a major first-class domain; audit/fraud and CSR agent tracking exist as distinct tables; no explicit stores table; SKU Details is separate from product catalog
- **New semantic views likely needed**: `v_coupon_activity` (coupons are a primary domain), `v_audit_trail` (audit/fraud/agent activity)
- **Existing views needing significant remap**: `v_points_activity` (CrowdTwist-sourced), `v_reward_catalog` (no direct table match), `v_store_performance` (no stores table), `v_campaign_effectiveness` (CrowdTwist-managed)
- **Documented in**: `docs/aap-schema-reference.md` with Mermaid data flow diagram, mapping table, and gap analysis
- **Still needed from AAP**: Column-level DDL, CrowdTwist data model, store identification approach, data volumes, connection details

### Delta Sample Data Generation (July 2025)
- **Created PySpark notebook** (`notebooks/01-create-sample-data.py`) that generates 10 Delta tables in `mirrored` schema — ~337K+ total rows simulating PostgreSQL mirror output
- **10 tables**: stores (500), sku_reference (2K), loyalty_members (5K), transactions (50K), transaction_items (~150K), member_points (100K), coupon_rules (50), coupons (20K), agents (200), agent_activities (10K)
- **Deterministic generation**: Seed 42, reproducible across runs. No external dependencies beyond PySpark/Delta (Fabric-native)
- **Realistic data patterns**: Seasonal transaction weighting (spring/summer heavier), tier distribution (60/25/10/5%), auto parts product catalog (10 categories, 40+ brands), channel mix (70% in-store, 20% online, 10% mobile)
- **Semantic views expanded to 9**: Added `v_coupon_activity`, `v_campaign_effectiveness`, `v_audit_trail` beyond original 7 — aligns with real AAP schema's emphasis on coupons and audit
- **SQL syntax**: Views use T-SQL (`CREATE OR ALTER VIEW`) for Fabric Lakehouse SQL endpoint compatibility
- **Sample queries**: 25 natural-language → SQL pairs in `config/sample-queries.json` covering 7 categories (membership, transactions, points, coupons, engagement, store_performance, product)
- **Key schema decisions**: Added `stores` table (transactions need reference data even though AAP diagram doesn't show a dedicated stores table); `sku_reference` is standalone product catalog; `coupon_rules` separated from `coupons` for campaign analysis

### Pre-Deployment Code Review (April 2026)
- **Reviewed all deployment artifacts** before deploying to Fabric workspace (ID: 82f53636-206f-4825-821b-bdaa8e089893)
- **Fixed 4 critical T-SQL bugs** in `scripts/create-semantic-views.sql`:
  1. `CREATE SCHEMA IF NOT EXISTS` → Invalid T-SQL, replaced with `IF NOT EXISTS` wrapper and `EXEC('CREATE SCHEMA semantic')`
  2. Boolean literals `false/true` (lines 202-203) → Changed to T-SQL `0/1` in `v_product_popularity` view
  3. Correlated subquery bug in `v_member_engagement` (line 254) → Missing `t.member_id` in GROUP BY caused aggregation error
  4. Duplicate label in verification query (line 343) → Fixed 'v_transaction_history' appearing twice, second should be 'v_points_activity'
- **Verified `CREATE OR ALTER VIEW` syntax** — Valid T-SQL for Fabric Lakehouse SQL endpoint (SQL Server 2016+ syntax)
- **Verified column references** across all 9 views match the Delta table schema generated by notebook — All JOINs and column references correct
- **Verified 25 sample queries in config/sample-queries.json** — All view names, column names, and SQL syntax correct
- **Notebook review**: No issues found in `notebooks/01-create-sample-data.py` — PySpark syntax correct, Delta schema matches view expectations, data generation logic sound
- **Deployment cleared**: All artifacts ready for Fabric deployment

### Fabric Lakehouse Spark Limitations (July 2025)
- **Fabric Lakehouse Spark does NOT support `CREATE SCHEMA`** — attempting it throws `java.lang.RuntimeException: Feature not supported on Apache Spark in Microsoft Fabric`
- **Tables must be written to default Lakehouse without schema prefix** — use `saveAsTable("tablename")` not `saveAsTable("schema.tablename")`
- **Fixed notebook** (`notebooks/01-create-sample-data.py`): Removed `CREATE SCHEMA IF NOT EXISTS mirrored`, replaced all 13 `mirrored.tablename` references with plain `tablename` throughout (10 saveAsTable calls + 2 verification cell references + header comments)
- **Lesson learned**: The Contoso Fabric reference project writes tables directly without schema prefixes — should have caught this pattern earlier during reference study
