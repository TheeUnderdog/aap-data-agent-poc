# PostgreSQL → Fabric Mirroring & Schema Fitting Guide

**Purpose:** Step-by-step technical instructions for mirroring AAP's PostgreSQL loyalty database into Microsoft Fabric and fitting the existing Data Agent solution to the real schema.

**Status:** Pre-customer handoff. The current solution runs on synthetic data. When the customer provides PostgreSQL access, follow this guide to connect real data.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Azure PostgreSQL | Customer-provided connection string (host, port, database, credentials) |
| Fabric Workspace | Already provisioned — workspace ID: `82f53636-206f-4825-821b-bdaa8e089893` |
| Fabric Capacity | F64 or higher (mirroring requires Premium/Fabric capacity) |
| Network Access | PostgreSQL must be reachable from Fabric — may require Private Endpoint or firewall rules |
| Entra ID | User with Fabric workspace Admin or Member role |

---

## Part 1: Set Up Fabric Mirroring from PostgreSQL

### Step 1: Enable Mirroring on the PostgreSQL Source

Fabric Mirroring from Azure PostgreSQL requires **logical replication** enabled on the source database.

1. **Verify server parameter** — In Azure Portal → PostgreSQL Flexible Server → Server Parameters:
   ```
   wal_level = logical
   ```
   If this requires a restart, coordinate with the customer's DBA.

2. **Create a replication user** (or use an existing one with sufficient privileges):
   ```sql
   CREATE ROLE fabric_mirror WITH LOGIN PASSWORD '<secure-password>' REPLICATION;
   GRANT CONNECT ON DATABASE loyalty_db TO fabric_mirror;
   GRANT USAGE ON SCHEMA public TO fabric_mirror;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO fabric_mirror;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fabric_mirror;
   ```

3. **Network access** — Ensure the PostgreSQL server allows connections from Fabric's IP ranges, or configure a Private Endpoint in the same VNet.

### Step 2: Create a Mirrored Database in Fabric

