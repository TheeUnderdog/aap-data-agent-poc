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

### CSR Table Rename (July 2025)
- **Renamed `agents` → `csr` and `agent_activities` → `csr_activities`** across all artifacts to eliminate "agent" overload (AI agents vs customer service reps)
- **Column renames**: `agent_id` → `csr_id`, `agent_name` → `csr_name`, `agent_email` → `csr_email`, `agent_department` → `csr_department` (in v_audit_trail view)
- **Files changed**: `notebooks/01-create-sample-data.py` (table generation + schema + summary), `scripts/create-semantic-views.sql` (v_audit_trail view), `config/sample-queries.json` (1 query updated)
- **Not changed**: `agents/` folder configs use "agent" in natural language (business persona context), not as data column references — no rename needed there
- **Key pattern**: When a term is overloaded in the project, rename the data layer first since it's the contract that downstream consumers depend on

### CSR Rename Completion — Data Layer Finalization (April 2026)
- **Completed full CSR table rename initiative** across all remaining data layer references
- **Verified zero stale references** — All notebook, view, config, and query references use new `csr`/`csr_activities` table names
- **Orchestration log:** `.squad/orchestration-log/2026-04-24T15-59-00Z-livingston.md`
- **Status:** Complete — data layer contract stabilized for downstream semantic model and Data Agent consumption

### Notebook Redeployment with CSR Rename (April 2026)
- **Redeployed `01-create-sample-data` notebook** to Fabric workspace `82f53636-206f-4825-821b-bdaa8e089893` using `--force --skip-run`
- **Old notebook ID:** `351e2490-024b-43ff-b1fa-bef3d8d274e6` (deleted)
- **New notebook ID:** `f0af7753-cfef-47f5-8c0f-43ded9218b66`
- **Purpose:** Push CSR rename changes (agents→csr, agent_activities→csr_activities) to Fabric
- **409 conflict encountered** on first attempt due to Fabric propagation delay after delete — resolved by waiting 10 seconds and retrying
- **Notebook uploaded but not executed** (`--skip-run`) — Dave will run manually in the Fabric portal
- **Portal link:** https://app.fabric.microsoft.com/groups/82f53636-206f-4825-821b-bdaa8e089893/notebooks/f0af7753-cfef-47f5-8c0f-43ded9218b66
- **Lesson learned:** Fabric's item delete API returns success before the item is fully purged — always build in a retry with delay when using `--force` redeployment

### Semantic View Deployment to Fabric (July 2025)
- **Deployed all 9 semantic views** to Fabric Lakehouse SQL endpoint via `deploy-views.py`
- **Fixed SQL parser bug in deploy-views.py**: `split_sql_on_go()` had a comment-filter that discarded any SQL block starting with `--` (line comments). Since every block in `create-semantic-views.sql` begins with comment headers, the parser found 0 statements. Fixed by replacing `re.match(r'^\s*--', trimmed)` with a check that strips all comment lines first and only skips blocks that are *entirely* comments.
- **10 statements executed**: 1 schema creation (`semantic`) + 9 `CREATE OR ALTER VIEW` statements
- **Views deployed**: v_member_summary, v_transaction_history, v_points_activity, v_coupon_activity, v_store_performance, v_product_popularity, v_member_engagement, v_campaign_effectiveness, v_audit_trail
- **Driver used**: Invoke-Sqlcmd (PowerShell) — pyodbc was available but the script fell through to the PowerShell fallback path
- **Auth**: InteractiveBrowserCredential (browser popup, manual auth by Dave)
- **All views reference CSR-renamed tables** (csr, csr_activities) — no stale agent/agent_activities references
- **Lesson learned**: Always test SQL parser with real SQL files that contain comment headers — the `re.match(r'^\s*--')` pattern is a common gotcha when SQL blocks have leading comments

