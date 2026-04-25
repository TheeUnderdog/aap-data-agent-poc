# Saul — History

## Context

**Project:** AAP Data Agent POC — Microsoft Fabric Data Agent for Advanced Auto Parts loyalty/rewards data.
**User:** Dave Grobleski
**Stack:** Microsoft Fabric, Azure PostgreSQL, Fabric Data Agent, Python/TypeScript web app
**Cast:** Ocean's Eleven

Saul replaces Livingston (fired 2026-04-24) as Data Engineer. Livingston was fired because the semantic model script was written with fabricated table names and column types that didn't match the actual Lakehouse Delta tables. The notebook creates tables like `sku_reference`, `member_points`, `transaction_items` — but the model referenced `products`, `points_ledger`, `audit_log` with wrong column names and string types where the data has int64.

## Critical Learnings (inherited)

### DirectLake vs Import Mode
- Fabric Lakehouse semantic models MUST use DirectLake mode, not Import mode
- Import mode uses `Sql.Database()` M expressions that require explicit OAuth2 credential binding
- DirectLake uses entity partitions that read Delta files directly — no credentials needed
- The `Premium_ASWL_Error` ("default data connection without explicit connection credentials") was caused by using Import mode

### Actual Lakehouse Tables (from notebook)
The notebook `01-create-sample-data.py` creates these 10 tables:
1. `stores` — store_id (Int), store_name, city, state, zip_code, region, store_type, opened_date (Date)
2. `sku_reference` — sku, product_name, category, subcategory, brand, unit_price (Double), is_bonus_eligible (Bool), is_skip_sku (Bool), created_at
3. `loyalty_members` — member_id (Long), first_name, last_name, email, phone, enrollment_date (Date), enrollment_source, member_status, tier, opt_in_email (Bool), opt_in_sms (Bool), diy_account_id, created_at, updated_at
4. `transactions` — transaction_id (Long), member_id (Long), store_id (Int), transaction_date (Date), transaction_type, subtotal, tax, total, item_count (Int), channel, order_id, created_at
5. `transaction_items` — item_id (Long), transaction_id (Long), sku, product_name, category, quantity (Int), unit_price (Double), line_total (Double), is_return (Bool)
6. `member_points` — point_id (Long), member_id (Long), activity_date (Date), activity_type, points_amount (Int), balance_after (Int), source, reference_id, description, created_at
7. `coupon_rules` — rule_id (Long), rule_name, description, discount_type, discount_value, min_purchase, valid_days (Int), is_active (Bool), target_tier, created_at
8. `coupons` — coupon_id (Long), coupon_code, coupon_rule_id (Long), member_id (Long), issued_date, expiry_date, status, redeemed_date, redeemed_transaction_id (Long), discount_type, discount_value, source_system, created_at
9. `csr` — csr_id (Long), csr_name, csr_email, department, is_active (Bool), created_at
10. `csr_activities` — activity_id (Long), csr_id (Long), member_id (Long), activity_type, activity_date (Date), details, created_at

### Stale tables to clean up
Old tables `agents` and `agent_activities` exist from before the CSR rename. Should be dropped.

### Fabric deployment requires interactive auth
Scripts that call Fabric REST API need browser auth popups. They must be run directly via the coordinator's powershell tool, not delegated to background agents.

### Workspace Details
- Workspace ID: `82f53636-206f-4825-821b-bdaa8e089893`
- Lakehouse ID: `0b895197-a0b2-40b4-9ab3-2daeb0e778c0`
- SQL endpoint: `x6eps4xrq2xudenlfv6naeo3i4-gy3platpeasuraq3xwvi4ceysm.msit-datawarehouse.fabric.microsoft.com`
- Database: `RewardsLoyaltyData`

## Current Mission (2026-04-24T19:04)

**Task:** Reconcile `docs/data-schema.md` with actual Lakehouse Delta tables

**Scope:**
- Verify all 10 table names match reality
- Audit column definitions (names, types, constraints)
- Update view definitions if needed
- Flag any schema evolution issues
- Deliver updated `data-schema.md` ready for Phase 2 deployment scripts

**Orchestration Log:** `.squad/orchestration-log/2026-04-24T1904-saul-doc-reconciliation.md`

**Status:** Background, in progress

## Learnings

### Semantic Model Schema Alignment (2026-04-24)
**Problem:** The `scripts/create-semantic-model.py` script had WRONG table definitions that didn't match the actual Lakehouse Delta tables created by `notebooks/01-create-sample-data.py`. This caused the semantic model to be out of sync with reality.