1. Open [Fabric Portal](https://msit.powerbi.com) → Navigate to the workspace.
2. Click **+ New item** → **Mirrored Database** → **Azure Database for PostgreSQL**.
3. Enter connection details:
   - **Server:** `<customer-provided-host>.postgres.database.azure.com`
   - **Port:** `5432`
   - **Database:** `<loyalty_database_name>`
   - **Authentication:** Basic (username/password) or Entra ID if supported
4. **Select tables to mirror** — Select all tables in the loyalty schema. At minimum, we expect:
   - Transaction tables (purchases, returns, line items)
   - Member tables (profiles, tiers, enrollment)
   - Points tables (earn/redeem ledger)
   - Coupon tables (rules, issuance, redemption)
   - CSR/Agent tables
   - SKU/Product reference tables
5. Click **Mirror database** to start initial sync.

### Step 3: Verify Mirroring Status

1. In the workspace, open the Mirrored Database item.
2. Check the **Replication Status** tab — all tables should show "Running" after initial snapshot completes.
3. **Initial sync time** depends on data volume:
   - < 1M rows: minutes
   - 1-10M rows: 10-30 minutes
   - 10M+ rows: may take hours
4. Verify row counts match the source: click any table → Preview data.

### Step 4: Access Mirrored Data in the Lakehouse

Mirrored tables appear automatically in the workspace's default Lakehouse SQL Analytics Endpoint. Verify:

1. Open the **SQL Analytics Endpoint** for the mirrored database.
2. Run: `SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo';`
3. Confirm all expected tables are present.

> **Note:** Mirrored tables are read-only Delta tables in OneLake. They update continuously as changes flow from PostgreSQL.

---

## Part 2: Fit the Solution to the Real Schema

### Overview: What Needs to Change

The solution is designed for schema independence. All components query through a **semantic view layer**, never raw tables. When the real schema arrives, the changes are isolated to:

| Component | What Changes | Effort |
|-----------|-------------|--------|
| Semantic Views | `scripts/create-semantic-views.sql` — remap SELECT statements | Medium |
| Semantic Model | TMDL table definitions — point at new table/column names | Medium |
| Data Agent Instructions | `agents/*/instructions.md` — update example queries | Low |
| Linguistic Schema | `scripts/configure-linguistic-schema.py` — update synonyms | Low |
| Web App / API | **Nothing** — queries through views | None |

### Step 5: Map Real Tables to Contract Views

The contract views are the stable interface. Map the customer's actual tables to them:

| Contract View | Purpose | Map From (Customer Tables) |
|---------------|---------|---------------------------|
| `semantic.v_member_summary` | Member profile + tier + points balance | Member table(s) + points table(s) |
| `semantic.v_transaction_history` | Enriched purchase/return history | Transaction + line item tables |
| `semantic.v_points_activity` | Points earned/redeemed timeline | Points ledger table |
| `semantic.v_reward_catalog` | Available rewards + redemption stats | Coupon rules / rewards tables |
| `semantic.v_store_performance` | Store-level aggregates | Transaction + store tables |
| `semantic.v_campaign_effectiveness` | Campaign ROI and engagement | Campaign / coupon tables |
| `semantic.v_product_popularity` | Product sales by category | Transaction items + SKU tables |

**Process:**

1. Get the real schema DDL from the mirrored database:
   ```sql
   SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
   FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = 'dbo'
   ORDER BY TABLE_NAME, ORDINAL_POSITION;
   ```

2. Compare against the POC schema documented in `docs/data-schema.md` § 3.

3. Create a column mapping spreadsheet:
   ```
   POC Column              → Real Column
   loyalty_members.tier    → <real_table>.<real_column>
   transactions.total      → <real_table>.<real_column>
   ...
   ```

4. If the customer's schema uses a different naming convention (e.g., `TXN_DETAIL` instead of `transactions`), that's fine — the views abstract it away.

### Step 6: Rewrite the Semantic Views

Edit `scripts/create-semantic-views.sql` to point at the real tables.

**Example — before (POC):**
```sql
CREATE OR ALTER VIEW semantic.v_member_summary AS
SELECT
    m.member_id,
    m.first_name,
    m.last_name,
    m.tier,
    ...
FROM dbo.loyalty_members m
LEFT JOIN dbo.member_points mp ON m.member_id = mp.member_id
```

**Example — after (real schema, hypothetical):**
```sql
CREATE OR ALTER VIEW semantic.v_member_summary AS
SELECT
    m.MEMBER_KEY AS member_id,
    m.FIRST_NM AS first_name,
    m.LAST_NM AS last_name,
    t.TIER_NM AS tier,
    ...
FROM dbo.LYL_MEMBER m
LEFT JOIN dbo.MBR_TIER t ON m.MEMBER_KEY = t.MEMBER_KEY
LEFT JOIN dbo.MBR_POINTS_BALANCE pb ON m.MEMBER_KEY = pb.MEMBER_KEY
```

**Key rules:**
- View output columns stay the same (these are the contract)
- Only the FROM/JOIN/WHERE clauses change
- Use COALESCE for nullable columns to match expected behavior
- If a contract field doesn't exist in the real schema, use NULL with an alias

### Step 7: Deploy Updated Views

```bash
# From the repo root
python scripts/deploy-views.py
```

Or manually in the SQL Analytics Endpoint — paste the updated `create-semantic-views.sql` and execute.

**Verify:**
```sql
SELECT TOP 10 * FROM semantic.v_member_summary;
SELECT TOP 10 * FROM semantic.v_transaction_history;
-- etc. for each view
```

### Step 8: Update the Semantic Model

The Power BI semantic model (TMDL in `scripts/`) defines tables, relationships, and DAX measures.

1. **Update table sources** — Each model table points at a Lakehouse table or view. Update to reference the contract views or the real mirrored tables (depending on whether the model queries views or tables directly).

2. **Update relationships** — If foreign key column names changed, update the relationship definitions.

3. **Verify DAX measures still work** — Run `scripts/create-semantic-model.py` or manually refresh in Power BI Desktop.

4. **Redeploy** via git sync (the model is committed to this repo under `scripts/`).

### Step 9: Update Linguistic Schema

The linguistic schema maps natural language terms to model entities. Update if:
- Table names changed (synonyms still point at old names)
- New columns or concepts were added
- Domain terminology differs from what we assumed

```bash
python scripts/configure-linguistic-schema.py
```

Review the synonym mappings in that script and adjust for the customer's actual terminology.

### Step 10: Update Data Agent Instructions (If Needed)

Each Fabric Data Agent has instruction files in `agents/*/`:

| Agent | Domain | Update if... |
|-------|--------|-------------|
| `loyalty-program-manager` | Members, tiers, points, churn | Member/points table structure differs |
| `store-operations` | Stores, revenue, channels | Store data is structured differently |
| `merchandising` | Products, categories, SKUs | Product catalog schema differs |
| `marketing-promotions` | Campaigns, coupons, redemption | Campaign/coupon model differs significantly |
| `customer-service` | CSR activities, member support | CSR/audit table structure differs |

**What to update in instruction files:**
- Sample queries that reference specific column names
- Verified answers in `verified-answers-*.json` — these may need regeneration
- Business rules that reference specific field values (e.g., tier names)

**What NOT to change:**
- Agent persona and tone
- Response format rules
- General business context

---

## Part 3: Handling Agents Without Matching Data

Some agents cover data subjects that may not exist in the customer's real schema. **Leave them in place.**

| Scenario | Action |
|----------|--------|
| Agent's data subject exists in real schema | Remap views and instructions (Steps 5-10) |
| Agent's data subject partially exists | Remap what's available, note gaps in instructions |
| Agent's data subject doesn't exist at all | Leave agent configured — it simply won't return results for those queries |
| Agent covers a data subject the customer adds later | Already ready — just remap the views when data arrives |

**Why not remove agents:**
- The web app UI accommodates them gracefully (tabs remain, agent responds with "no data available")
- If the customer adds that data domain later, the agent is ready
- The prototype demonstrates the *capability* even if real data isn't connected yet

**For the demo/handoff:** Brief the customer that some agents query synthetic data domains that will light up when their full data is connected.

---

## Part 4: Validation Checklist

After completing the schema fitting:

- [ ] All mirrored tables show "Running" replication status
- [ ] Each semantic view returns data without errors
- [ ] Row counts are reasonable (compare to source)
- [ ] Semantic model refreshes successfully in Fabric
- [ ] Each Data Agent answers a basic query correctly via the web app
- [ ] Points and transaction totals are internally consistent
- [ ] No PII leakage in agent responses (verify data access scope)

---

## Part 5: What We Know About the Customer's Data

> **Current status:** We have a preliminary screenshot of the customer's database schema. This is NOT a full DDL or data dictionary.

**What the screenshot showed:**
- Confirms the 8 table groups documented in `docs/production-schema-migration.md`
- Source systems: POS, Ecomm, Sterling (OMS), Customer First, CrowdTwist, GK Coupon Management
- Data domains: Transactions, Members, Points, Coupons, Audit/Fraud, Agents, SKUs, Campaigns

**What we still need from AAP:**
1. Full table DDL (column names, types, constraints)
2. PostgreSQL connection credentials (host, port, database, user)
3. Network access (IP allowlist or Private Endpoint coordination)
4. Sample data walkthrough (confirm our column mapping assumptions)
5. Business rules clarification (tier thresholds, points multipliers, coupon logic)
6. Data volume estimates (for capacity planning)

**Risk:** Our POC schema was built from domain knowledge and the preliminary screenshot. Some column names and relationships will differ. The semantic view layer isolates this risk — worst case is view SQL rewrites, not application changes.

---

## Quick Reference: File Locations

| File | Purpose |
|------|---------|
| `scripts/create-semantic-views.sql` | Contract view definitions (edit these for real schema) |
| `scripts/configure-linguistic-schema.py` | NL synonym mappings |
| `scripts/create-semantic-model.py` | Semantic model deployment |
| `agents/*/instructions.md` | Per-agent instruction files |
| `agents/*/verified-answers-*.json` | Pre-validated Q&A pairs |
| `docs/data-schema.md` | Full POC schema documentation |
| `docs/production-schema-migration.md` | POC vs. real schema analysis |
| `notebooks/01-create-sample-data.py` | Sample data generator (POC only) |