### SQL Views vs Semantic Models — Key Fabric Distinction (July 2025)
- **SQL views ≠ Semantic models** — they are fundamentally different Fabric concepts
- **SQL views**: Database objects inside the SQL Analytics Endpoint, visible in object explorer. Created via `CREATE OR ALTER VIEW`. This is what `deploy-views.py` creates.
- **Semantic models** (formerly Power BI datasets): Workspace-level items that appear in the Fabric workspace item list alongside Lakehouses, Notebooks, etc. Created via Fabric portal, REST API, or XMLA/TMSL.
- **Lakehouse default semantic model**: Auto-generated, includes all Delta tables in `dbo` schema. Does NOT automatically include custom views in other schemas (like `semantic`).
- **Created `scripts/verify-views.py`**: Uses Fabric REST API to list workspace items and Invoke-Sqlcmd to verify views exist on the SQL endpoint. Shows distinction between workspace items and SQL objects.
- **Created `scripts/create-semantic-model.py`**: Uses Fabric REST API (`POST /v1/workspaces/{id}/semanticModels`) with TMDL definition to create a workspace-level semantic model from our 9 views. Each view becomes a model table with M expression sourcing from `semantic.{view_name}`.
- **TMDL format**: Fabric REST API expects definition as `parts` array with base64-encoded `.tmdl` files — one `model.tmdl` root + one per table.
- **Fallback TMSL**: Also generates `semantic-model-tmsl.json` for import via SSMS or Tabular Editor if REST API fails.
- **Lesson learned**: When someone says "I see zero semantic models" after deploying SQL views, the answer is always "those are different things" — need to create a semantic model separately

### Semantic Model Architecture Shift — Direct Delta Table Mapping (April 2026)
- **PIVOTED AWAY from semantic views** after Danny (Lead/Architect) completed architecture review in `docs/semantic-model-architecture.md`
- **Key finding**: SQL views add NO value when we already have a semantic model (the BI layer). Views were redundant abstraction. Semantic model IS the business layer.
- **New approach**: Semantic model sources directly from 10 Lakehouse Delta tables (`dbo` schema) — 1:1 mapping with relationships, DAX measures, and descriptions
- **Updated `scripts/create-semantic-model.py`**: Changed from sourcing `semantic.v_*` views to sourcing `dbo.tablename` tables. Each table's partition uses M expression: `Sql.Database(...){[Schema="dbo", Item="tablename"]}[Data]`
- **Deployed "AAP Rewards Loyalty Model"** to workspace with 10 tables, 7 relationships, 16 DAX measures as baseline
- **Lesson learned**: TMDL does NOT support table-level `description` property (causes parse error). Only table annotations work. Also `lineageTag` is not supported.
- **Agent configs updated**: Deprecated references to `semantic.v_*` views. Agents now query the semantic model via Fabric Data Agent, not SQL views.
- **Views remain deployed** but are not actively used. Semantic model is the single source of truth for BI and AI agents.

### Phase 1 Semantic Model Enrichment (April 2026)
- **Implemented ALL Phase 1 critical items** from `docs/semantic-model-architecture.md` architecture review
- **Added missing relationship**: `coupons → transactions` via `redeemed_transaction_id` (INACTIVE to avoid ambiguous path coupons → transactions → loyalty_members)
- **Added column descriptions to all 10 tables**: Extended column tuples from `(name, type, label)` to `(name, type, label, description)`. Every column now has AI-readable plain-English description.
- **Added ~20 missing DAX measures** organized into 6 display folders:
  - 📊 Membership (7 measures): New Members This Month, Churn Risk Members, Email/SMS Opt-In Rates, Avg Lifetime Spend, Points Liability ($)
  - 💰 Revenue & Transactions (8 measures): Total Revenue (purchase-only), Return Rate, Avg Items Per Transaction, Unique Members (Transacting)
  - 🏪 Store Performance (2 measures): Revenue Per Store
  - 🎟️ Coupons & Campaigns (7 measures): Coupons Expired/Voided/Outstanding, Avg Discount Value
  - ⭐ Points & Rewards (5 measures): Points Liability ($), Total/Avg Points Balance
  - 🛡️ Service & Audit (4 measures): Active CSR Agents, Avg Activities Per CSR, CSR Activities This Month
  - 📦 Product Performance (1 measure): Unique Products Sold
- **Display folders**: Measures grouped for AI Data Agent and Power BI usability. Set via `displayFolder: "folder name"` property in TMDL.
- **Column descriptions via annotations**: TMDL doesn't support native column-level `description` property, so added as `annotation Description = "..."` instead
- **Total metrics**: 10 tables, 8 relationships (1 inactive), 34 DAX measures (up from 16), all columns described
- **Ambiguous path resolution**: coupons → transactions relationship marked inactive to avoid conflict with direct coupons → loyalty_members path. DAX measures can use `USERELATIONSHIP()` to activate when needed.
- **Deployment**: Successfully deployed to workspace 82f53636-206f-4825-821b-bdaa8e089893 via `python scripts/create-semantic-model.py --force`
- **TMDL lessons learned**:
  - Table-level `description` NOT supported (parse error)
  - Column-level native `description` NOT supported → use annotations
  - `displayFolder` on measures IS supported
  - Inactive relationships: use `isActive: false` property in relationship TMDL
  - Emoji in display folder names work fine (UTF-8 encoding handled correctly)