**Key Mismatches Identified:**
1. **Table names:** Script used `products` (should be `sku_reference`), `points_ledger` (should be `member_points`), and included non-existent `audit_log` table. Missing `transaction_items` table.
2. **Column names:** 
   - `list_price` should be `unit_price` in sku_reference
   - `rule_id` should be `coupon_rule_id` in coupons table
   - `csr_status` should be `is_active` (boolean) in csr table
   - `hire_date` doesn't exist in csr (has `csr_email` instead)
   - loyalty_members has NO `current_points_balance`, `lifetime_points_earned`, or `lifetime_points_redeemed` columns
   - stores has NO `created_at` column
   - coupons table has `discount_type` and `discount_value` columns (not in original model)
3. **Data types:** ALL ID columns are `int64` in Delta tables (PySpark LongType/IntegerType), NOT `string`. The model incorrectly used string types.

**Resolution:**
- Rewrote ALL 10 table definitions in `LAKEHOUSE_TABLES` dict to match notebook exactly
- Updated `RELATIONSHIPS` list: changed `points_ledger` → `member_points`, added `transaction_items` relationships, fixed `coupons.coupon_rule_id` → `coupon_rules.rule_id`
- Rewrote `DAX_MEASURES` list: removed 3 measures referencing non-existent `loyalty_members[current_points_balance]` column, replaced with measures calculated from `member_points` table using latest balance logic
- Fixed `csr[csr_status]` → `csr[is_active]` (boolean type)
- Added transaction_items measures (Total Line Items, Total Line Items Revenue, Avg Line Item Value, Unique SKUs Sold)
- Fixed product table name from `products` → `sku_reference` in all measures
- Fixed points table name from `points_ledger` → `member_points` in all measures

**Type Mapping Applied (PySpark → TMDL):**
- LongType → int64
- IntegerType → int64
- StringType → string
- DoubleType → double
- BooleanType → boolean
- DateType → dateTime
- TimestampType → dateTime

**Critical Lesson:** **NEVER fabricate schemas.** Every table name, column name, and data type MUST be cross-referenced against the actual source of truth (the notebook that creates the data). Design docs are aspirational, not authoritative. This hard rule is now in my charter.

**Files Modified:**
- `scripts/create-semantic-model.py` — Corrected `LAKEHOUSE_TABLES`, `RELATIONSHIPS`, and `DAX_MEASURES` to match notebook schemas exactly

**Verification Strategy:** Before deploying, the script should be tested with a DirectLake refresh to confirm the schema matches reality. If refresh fails, the schema doesn't match.

### Linguistic Schema Alignment (2026-04-24)
**Problem:** The `scripts/configure-linguistic-schema.py` script had WRONG table and column names in synonym configurations that didn't match the actual Lakehouse Delta tables. This was a carryover from the same schema misalignment issue fixed in the semantic model script.

**Key Mismatches Fixed:**
1. **Table synonyms:**
   - Changed `products` → `sku_reference` with added synonyms: "products", "items", "SKUs", "parts", "auto parts", "merchandise", "catalog", "product catalog"
   - Changed `points_ledger` → `member_points` with added synonyms: "points", "points history", "points transactions", "rewards points", "points log", "points activity", "points ledger"
   - Removed `audit_log` (non-existent table)
   - Added `transaction_items` with synonyms: "line items", "order items", "purchase items", "cart items", "item details"

