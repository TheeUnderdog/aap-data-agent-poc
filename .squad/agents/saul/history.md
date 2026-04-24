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