- **Ready for Phase 2**: Synonyms, AI instructions, verified answers via Fabric portal "Prep for AI" UI

### Linguistic Schema & AI Instructions Script (July 2025)
- **Created `scripts/configure-linguistic-schema.py`** — configures synonyms and AI instructions via Fabric REST API updateDefinition
- **Approach**: Uses the `Copilot/` folder structure in the semantic model definition (documented in Fabric REST API definition spec). AI instructions go in `Copilot/Instructions/instructions.md`, linguistic metadata (synonyms) in `Copilot/linguisticMetadata.json`, settings in `Copilot/settings.json`.
- **Synonyms scope**: 10 tables (50 synonyms), 20 columns (66 synonyms), 7 columns with value synonyms (53 total). CSR tables prioritized — "agents", "reps", "representatives" all map to `csr` table.
- **AI Instructions**: 53-line business context block covering tier definitions, points system, calculation rules, data time range, product context, coupon system, store types, and explicit table name guidance for ambiguous terms.
- **Script features**: `--dry-run` preview mode, `--model-name` override, `--auth` method selection, clear console output, long-running operation polling for both getDefinition and updateDefinition.
- **Key research findings**:
  - Fabric semantic model definitions support a `Copilot/` folder structure alongside the TMDL `definition/` folder
  - Q&A is being deprecated (Dec 2026) in favor of Copilot — the Copilot folder is the forward-looking approach
  - "Prep for AI" features (AI instructions, AI data schema, synonyms) save to the LSDL internally but are represented as Copilot/ folder files in the REST API definition format
  - `definition.pbism` has a `qnaEnabled` setting that must be true for Q&A/Copilot features
  - The AI instructions also include synonym guidance as a belt-and-suspenders approach — Copilot uses these to interpret natural language even if the formal linguistic schema isn't fully consumed
- **TMDL lesson**: Console encoding on Windows (cp1252) can't handle Unicode box-drawing/emoji characters — always set `sys.stdout` encoding to UTF-8 at script start

### Semantic Model Credential Binding (April 2026)
- **Problem**: After deploying semantic model via Fabric REST API (TMDL), data sources have no credentials bound. Refresh fails with "default data connection without explicit connection credentials" error.
- **Root cause**: TMDL deployment creates M partition expressions with `Sql.Database()` calls but doesn't associate any authentication credentials with those data sources.
- **Solution**: Created `scripts/bind-model-credentials.py` — standalone script that:
  1. Finds the semantic model by name via Fabric REST API
  2. Calls Power BI REST API `Default.TakeOver` to bind current user's OAuth2 credentials
  3. Discovers gateway/datasource IDs and patches each with OAuth2 credential type
  4. Triggers a refresh and polls for completion
- **Two API scopes required**: Fabric API (`api.fabric.microsoft.com/.default`) for listing models, Power BI API (`analysis.windows.net/powerbi/api/.default`) for dataset operations (takeover, datasources, refresh)
- **Updated `create-semantic-model.py`**: Added post-deploy hook that automatically runs takeover + credential bind + refresh after model creation. Uses module import with inline fallback.
- **Key API endpoints**:
  - `POST /v1.0/myorg/datasets/{id}/Default.TakeOver` — binds current user as data source owner
  - `GET /v1.0/myorg/datasets/{id}/datasources` — returns gateway/datasource IDs
  - `PATCH /v1.0/myorg/gateways/{gw}/datasources/{ds}` — sets OAuth2 credentials
  - `POST /v1.0/myorg/datasets/{id}/refreshes` — triggers refresh
- **Lesson learned**: Fabric semantic models deployed via REST API always need a separate credential-binding step. The `TakeOver` endpoint is the simplest path — it binds the calling user's OAuth2 token to all data sources in one call.
- **Orchestration log:** `.squad/orchestration-log/2026-04-24T17-56-UTC-livingston.md`
- **Status:** Complete — credentials binding pattern integrated into Phase 2 deployment automation