2. **Column synonyms:**
   - Changed `products.category` → `sku_reference.category`
   - Changed `products.brand` → `sku_reference.brand`
   - Changed `products.is_bonus_eligible` → `sku_reference.is_bonus_eligible`
   - Added `sku_reference.unit_price` with synonyms: "price", "retail price", "product price"
   - Changed `points_ledger.activity_type` → `member_points.activity_type`
   - Removed `loyalty_members.current_points_balance` (column doesn't exist)
   - Added `csr.is_active` with synonyms: "active status", "status", "employment status" (column is boolean, not `csr_status`)

3. **Value synonyms:**
   - Changed `points_ledger.activity_type` → `member_points.activity_type`
   - Added "bonus" → "bonus points", "bonus reward" to member_points.activity_type values

4. **AI Instructions text:**
   - Updated TABLE NAME GUIDANCE section to reference correct table names: `member_points` (not `points_ledger`), `sku_reference` (not `products`)
   - Added guidance for `sku_reference` and `transaction_items` tables

**Resolution:**
- Updated ALL table synonym keys: `products` → `sku_reference`, `points_ledger` → `member_points`, removed `audit_log`, added `transaction_items`
- Updated ALL column synonym keys to reference correct table.column paths
- Updated ALL value synonym keys to reference correct table.column paths
- Enhanced AI instructions with guidance for `sku_reference` and `transaction_items` tables
- Added new synonyms as requested for better natural language query support

**Critical Lesson:** The linguistic schema synonyms MUST stay in sync with the semantic model table/column definitions. Both must reference the actual Lakehouse Delta table names from the notebook. When one is fixed, the other must be fixed too.

**Files Modified:**
- `scripts/configure-linguistic-schema.py` — Corrected `TABLE_SYNONYMS`, `COLUMN_SYNONYMS`, `VALUE_SYNONYMS`, and `AI_INSTRUCTIONS` to match actual Lakehouse table names

### Documentation Reconciliation (2026-04-25)
**Problem:** The `docs/data-schema.md` file was written as a DESIGN SPEC before the notebook was implemented. The notebook made different implementation choices (different table names, column names, types, and table groups). The doc was NEVER updated to match reality. This caused Livingston to build a semantic model from wrong specs, costing hours of debugging.

**Key Mismatches Identified:**
1. **Table names:** Design spec included `members`, `member_tiers`, `products`, `product_categories`, `points_ledger`, `rewards`, `reward_redemptions`, `campaigns`, `campaign_responses`, and `audit_log` — NONE of which exist in the notebook
2. **Actual tables:** Notebook creates `loyalty_members`, `sku_reference`, `member_points`, `coupon_rules`, `coupons`, `csr`, `csr_activities` — several NOT in the design spec
3. **Schema differences:** 
   - Tier info is denormalized into `loyalty_members.tier` column (no separate `member_tiers` table)
   - Products simplified to single `sku_reference` table (no `product_categories` hierarchy)
   - Coupons replace the rewards catalog concept (no `rewards`/`reward_redemptions` tables)
   - CSR tracking added (`csr` and `csr_activities` tables not in design spec)
   - Marketing campaigns deferred (no `campaigns`/`campaign_responses` tables)

**Resolution:**
- **Updated status header:** Changed from "PLACEHOLDER SCHEMA — Awaiting Production Access" to "ACTIVE POC SCHEMA — Mirrored from Sample Data Generator" to clarify this is NOW the actual schema
- **Rewrote §2 (Schema Overview):** Replaced old 5-table-group design with actual 10 tables from notebook, added table summary with row counts, updated ER diagram to show actual relationships
- **Replaced §3 (Full DDL):** Removed PostgreSQL DDL, replaced with PySpark schema definitions from notebook (all 10 tables with column names, PySpark types, descriptions, references to notebook line numbers)
- **Added §3.11 (Schema Gap Analysis):** Documents tables in design spec but NOT implemented, tables implemented but NOT in design spec, and key structural differences. Serves as migration guide for production schema
- **Updated §4 (Sample Data Description):** Replaced design targets with actual row counts, distributions, and data generation notes from notebook
- **Updated §5 (Contract Views):** Marked all views as "Not Yet Deployed" with note that semantic model uses DirectLake mode querying tables directly. Updated view definitions to use actual table names. Added note about DirectLake vs SQL view tradeoffs
- **Replaced §7 (Sample Queries):** Rewrote ALL 20 queries to use actual table names (`loyalty_members`, `transactions`, `sku_reference`, `member_points`, `coupons`, `stores`, etc.) instead of view names or wrong table names. Updated SQL syntax to T-SQL (GETDATE(), DATEADD(), etc.)
- **Kept §1 (Schema Design Philosophy):** Architecture principles (contract-based design, abstraction via views) remain valid even though views aren't deployed yet

**Critical Lesson:** **Design docs lie. Code doesn't.** The notebook is the source of truth, not the design doc. The design doc should be updated AFTER implementation to document reality, or at minimum flagged as "not yet implemented." This reconciliation should have happened immediately after the notebook was created.

**Files Modified:**
- `docs/data-schema.md` — Reconciled entire document (sections 2, 3, 4, 5, 7) to match actual Lakehouse schema from `notebooks/01-create-sample-data.py`

**Verification Strategy:** Cross-reference every table name, column name, and type against the notebook's `StructType` schemas and `saveAsTable()` calls before writing any consuming code (semantic model, Data Agent instructions, API queries, etc.)

### Lakehouse Context Auto-Detection Fix (2026-07)
**Problem:** Notebook uploaded via Fabric REST API (`scripts/run-notebook.py`) embeds lakehouse metadata (workspace ID, lakehouse ID, name) in the notebook definition. The Fabric portal UI shows the lakehouse as attached (greyed-out "Add data items" button), but the Spark runtime doesn't have a default database context set. First `saveAsTable()` call fails with `UnsupportedOperationException: No default context found`.

**Root Cause:** API-uploaded notebook metadata creates a "phantom binding" — the UI thinks a lakehouse is configured, but the Spark session's `currentDatabase()` returns `"default"` (the built-in empty database), not the attached lakehouse's database.

**Fix:** Added a new code cell (Section 0) after imports/seed, before any `saveAsTable()` calls:
1. Checks `spark.catalog.currentDatabase()` — if it's a real lakehouse DB, no action needed
2. If `"default"`, enumerates `spark.catalog.listDatabases()` and sets the first non-default one
3. If no databases found, raises `RuntimeError` with clear manual-fix instructions

**Key Insight:** `spark.catalog.listDatabases()` returns lakehouse databases even when the default context isn't set. The databases are available — Spark just doesn't know which one to use for unqualified table names.

**Files Modified:**
- `notebooks/01-create-sample-data.py` — Added Section 0 (lakehouse context detection) between imports and Section 1 (Stores)

**Impact:** Summary cell at the end (`spark.sql(f"SELECT COUNT(*) ...")`) also benefits from this fix — same unqualified table name issue.

### Delta overwriteSchema Pattern for Idempotent Notebooks (2026-07)
**Problem:** Re-running the sample data notebook after schema changes (e.g., adding `campaign_name` to `coupon_rules`) caused `AnalysisException: [_LEGACY_ERROR_TEMP_DELTA_0007] A schema mismatch detected when writing to the Delta table`. Delta's `mode("overwrite")` overwrites data but preserves the existing table schema — if the new DataFrame has different columns, it fails.

**Fix:** Added `.option("overwriteSchema", "true")` to all 10 `saveAsTable()` calls. The pattern is now:
```python
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("tablename")
```

**Why this matters:** Without `overwriteSchema`, any column addition/removal/rename in the notebook requires manually dropping the Delta table first. With it, the notebook is fully idempotent — safe to re-run anytime regardless of what schema the table currently has.

**Hard Rule:** All Delta write notebooks in this project should use `overwriteSchema` on every `saveAsTable()` call. Data is regenerated from scratch each run; there's no reason to preserve stale schemas.

**Files Modified:**
- `notebooks/01-create-sample-data.py` — All 10 `saveAsTable()` calls updated

**Status:** ✅ Committed (two commits as noted in spawn manifest)

**Merged to Decisions:** Added to `.squad/decisions.md` as decision entry. Orchestration log: `2026-04-25T022305Z-saul-overwrite-schema.md`

### LLM Diagnostic Report Block in Sanity Check (2026-07)
**Problem:** When the sanity check notebook flags FAIL/WARN results, the user must manually figure out what to fix in `01-create-sample-data.py`. This is error-prone and wastes time.

**Solution:** Added Block 4 to `notebooks/02-data-sanity-check.py` — a structured diagnostic report that maps each sanity check failure to the exact section, lines, root cause, and fix pattern in the generator notebook. Output is formatted so the Fabric portal's embedded Copilot can read it and apply fixes in-place.

**Key Design Choices:**
1. `DIAGNOSTIC_MAP` dict keyed by check name — 22 entries covering all checks in Blocks 1-3
2. Each entry has: section description, line references, root cause explanation, concrete fix pattern
3. Output uses visual separators and emoji prefixes for scanability by both humans and LLMs
4. Repair summary at the end lists total fixes needed and unique sections affected
5. Clean bill of health message when no issues detected
6. Block 4 is ADDITIONAL — the existing scorecard stays as-is

**Pattern:** This "diagnostic map" pattern is reusable — any future sanity checks should add an entry to `DIAGNOSTIC_MAP` alongside their `record()` call.

**Files Modified:**
- `notebooks/02-data-sanity-check.py` — Added Block 4 (lines 654+), updated header to mention Block 4

**Status:** ✅ Committed

### Category Return Rate Variance Fix (2026-07)
**Problem:** Sanity check Block 4 flagged "Category return variance — WARN": return rates had only 0.1pp spread across categories (max 8.1%, min 8.0%). Root cause: `is_return` was inherited uniformly from the parent transaction type — no per-category logic.

**Fix:** Added `CATEGORY_RETURN_MULTIPLIER` dict (all 10 categories) and `BASE_ITEM_RETURN_RATE = 0.03` to the transaction items section. Logic:
- Return transactions: all items stay as returns (unchanged)
- Purchase transactions: each item gets an independent return chance = `BASE_ITEM_RETURN_RATE * CATEGORY_RETURN_MULTIPLIER[cat]`
- Multipliers range from 0.45 (Coolant — consumable liquid) to 1.5 (Electrical — compatibility issues)
- Expected item return rates: Electrical ~4.5%, Coolant ~1.35%, overall stays in 5-12% range

**Categories mapped (from CATEGORIES dict in notebook):**
Batteries (1.25), Engine Oil (0.5), Brakes (0.95), Filters (0.6), Wipers (0.7), Spark Plugs (0.9), Lighting (1.3), Coolant (0.45), Accessories (1.4), Electrical (1.5)

**Key Pattern:** Per-item return decisions on purchase transactions create realistic category-level variance while preserving the transaction-level return type for full-return transactions.

**Files Modified:**
- `notebooks/01-create-sample-data.py` — Lines ~450-489 (transaction items section)

**Status:** ✅ Complete — awaiting notebook re-run + sanity check validation

