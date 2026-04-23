# AAP Data Agent POC — Implementation Plan

**Version:** 1.0  
**Date:** April 2026  
**Project:** Advanced Auto Parts Data Agent Proof of Concept  
**Owner:** Danny (Lead/Architect)

---

## Executive Summary

This implementation plan provides a detailed, phased approach to deploying the AAP Data Agent POC. The plan is structured around four sequential phases that align with the technical architecture: (1) Fabric workspace setup, (2) PostgreSQL mirroring configuration, (3) Data Agent deployment, and (4) web application development. Each phase includes step-by-step tasks, prerequisites, validation criteria, and estimated timelines. A dedicated section outlines the schema swap procedure for transitioning from placeholder to production data.

**Total Estimated Timeline:** 3-4 weeks (assuming no blockers on AAP prerequisites)

---

## Phase 1: Fabric Workspace Setup

**Objective:** Provision and configure a Microsoft Fabric workspace with Lakehouse for mirrored data storage.

**Duration:** 3-5 days  
**Owner:** Data Platform Team / DevOps  
**Prerequisites:** 
- Access to AAP's Fabric tenant (Fabric Admin or Capacity Admin role)
- Decision on which existing Fabric capacity to use
- Naming conventions and resource tagging standards

### Tasks

#### 1.1 Workspace Provisioning

**Steps:**
1. Log into [Microsoft Fabric portal](https://app.fabric.microsoft.com)
2. Navigate to **Workspaces** → **New Workspace**
3. Configure workspace:
   - **Name:** `AAP-RewardsLoyalty-POC` (or per AAP naming convention)
   - **Description:** "Proof of concept for natural language data querying over rewards/loyalty data"
   - **License Mode:** Fabric Capacity (select from AAP's existing capacities)
   - **Capacity:** Choose non-production capacity in same region as Azure PostgreSQL
4. Set workspace admins:
   - Add DevOps/Platform team members
   - Add Danny (architect) for oversight
5. Create workspace → Verify creation successful

**Validation:**
- Workspace appears in workspace list
- Workspace settings show correct capacity assignment
- Admins can access workspace

**Estimated Time:** 30 minutes

#### 1.2 Lakehouse Creation

**Steps:**
1. Within workspace, click **New** → **Lakehouse**
2. Configure Lakehouse:
   - **Name:** `RewardsLoyaltyData`
   - **Description:** "Mirrored PostgreSQL data for rewards and loyalty program"
3. Create Lakehouse
4. Navigate to Lakehouse → **Settings** → **SQL endpoint**
5. Verify SQL endpoint is enabled (should be default)
6. Note SQL endpoint connection string (format: `<workspace>.datawarehouse.fabric.microsoft.com`)

**Validation:**
- Lakehouse visible in workspace items list
- SQL endpoint shows "Running" status
- Can connect to SQL endpoint via SQL Server Management Studio (SSMS) or Azure Data Studio
  - Connection: Use Azure Active Directory authentication
  - Database: `RewardsLoyaltyData`

**Estimated Time:** 1 hour (including SQL endpoint validation)

#### 1.3 Schema Creation in Lakehouse

**Steps:**
1. Connect to Lakehouse SQL endpoint (via SSMS, Azure Data Studio, or Fabric SQL editor)
2. Create schemas for data organization:

```sql
-- Create schema for mirrored tables
CREATE SCHEMA mirrored;
GO

-- Create schema for semantic views (contract layer)
CREATE SCHEMA semantic;
GO
```

3. Verify schema creation:

```sql
SELECT name FROM sys.schemas WHERE name IN ('mirrored', 'semantic');
```

**Validation:**
- Both schemas exist in Lakehouse
- Query returns two rows: `mirrored`, `semantic`

**Estimated Time:** 15 minutes

#### 1.4 Service Principal Setup

**Steps:**
1. Navigate to [Azure Portal](https://portal.azure.com) → **Entra ID** → **App registrations**
2. Click **New registration**:
   - **Name:** `AAP-DataAgent-ServicePrincipal`
   - **Supported account types:** Single tenant (AAP tenant only)
   - **Redirect URI:** (none for service principal)
3. Register → Note **Application (client) ID** and **Tenant ID**
4. Navigate to **Certificates & secrets** → **New client secret**:
   - **Description:** `Fabric access for Data Agent API`
   - **Expires:** 6 months (or per AAP policy)
   - Copy secret **Value** (only shown once)
5. Store credentials in Azure Key Vault (created in Phase 4):
   - For now, store securely in password manager or encrypted file

**Grant Service Principal Access to Fabric Workspace:**
1. Return to Fabric portal → Workspace → **Manage access**
2. Click **Add people or groups**
3. Search for `AAP-DataAgent-ServicePrincipal` (app name)
4. Assign role: **Contributor** (allows read/execute, not modify workspace settings)
5. Save

**Grant Service Principal Access to Lakehouse SQL Endpoint:**
1. Connect to Lakehouse SQL endpoint as admin
2. Grant read permission on `semantic` schema:

```sql
-- Create user for service principal
CREATE USER [AAP-DataAgent-ServicePrincipal] FROM EXTERNAL PROVIDER;
GO

-- Grant read access to semantic schema
GRANT SELECT ON SCHEMA::semantic TO [AAP-DataAgent-ServicePrincipal];
GO
```

**Validation:**
- Service principal appears in Fabric workspace access list
- Can acquire token for service principal using client ID + secret
- (Deferred validation: test in Phase 3 when Data Agent configured)

**Estimated Time:** 1 hour

#### 1.5 Workspace Configuration Documentation

**Steps:**
1. Create configuration document in source control: `config/fabric-workspace-config.json`

```json
{
  "workspace": {
    "name": "AAP-RewardsLoyalty-POC",
    "id": "<workspace-guid>",
    "capacityId": "<capacity-guid>",
    "region": "East US"
  },
  "lakehouse": {
    "name": "RewardsLoyaltyData",
    "sqlEndpoint": "<workspace>.datawarehouse.fabric.microsoft.com",
    "schemas": ["mirrored", "semantic"]
  },
  "servicePrincipal": {
    "clientId": "<client-id>",
    "displayName": "AAP-DataAgent-ServicePrincipal",
    "tenantId": "<tenant-id>"
  }
}
```

2. Document connection instructions for team: `docs/fabric-connection-guide.md`
3. Add to README any prerequisites for accessing workspace

**Validation:**
- Config file committed to Git
- Connection guide accessible to team members

**Estimated Time:** 30 minutes

### Phase 1 Deliverables

- [ ] Fabric workspace `AAP-RewardsLoyalty-POC` provisioned
- [ ] Lakehouse `RewardsLoyaltyData` with SQL endpoint enabled
- [ ] Schemas `mirrored` and `semantic` created
- [ ] Service principal created with Contributor role in workspace
- [ ] Configuration documented in `config/fabric-workspace-config.json`

### Phase 1 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Capacity at max CU utilization | Medium | High | Monitor capacity metrics before assignment; request additional capacity if needed |
| Service principal permissions insufficient | Medium | Medium | Test end-to-end in Phase 3; adjust permissions as needed |
| Network connectivity issues to SQL endpoint | Low | Medium | Validate from developer workstation and Azure Functions (Phase 4) |

---

## Phase 2: Data Mirroring

**Objective:** Configure Fabric Mirroring to replicate Azure PostgreSQL rewards/loyalty data into Lakehouse, deploy placeholder schema, and create semantic views.

**Duration:** 5-7 days  
**Owner:** Data Engineering Team + Livingston (Data Modeler)  
**Prerequisites:**
- Phase 1 complete (workspace and Lakehouse ready)
- Access to Azure PostgreSQL server (admin credentials)
- Network connectivity from Fabric to PostgreSQL (public endpoint or private link)
- PostgreSQL `wal_level` set to `logical` (required for CDC)

### Tasks

#### 2.1 PostgreSQL Prerequisites Validation

**Steps:**
1. **Verify PostgreSQL Version:**
   - Connect to PostgreSQL server (via psql, pgAdmin, or Azure Portal)
   - Run: `SELECT version();`
   - Confirm version ≥ 11 (required for logical replication)

2. **Enable Logical Replication:**
   - **Azure PostgreSQL Flexible Server:**
     - Navigate to server in Azure Portal → **Server parameters**
     - Set `wal_level` = `logical`
     - Set `max_replication_slots` = `10` (or higher if multiple mirroring jobs)
     - Set `max_wal_senders` = `10`
     - **Save** → Server will restart (downtime ~2-5 minutes)
   - **Azure PostgreSQL Single Server:**
     - Same parameters, may require support ticket for some settings

3. **Create Mirroring User (Optional but Recommended):**
   ```sql
   -- As PostgreSQL admin
   CREATE USER fabric_mirror WITH PASSWORD '<secure-password>';
   GRANT CONNECT ON DATABASE <rewards_db> TO fabric_mirror;
   GRANT USAGE ON SCHEMA public TO fabric_mirror;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO fabric_mirror;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fabric_mirror;
   
   -- Grant replication privilege
   ALTER USER fabric_mirror REPLICATION;
   ```

4. **Network Access:**
   - **If public endpoint:**
     - Azure Portal → PostgreSQL server → **Networking** → **Firewall rules**
     - Add rule to allow Fabric service IPs (see [Fabric networking docs](https://learn.microsoft.com/en-us/fabric/admin/service-ip-addresses))
     - Or allow all Azure services (less secure, but acceptable for POC)
   - **If private endpoint:**
     - Ensure private link configured
     - Verify Fabric can resolve private DNS
     - Test connectivity from Fabric workspace (use notebook with psycopg2)

**Validation:**
- `wal_level` = `logical` (run `SHOW wal_level;`)
- Mirroring user can connect and read tables
- Fabric can reach PostgreSQL endpoint (test in Fabric notebook):

```python
import psycopg2
conn = psycopg2.connect(
    host='<postgres-server>.postgres.database.azure.com',
    database='<db>',
    user='fabric_mirror',
    password='<password>'
)
cursor = conn.cursor()
cursor.execute('SELECT 1;')
print(cursor.fetchone())  # Should print (1,)
conn.close()
```

**Estimated Time:** 2-3 hours (including server restart)

#### 2.2 Placeholder Schema Deployment (PostgreSQL)

**Context:** Since AAP has not provided production schema, Livingston creates placeholder schema based on rewards/loyalty domain knowledge.

**Steps:**
1. **Review Placeholder Schema:** See `docs/data-schema.md` (created by Livingston)
   - Tables: `customers`, `transactions`, `rewards`, `redemptions`, `products`, `stores`
   - Relationships: Foreign keys defined
   - Sample data generation scripts

2. **Deploy Schema to PostgreSQL:**
   - Option A: If AAP has a dev/sandbox PostgreSQL instance, deploy there
   - Option B: Create new Azure PostgreSQL Flexible Server for POC (recommended to avoid impacting any existing systems)
     - Cost: ~$50-100/month for POC
     - Create server in Azure Portal → PostgreSQL flexible server
     - Configure firewall, enable logical replication (as in 2.1)

3. **Run Schema Creation Scripts:**
   ```bash
   # Assuming scripts in database/placeholder-schema/
   psql -h <server> -U <admin-user> -d <db> -f database/placeholder-schema/01-create-tables.sql
   psql -h <server> -U <admin-user> -d <db> -f database/placeholder-schema/02-create-indexes.sql
   psql -h <server> -U <admin-user> -d <db> -f database/placeholder-schema/03-insert-sample-data.sql
   ```

4. **Verify Data Load:**
   ```sql
   SELECT 'customers' AS table_name, COUNT(*) FROM customers
   UNION ALL
   SELECT 'transactions', COUNT(*) FROM transactions
   UNION ALL
   SELECT 'rewards', COUNT(*) FROM rewards;
   ```
   - Expected: ~100K customers, ~1M transactions, ~100K rewards records

**Validation:**
- All placeholder tables exist in PostgreSQL
- Sample data loaded (row counts match expectations)
- Foreign key relationships intact (`SELECT * FROM information_schema.table_constraints WHERE constraint_type = 'FOREIGN KEY';`)

**Estimated Time:** 2-4 hours (depending on data generation time)

#### 2.3 Configure Fabric Mirroring

**Steps:**
1. **Create Mirroring Connection:**
   - Fabric portal → Workspace → **New** → **Mirrored Database** → **Azure Database for PostgreSQL**
   - Configure connection:
     - **Connection name:** `AAP-PostgreSQL-RewardsLoyalty`
     - **Server:** `<server>.postgres.database.azure.com`
     - **Port:** 5432
     - **Database:** `<db-name>`
     - **Authentication:** SQL authentication (username: `fabric_mirror`, password: stored in Key Vault or entered directly)
     - **Encryption:** Require (SSL/TLS)
   - **Test connection** → Should succeed
   - Save connection

2. **Select Tables to Mirror:**
   - Fabric shows list of tables in PostgreSQL database
   - Select tables: `customers`, `transactions`, `rewards`, `redemptions`, `products`, `stores`
   - Deselect any system tables (e.g., `pg_*`)

3. **Configure Mirroring Destination:**
   - **Target Lakehouse:** `RewardsLoyaltyData`
   - **Target schema:** `mirrored` (create if not exists)
   - **Table name mapping:** Use source table names (e.g., `customers` → `mirrored.customers`)

4. **Start Mirroring:**
   - Review configuration
   - Click **Start mirroring**
   - Fabric begins initial snapshot (full table copy)

**Validation (Initial Snapshot):**
- Mirroring status shows "Running" in Fabric portal
- After 10-30 minutes (depending on data size), status shows "Active"
- Verify tables exist in Lakehouse:

```sql
-- Connect to Lakehouse SQL endpoint
SELECT TABLE_SCHEMA, TABLE_NAME, CREATE_DATE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'mirrored'
ORDER BY TABLE_NAME;
```

- Verify row counts match source:

```sql
SELECT 'customers' AS table_name, COUNT(*) FROM mirrored.customers
UNION ALL
SELECT 'transactions', COUNT(*) FROM mirrored.transactions
UNION ALL
SELECT 'rewards', COUNT(*) FROM mirrored.rewards;
```

**Validation (CDC - Change Data Capture):**
- Insert test row in PostgreSQL:
  ```sql
  INSERT INTO customers (customer_id, email, loyalty_tier, join_date)
  VALUES (999999, 'test@example.com', 'Bronze', CURRENT_DATE);
  ```
- Wait 1-2 minutes
- Check Lakehouse for new row:
  ```sql
  SELECT * FROM mirrored.customers WHERE customer_id = 999999;
  ```
- Should return the test row (confirms CDC working)

**Estimated Time:** 2-3 hours (including initial snapshot wait)

#### 2.4 Create Semantic Views (Contract Layer)

**Steps:**
1. **Review View Definitions:** See architecture doc section "Schema Abstraction Layer Design"
2. **Create Views in Lakehouse:**

```sql
-- Connect to Lakehouse SQL endpoint
USE RewardsLoyaltyData;
GO

-- View 1: Customer Profile
CREATE VIEW semantic.vw_CustomerProfile AS
SELECT
    customer_id AS CustomerID,
    email AS Email,
    first_name AS FirstName,
    last_name AS LastName,
    loyalty_tier AS LoyaltyTier,
    lifetime_points AS LifetimePoints,
    join_date AS JoinDate,
    last_purchase_date AS LastPurchaseDate
FROM mirrored.customers;
GO

-- View 2: Transaction History
CREATE VIEW semantic.vw_TransactionHistory AS
SELECT
    transaction_id AS TransactionID,
    customer_id AS CustomerID,
    transaction_date AS TransactionDate,
    store_id AS StoreID,
    total_amount AS TotalAmount,
    points_earned AS PointsEarned
FROM mirrored.transactions;
GO

-- View 3: Rewards Summary
CREATE VIEW semantic.vw_RewardsSummary AS
SELECT
    customer_id AS CustomerID,
    points_balance AS PointsBalance,
    points_earned_lifetime AS PointsEarnedLifetime,
    points_redeemed_lifetime AS PointsRedeemedLifetime,
    last_points_activity_date AS LastActivityDate
FROM mirrored.rewards;
GO

-- View 4: Redemption History
CREATE VIEW semantic.vw_RedemptionHistory AS
SELECT
    redemption_id AS RedemptionID,
    customer_id AS CustomerID,
    redemption_date AS RedemptionDate,
    points_redeemed AS PointsRedeemed,
    reward_description AS RewardDescription
FROM mirrored.redemptions;
GO

-- View 5: Store Locations
CREATE VIEW semantic.vw_StoreLocations AS
SELECT
    store_id AS StoreID,
    store_name AS StoreName,
    city AS City,
    state AS State,
    zip_code AS ZipCode,
    region AS Region
FROM mirrored.stores;
GO
```

3. **Document View Contracts:**
   - Create `docs/schema-contract.md` listing view names, column names, types, descriptions
   - Add to source control: `database/views/*.sql` (individual SQL files per view for maintainability)

4. **Test Views:**
   ```sql
   -- Verify views return data
   SELECT TOP 10 * FROM semantic.vw_CustomerProfile;
   SELECT TOP 10 * FROM semantic.vw_TransactionHistory;
   SELECT TOP 10 * FROM semantic.vw_RewardsSummary;
   
   -- Test join across views (Data Agent will do this)
   SELECT 
       cp.LoyaltyTier,
       COUNT(DISTINCT th.CustomerID) AS CustomerCount,
       AVG(th.TotalAmount) AS AvgTransactionAmount
   FROM semantic.vw_TransactionHistory th
   JOIN semantic.vw_CustomerProfile cp ON th.CustomerID = cp.CustomerID
   WHERE th.TransactionDate >= DATEADD(month, -1, GETDATE())
   GROUP BY cp.LoyaltyTier;
   ```

**Validation:**
- All views created successfully (no SQL errors)
- Views return expected data (sample queries execute)
- View definitions stored in source control

**Estimated Time:** 2 hours

#### 2.5 Data Quality Validation

**Steps:**
1. **Row Count Validation:**
   - Compare row counts between PostgreSQL source and Lakehouse mirrored tables
   - Verify 100% match (initial snapshot should be exact copy)

2. **Data Type Validation:**
   - Check that data types mapped correctly (e.g., PostgreSQL `integer` → SQL `int`, `timestamp` → `datetime2`)

3. **Null Handling:**
   - Verify NULLs preserved (sample rows with NULL values in source)

4. **Date Range Check:**
   - Verify transaction dates span expected range (e.g., last 2 years for placeholder data)

5. **Referential Integrity:**
   - Test joins across views (as in 2.4 test queries)
   - Verify foreign key relationships logically maintained (e.g., all `CustomerID` in transactions exist in customers)

**Validation Queries:**
```sql
-- Check for orphaned transactions (customer doesn't exist)
SELECT COUNT(*) AS OrphanedTransactions
FROM semantic.vw_TransactionHistory th
WHERE NOT EXISTS (
    SELECT 1 FROM semantic.vw_CustomerProfile cp WHERE cp.CustomerID = th.CustomerID
);
-- Should return 0

-- Check for invalid loyalty tiers
SELECT DISTINCT LoyaltyTier
FROM semantic.vw_CustomerProfile
WHERE LoyaltyTier NOT IN ('Bronze', 'Silver', 'Gold');
-- Should return 0 rows
```

**Estimated Time:** 1 hour

### Phase 2 Deliverables

- [ ] PostgreSQL source database configured with logical replication enabled
- [ ] Placeholder schema deployed to PostgreSQL with sample data
- [ ] Fabric Mirroring configured and actively syncing
- [ ] Mirrored tables in `mirrored` schema with validated row counts
- [ ] Semantic views in `semantic` schema (contract layer)
- [ ] View definitions documented and source-controlled
- [ ] Data quality validation passed

### Phase 2 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PostgreSQL logical replication not supported on current version | Low | High | Verify version before starting; upgrade if needed |
| Initial snapshot takes too long (>8 hours) | Medium | Medium | Use smaller sample data for POC; parallelize table mirroring if supported |
| CDC latency too high (>5 minutes) | Medium | Medium | Monitor mirroring metrics; adjust `wal_sender` parameters; escalate to Microsoft support |
| Schema mismatch between source and views | Medium | High | Automated tests for view queries; document contract in schema-contract.md |

---

## Phase 3: Fabric Data Agent

**Objective:** Create and configure a Fabric Data Agent to translate natural language queries into SQL against semantic views, and expose via REST API.

**Duration:** 3-4 days  
**Owner:** Data Engineering Team + Danny (Architect)  
**Prerequisites:**
- Phase 2 complete (mirrored data and semantic views ready)
- Sample query set from AAP marketing team (optional but highly recommended)
- Service principal configured (from Phase 1)

### Tasks

#### 3.1 Create Data Agent in Fabric

**Steps:**
1. **Navigate to Workspace:**
   - Fabric portal → Workspace `AAP-RewardsLoyalty-POC`

2. **Create Data Agent:**
   - Click **New** → **Data Agent** (or **More options** → **Data Agent**)
   - Configure agent:
     - **Name:** `RewardsLoyaltyAgent`
     - **Description:** "Natural language interface for AAP rewards and loyalty data"
     - **Data source:** Lakehouse `RewardsLoyaltyData`
     - **Schema scope:** Select `semantic` schema only (deselect `mirrored`)
   - Create agent

3. **Verify Agent Creation:**
   - Agent appears in workspace items list
   - Agent status: "Ready" or "Active"

**Validation:**
- Data Agent exists in workspace
- Can open agent configuration page

**Estimated Time:** 15 minutes

#### 3.2 Configure Data Agent Instructions

**Steps:**
1. **System Instructions (Grounding Prompt):**
   - Navigate to Data Agent → **Settings** → **Instructions**
   - Paste system prompt (see architecture doc, Phase 3 section):

```markdown
You are a data analyst assistant for Advanced Auto Parts' loyalty rewards program. 
You help marketing team members query customer, transaction, and rewards data using natural language.

Data Sources:
- vw_CustomerProfile: Customer demographics, loyalty tier (Bronze/Silver/Gold), lifetime points
- vw_TransactionHistory: Purchase records with date, amount, store location
- vw_RewardsSummary: Points balance and redemption history
- vw_RedemptionHistory: Reward redemption events
- vw_StoreLocations: Store locations and regions

Business Context:
- Loyalty tiers: Bronze (<$500 annual spend), Silver ($500-$1500), Gold (>$1500)
- Points: 1 point per dollar spent
- Geography: AAP operates stores across US, regional analysis common

Query Guidelines:
- Default to last 90 days for time-based queries if not specified
- Use LoyaltyTier filter for tier-specific analysis
- Aggregate by month or quarter for time series
- Protect customer privacy: never return raw email addresses or phone numbers
- When showing customer lists, use CustomerID only (not email)

Output Format:
- Provide clear, concise answers
- Include SQL query used (for transparency)
- Format numbers with appropriate units (e.g., $1,234.56 for currency, 1.2M for large counts)
```

2. **Save instructions**

**Validation:**
- Instructions saved successfully
- Can view instructions in agent settings

**Estimated Time:** 30 minutes

#### 3.3 Add Sample Queries for Training

**Steps:**
1. **Prepare Sample Query Set:**
   - If AAP provided sample queries, use those
   - Otherwise, use standard loyalty program queries (see architecture doc):

```json
[
  {
    "question": "How many customers are in each loyalty tier?",
    "notes": "Basic aggregation, tier breakdown"
  },
  {
    "question": "What is the average transaction amount in the last 30 days?",
    "notes": "Time filter, aggregation"
  },
  {
    "question": "Show me top 10 customers by lifetime points",
    "notes": "Sorting, limit, no PII"
  },
  {
    "question": "How many transactions were there last month by loyalty tier?",
    "notes": "Multi-table join, time filter, group by"
  },
  {
    "question": "What is the total points balance across all customers?",
    "notes": "Sum aggregation"
  },
  {
    "question": "Which stores had the most transactions in the last quarter?",
    "notes": "Store analysis, time filter, top N"
  },
  {
    "question": "How many gold tier customers joined in the last year?",
    "notes": "Tier filter, date filter, count"
  },
  {
    "question": "What is the average points earned per transaction by tier?",
    "notes": "Join, group by tier, average"
  },
  {
    "question": "Show me monthly transaction trends for the last 6 months",
    "notes": "Time series, monthly aggregation"
  },
  {
    "question": "How many customers have redeemed rewards in the last 90 days?",
    "notes": "Redemption table, date filter, distinct count"
  }
]
```

2. **Add Sample Queries to Agent:**
   - Data Agent → **Settings** → **Sample Queries** (or **Grounding**)
   - Add each question one at a time, OR
   - If bulk import supported, upload JSON file
   - For each sample, optionally provide expected SQL (if agent supports training mode):

```sql
-- Example for "How many customers are in each loyalty tier?"
SELECT LoyaltyTier, COUNT(*) AS CustomerCount
FROM semantic.vw_CustomerProfile
GROUP BY LoyaltyTier
ORDER BY CustomerCount DESC;
```

3. **Save sample queries**

**Validation:**
- Sample queries visible in agent configuration
- Agent can reference samples during query generation (implicit training)

**Estimated Time:** 1-2 hours (depending on number of samples and whether SQL provided)

#### 3.4 Test Data Agent with Sample Queries

**Steps:**
1. **Open Agent Test Interface:**
   - Data Agent → **Test** or **Chat** tab

2. **Run Sample Queries:**
   - Enter each sample question from 3.3
   - Verify agent returns:
     - ✅ Correct SQL query
     - ✅ Accurate results (row count, values)
     - ✅ Natural language answer

3. **Document Test Results:**
   - Create test log: `docs/data-agent-test-results.md`
   - For each query, log:
     - Question asked
     - SQL generated by agent
     - Results returned
     - ✅/❌ Pass/Fail (based on correctness)
     - Notes on any issues

**Example Test Case:**

| # | Question | Generated SQL | Result | Pass/Fail | Notes |
|---|----------|---------------|--------|-----------|-------|
| 1 | How many customers are in each loyalty tier? | `SELECT LoyaltyTier, COUNT(*) FROM semantic.vw_CustomerProfile GROUP BY LoyaltyTier` | Bronze: 60,000; Silver: 30,000; Gold: 10,000 | ✅ | Correct |
| 2 | What is the average transaction amount in the last 30 days? | `SELECT AVG(TotalAmount) FROM semantic.vw_TransactionHistory WHERE TransactionDate >= DATEADD(day, -30, GETDATE())` | $85.43 | ✅ | Correct |
| 3 | Show me customers with most lifetime points | `SELECT TOP 10 Email, LifetimePoints FROM semantic.vw_CustomerProfile ORDER BY LifetimePoints DESC` | (list of emails) | ❌ | Exposed PII (email), should use CustomerID only |

4. **Refine Instructions Based on Failures:**
   - If agent fails tests (wrong SQL, incorrect results), update system instructions
   - Example: Test 3 failed because agent returned `Email` instead of `CustomerID`
   - Update instructions: "When showing customer lists, use CustomerID only (not Email)"
   - Re-run failed tests

5. **Iterate Until 90%+ Pass Rate:**
   - Target: 9 out of 10 sample queries pass
   - If pass rate <90%, add more specific guidance in instructions or sample queries

**Validation:**
- Test results documented
- Pass rate ≥90% on sample queries
- Known failure cases documented (edge cases)

**Estimated Time:** 3-4 hours (including iterations)

#### 3.5 Configure Data Agent API Access

**Steps:**
1. **Retrieve Data Agent API Endpoint:**
   - Data Agent → **Settings** → **API** (or **Endpoint**)
   - Copy API endpoint URL (format: `https://api.fabric.microsoft.com/v1/workspaces/{workspace-id}/datascience/dataagents/{agent-id}/query`)
   - Note: Exact URL format may vary; check Fabric docs

2. **Test API with Service Principal:**
   - Use Postman, curl, or Python script to test API
   - Acquire token for service principal:

```bash
# Using Azure CLI
az login --service-principal \
  --username <client-id> \
  --password <client-secret> \
  --tenant <tenant-id>

# Acquire token for Fabric API
az account get-access-token --resource https://analysis.windows.net/powerbi/api
# Copy access_token from output
```

   - Send test query to Data Agent API:

```bash
curl -X POST "https://api.fabric.microsoft.com/v1/workspaces/{workspace-id}/datascience/dataagents/{agent-id}/query" \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many customers are in the gold loyalty tier?"
  }'
```

   - Verify response:

```json
{
  "answer": "There are 10,000 customers in the Gold loyalty tier.",
  "sql": "SELECT COUNT(*) FROM semantic.vw_CustomerProfile WHERE LoyaltyTier = 'Gold'",
  "results": [{"count": 10000}]
}
```

3. **Store API Configuration:**
   - Update `config/fabric-workspace-config.json`:

```json
{
  "dataAgent": {
    "name": "RewardsLoyaltyAgent",
    "id": "<agent-guid>",
    "apiEndpoint": "https://api.fabric.microsoft.com/v1/workspaces/{workspace-id}/datascience/dataagents/{agent-id}/query",
    "authentication": {
      "type": "ServicePrincipal",
      "clientId": "<client-id>",
      "scope": "https://analysis.windows.net/powerbi/api/.default"
    }
  }
}
```

**Validation:**
- Service principal can successfully call Data Agent API
- API returns expected responses for test queries
- API endpoint and auth config documented

**Estimated Time:** 1-2 hours

#### 3.6 Performance and Timeout Testing

**Steps:**
1. **Test Query Latency:**
   - Run 10 sample queries, measure response time
   - Target: <5 seconds for simple queries, <15 seconds for complex queries
   - Log results in test document

2. **Test Complex Queries:**
   - Ask intentionally complex questions:
     - "Show me monthly transaction trends by loyalty tier and store region for the last 12 months"
   - Verify query completes within timeout (default 30 seconds)
   - If timeout occurs frequently, optimize views (add indexes, materialized views)

3. **Test Concurrent Requests:**
   - Simulate multiple users querying simultaneously (5-10 concurrent requests)
   - Verify no rate limiting or errors
   - Check Fabric capacity metrics (CU utilization)

**Validation:**
- Average query latency <10 seconds
- No timeouts on reasonable queries
- Concurrent requests handled gracefully

**Estimated Time:** 2 hours

### Phase 3 Deliverables

- [ ] Data Agent `RewardsLoyaltyAgent` created in Fabric workspace
- [ ] System instructions configured with domain context and guidelines
- [ ] Sample queries added for training
- [ ] Test results documented with ≥90% pass rate
- [ ] Data Agent API accessible via service principal
- [ ] API endpoint and auth config stored in `config/fabric-workspace-config.json`
- [ ] Performance benchmarks documented

### Phase 3 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Agent generates incorrect SQL | Medium | High | Extensive sample queries; iterative refinement of instructions; return SQL to user for review |
| Query latency too high (>30 seconds) | Medium | Medium | Optimize views with indexes; use materialized views; set appropriate timeout; provide feedback to user |
| Agent hallucinates columns/tables not in schema | Low | Medium | Strict schema scope (semantic only); validate SQL before execution; clear error messages |
| PII exposed in results | Medium | High | Instructions emphasize no PII; test with PII-specific queries; implement column masking if needed |

---

## Phase 4: Web Application

**Objective:** Develop and deploy a React-based web application with backend API to expose Data Agent to AAP marketing team.

**Duration:** 1-2 weeks  
**Owner:** Full-Stack Development Team  
**Prerequisites:**
- Phase 3 complete (Data Agent API accessible)
- Azure subscription for deployment (Static Web Apps, Functions, Key Vault)
- Entra ID app registrations created

### Tasks

#### 4.1 Project Scaffolding

**Steps:**
1. **Create Git Repository Structure:**
   ```
   AAP-DataAgent-POC/
   ├── frontend/          # React SPA
   ├── backend/           # Azure Functions API
   ├── config/            # Configuration files
   ├── docs/              # Documentation
   └── .github/workflows/ # CI/CD pipelines
   ```

2. **Frontend (React SPA):**
   ```bash
   npx create-react-app frontend --template typescript
   cd frontend
   npm install @azure/msal-browser @azure/msal-react axios
   ```

3. **Backend (Azure Functions - Node.js):**
   ```bash
   cd backend
   func init --worker-runtime node --language typescript
   func new --template "HTTP trigger" --name query
   npm install @azure/identity @azure/keyvault-secrets axios
   ```

4. **Initialize Git:**
   ```bash
   git init
   git add .
   git commit -m "Initial project scaffolding"
   ```

**Validation:**
- Frontend runs locally: `npm start` → http://localhost:3000
- Backend runs locally: `func start` → http://localhost:7071

**Estimated Time:** 2 hours

#### 4.2 Azure Resources Provisioning

**Steps:**
1. **Create Resource Group:**
   ```bash
   az group create --name aap-data-agent-rg --location eastus
   ```

2. **Create Key Vault:**
   ```bash
   az keyvault create \
     --name aap-data-agent-kv \
     --resource-group aap-data-agent-rg \
     --location eastus
   ```

3. **Store Secrets in Key Vault:**
   ```bash
   az keyvault secret set --vault-name aap-data-agent-kv \
     --name FabricServicePrincipalClientId --value "<client-id>"
   
   az keyvault secret set --vault-name aap-data-agent-kv \
     --name FabricServicePrincipalClientSecret --value "<client-secret>"
   
   az keyvault secret set --vault-name aap-data-agent-kv \
     --name FabricDataAgentApiUrl --value "<api-endpoint>"
   ```

4. **Create Static Web App:**
   ```bash
   az staticwebapp create \
     --name aap-data-agent-web \
     --resource-group aap-data-agent-rg \
     --location eastus2 \
     --sku Free \
     --app-location "frontend" \
     --api-location "backend" \
     --output-location "build"
   ```

5. **Create Function App (if standalone, else skip):**
   - If using managed Functions with Static Web App, skip this
   - If using standalone Function App:
   ```bash
   az functionapp create \
     --name aap-data-agent-api \
     --resource-group aap-data-agent-rg \
     --consumption-plan-location eastus \
     --runtime node \
     --runtime-version 20 \
     --storage-account <storage-account-name>
   ```

6. **Configure Managed Identity for Function App:**
   ```bash
   az functionapp identity assign \
     --name aap-data-agent-api \
     --resource-group aap-data-agent-rg
   
   # Grant Key Vault access
   PRINCIPAL_ID=$(az functionapp identity show --name aap-data-agent-api --resource-group aap-data-agent-rg --query principalId -o tsv)
   
   az keyvault set-policy --name aap-data-agent-kv \
     --object-id $PRINCIPAL_ID \
     --secret-permissions get list
   ```

**Validation:**
- Resource group exists: `az group show --name aap-data-agent-rg`
- Key Vault accessible: `az keyvault secret list --vault-name aap-data-agent-kv`
- Static Web App created: `az staticwebapp show --name aap-data-agent-web`

**Estimated Time:** 1-2 hours

#### 4.3 Entra ID App Registrations

**Steps:**
1. **SPA App Registration:**
   - Azure Portal → Entra ID → **App registrations** → **New registration**
   - Name: `AAP-DataAgent-SPA`
   - Redirect URI: 
     - Type: Single-page application (SPA)
     - URI: `https://aap-data-agent-web.azurestaticapps.net` (update with actual Static Web App URL)
   - Register
   - Note **Application (client) ID**

2. **Backend API App Registration:**
   - New registration
   - Name: `AAP-DataAgent-API`
   - Expose an API:
     - Application ID URI: `api://aap-data-agent-api` (or custom domain if available)
     - Add scope:
       - Scope name: `Query.Execute`
       - Who can consent: Admins and users
       - Description: "Execute queries via Data Agent"
   - Note **Application (client) ID**

3. **Configure API Permissions (SPA → API):**
   - SPA app registration → **API permissions** → **Add a permission**
   - **My APIs** → Select `AAP-DataAgent-API`
   - Select `Query.Execute` scope
   - Add permissions
   - (Optional) Grant admin consent

4. **Update Frontend Config:**
   - `frontend/src/authConfig.ts`:

```typescript
export const msalConfig = {
  auth: {
    clientId: "<SPA-client-id>",
    authority: "https://login.microsoftonline.com/<tenant-id>",
    redirectUri: "https://aap-data-agent-web.azurestaticapps.net",
  },
};

export const loginRequest = {
  scopes: ["api://aap-data-agent-api/Query.Execute"],
};
```

**Validation:**
- Both app registrations visible in Entra ID
- SPA has permission to call API (API permissions list shows `Query.Execute`)
- Frontend config updated with correct client IDs

**Estimated Time:** 1 hour

#### 4.4 Backend API Implementation

**Steps:**
1. **Implement Query Endpoint (`backend/query/index.ts`):**

```typescript
import { AzureFunction, Context, HttpRequest } from "@azure/functions";
import { DefaultAzureCredential } from "@azure/identity";
import { SecretClient } from "@azure/keyvault-secrets";
import axios from "axios";

const httpTrigger: AzureFunction = async function (
  context: Context,
  req: HttpRequest
): Promise<void> {
  // 1. Validate authentication (Easy Auth handles this, user in req.headers)
  const user = req.headers["x-ms-client-principal"];
  if (!user) {
    context.res = {
      status: 401,
      body: { error: "Unauthorized" },
    };
    return;
  }

  // 2. Extract query from request
  const { question } = req.body;
  if (!question) {
    context.res = {
      status: 400,
      body: { error: "Missing 'question' in request body" },
    };
    return;
  }

  try {
    // 3. Get secrets from Key Vault
    const keyVaultUrl = "https://aap-data-agent-kv.vault.azure.net";
    const credential = new DefaultAzureCredential();
    const client = new SecretClient(keyVaultUrl, credential);

    const clientIdSecret = await client.getSecret("FabricServicePrincipalClientId");
    const clientSecretSecret = await client.getSecret("FabricServicePrincipalClientSecret");
    const apiUrlSecret = await client.getSecret("FabricDataAgentApiUrl");

    // 4. Acquire token for Fabric API
    const tokenResponse = await axios.post(
      `https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token`,
      new URLSearchParams({
        client_id: clientIdSecret.value,
        client_secret: clientSecretSecret.value,
        scope: "https://analysis.windows.net/powerbi/api/.default",
        grant_type: "client_credentials",
      }),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    );

    const accessToken = tokenResponse.data.access_token;

    // 5. Call Fabric Data Agent API
    const agentResponse = await axios.post(
      apiUrlSecret.value,
      { query: question },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        timeout: 30000, // 30 second timeout
      }
    );

    // 6. Return response to frontend
    context.res = {
      status: 200,
      body: {
        success: true,
        answer: agentResponse.data.answer,
        sql: agentResponse.data.sql,
        results: agentResponse.data.results,
        executionTime: agentResponse.data.executionTime,
      },
    };
  } catch (error) {
    context.log.error("Error calling Data Agent:", error);
    context.res = {
      status: 500,
      body: {
        success: false,
        error: error.response?.data?.error || error.message,
      },
    };
  }
};

export default httpTrigger;
```

2. **Configure Function App Settings:**
   - If using standalone Function App, add app settings:
     - `KEY_VAULT_URL=https://aap-data-agent-kv.vault.azure.net`
     - `AZURE_TENANT_ID=<tenant-id>`

3. **Enable Easy Auth (Azure Functions Authentication):**
   - Azure Portal → Function App → **Authentication**
   - Add identity provider: **Microsoft**
   - App registration: Select `AAP-DataAgent-API`
   - Require authentication: Yes
   - Unauthenticated requests: Return 401

**Validation:**
- Deploy function: `func azure functionapp publish aap-data-agent-api`
- Test endpoint with Postman:
  - POST to `https://aap-data-agent-api.azurewebsites.net/api/query`
  - Include Authorization header (acquire token as user via MSAL)
  - Body: `{ "question": "How many gold customers?" }`
  - Verify 200 response with answer

**Estimated Time:** 4-6 hours

#### 4.5 Frontend React Implementation

**Steps:**
1. **Implement Authentication (`frontend/src/App.tsx`):**

```typescript
import React from "react";
import { MsalProvider, useMsal, useIsAuthenticated } from "@azure/msal-react";
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "./authConfig";
import ChatInterface from "./components/ChatInterface";

const msalInstance = new PublicClientApplication(msalConfig);

function App() {
  return (
    <MsalProvider instance={msalInstance}>
      <MainContent />
    </MsalProvider>
  );
}

function MainContent() {
  const { instance } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleLogin = () => {
    instance.loginPopup();
  };

  if (!isAuthenticated) {
    return (
      <div style={{ textAlign: "center", marginTop: "100px" }}>
        <h1>AAP Data Agent</h1>
        <button onClick={handleLogin}>Sign In with Microsoft</button>
      </div>
    );
  }

  return <ChatInterface />;
}

export default App;
```

2. **Implement Chat UI (`frontend/src/components/ChatInterface.tsx`):**

```typescript
import React, { useState } from "react";
import { useMsal } from "@azure/msal-react";
import { loginRequest } from "../authConfig";
import axios from "axios";

interface Message {
  role: "user" | "agent";
  content: string;
  sql?: string;
}

function ChatInterface() {
  const { instance, accounts } = useMsal();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendQuery = async () => {
    if (!input.trim()) return;

    // Add user message
    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // Acquire token
      const response = await instance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
      });

      // Call backend API
      const apiResponse = await axios.post(
        "/api/query", // Proxied by Static Web App
        { question: input },
        {
          headers: {
            Authorization: `Bearer ${response.accessToken}`,
          },
        }
      );

      // Add agent response
      const agentMessage: Message = {
        role: "agent",
        content: apiResponse.data.answer,
        sql: apiResponse.data.sql,
      };
      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "agent",
        content: `Error: ${error.response?.data?.error || error.message}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
      <h1>AAP Rewards & Loyalty Data Agent</h1>
      
      <div style={{ border: "1px solid #ccc", minHeight: "400px", padding: "10px", marginBottom: "20px" }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ marginBottom: "10px" }}>
            <strong>{msg.role === "user" ? "You" : "Agent"}:</strong> {msg.content}
            {msg.sql && (
              <details style={{ marginTop: "5px", fontSize: "0.9em", color: "#666" }}>
                <summary>View SQL</summary>
                <pre>{msg.sql}</pre>
              </details>
            )}
          </div>
        ))}
        {loading && <div>Agent is thinking...</div>}
      </div>

      <div style={{ display: "flex" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && sendQuery()}
          placeholder="Ask a question about rewards and loyalty data..."
          style={{ flex: 1, padding: "10px", fontSize: "16px" }}
        />
        <button onClick={sendQuery} disabled={loading} style={{ padding: "10px 20px" }}>
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatInterface;
```

3. **Build Frontend:**
   ```bash
   cd frontend
   npm run build
   ```

**Validation:**
- Frontend builds successfully (no TypeScript errors)
- Can run locally with mock API: `npm start`

**Estimated Time:** 6-8 hours

#### 4.6 Deployment & CI/CD Pipeline

**Steps:**
1. **Configure GitHub Actions for Static Web App:**
   - Static Web App creation auto-generates workflow file: `.github/workflows/azure-static-web-apps-<name>.yml`
   - Verify workflow file exists and is configured correctly:

```yaml
name: Azure Static Web Apps CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build And Deploy
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "frontend"
          api_location: "backend"
          output_location: "build"
```

2. **Deploy to Azure:**
   - Commit code: `git add . && git commit -m "Initial deployment" && git push origin main`
   - GitHub Actions triggers automatically
   - Monitor deployment: GitHub repo → **Actions** tab

3. **Verify Deployment:**
   - Navigate to Static Web App URL (e.g., `https://aap-data-agent-web.azurestaticapps.net`)
   - Should see login page
   - Sign in with AAP credentials
   - Test query: "How many customers are in the gold loyalty tier?"
   - Verify response received

**Validation:**
- GitHub Actions workflow succeeds (green checkmark)
- Static Web App accessible at public URL
- Can sign in and execute queries
- Backend API accessible from frontend

**Estimated Time:** 2-3 hours

#### 4.7 Custom Domain & SSL (Optional)

**Steps:**
1. **Configure Custom Domain:**
   - Azure Portal → Static Web App → **Custom domains**
   - Add custom domain: `dataagent.advanceautoparts.com`
   - Verify domain ownership (add TXT record to DNS)
   - Wait for SSL provisioning (auto-managed by Azure)

2. **Update Entra ID Redirect URIs:**
   - Update SPA app registration redirect URI to custom domain
   - Update `frontend/src/authConfig.ts` with custom domain

**Validation:**
- Custom domain resolves to Static Web App
- HTTPS works with valid certificate
- Authentication works with custom domain

**Estimated Time:** 1-2 hours (if custom domain available)

### Phase 4 Deliverables

- [ ] React SPA with MSAL authentication
- [ ] Backend API (Azure Functions) with Data Agent integration
- [ ] Azure resources provisioned (Static Web App, Key Vault, Entra ID apps)
- [ ] CI/CD pipeline configured (GitHub Actions)
- [ ] Application deployed to Azure and accessible
- [ ] End-to-end test passed (user can sign in and query data)

### Phase 4 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CORS issues between frontend and backend | Medium | Medium | Configure CORS in Function App settings; use Static Web App managed API (auto-configured) |
| Token acquisition fails (MSAL errors) | Medium | High | Thorough testing of auth flow; clear error messages; fallback to login redirect if popup blocked |
| Backend timeout calling Data Agent | Medium | Medium | Set appropriate timeout (30s); show loading indicator; handle timeout gracefully |
| Key Vault access denied (managed identity issue) | Low | High | Verify managed identity assigned; test Key Vault access independently; check access policies |

---

## Schema Swap Procedure

**Objective:** Replace placeholder schema with production schema when AAP provides real data, with minimal impact to deployed application.

**Duration:** 2-3 days  
**Owner:** Data Engineering Team + Livingston (Data Modeler)  
**Prerequisites:**
- AAP provides production PostgreSQL connection details
- Production schema documented (table names, column names, relationships)
- UAT environment available for testing swap before production

### Steps

#### Step 1: Production Schema Analysis

**Tasks:**
1. **Receive Production Schema Documentation:**
   - AAP provides: ER diagram, DDL scripts, data dictionary
   - Review schema: table names, column names, data types, relationships

2. **Gap Analysis:**
   - Compare production schema to placeholder schema
   - Identify differences:
     - Different table names? (e.g., `prod_customers` vs `customers`)
     - Different column names? (e.g., `cust_id` vs `customer_id`)
     - Different data types? (e.g., `varchar(100)` vs `text`)
     - Additional columns? (new attributes not in placeholder)
     - Missing columns? (placeholder had columns production doesn't)

3. **Create Mapping Document:**
   - `docs/schema-mapping.md`:

| Production Table | Production Column | Placeholder Table | Placeholder Column | Notes |
|------------------|-------------------|-------------------|--------------------|-------|
| loyalty_customers | cust_id | customers | customer_id | Rename in view |
| loyalty_customers | email_addr | customers | email | Rename in view |
| loyalty_customers | tier | customers | loyalty_tier | Rename in view |
| purchase_history | trans_id | transactions | transaction_id | Rename in view |
| ... | ... | ... | ... | ... |

**Estimated Time:** 4 hours

#### Step 2: Configure Mirroring for Production Data

**Tasks:**
1. **Update Fabric Mirroring Connection:**
   - Fabric portal → Mirroring → `AAP-PostgreSQL-RewardsLoyalty` → Settings
   - Update connection string to production PostgreSQL server
   - Update credentials (production user/password)
   - Test connection

2. **Select Production Tables:**
   - Deselect placeholder tables (if using same mirroring, OR create new mirroring)
   - Select production tables (e.g., `loyalty_customers`, `purchase_history`, ...)
   - Configure destination: Still `mirrored` schema (keep consistent)

3. **Start Mirroring (Initial Snapshot):**
   - Start mirroring
   - Wait for initial snapshot to complete (may take hours depending on data volume)
   - Validate row counts match production source

**Estimated Time:** 2-4 hours (plus snapshot wait time)

#### Step 3: Update Semantic Views

**Tasks:**
1. **Update View Definitions:**
   - For each view in `semantic` schema, update SQL to map production tables/columns to contract:

**Before (Placeholder):**
```sql
CREATE VIEW semantic.vw_CustomerProfile AS
SELECT
    customer_id AS CustomerID,
    email AS Email,
    loyalty_tier AS LoyaltyTier,
    lifetime_points AS LifetimePoints,
    join_date AS JoinDate
FROM mirrored.customers;
```

**After (Production):**
```sql
CREATE OR ALTER VIEW semantic.vw_CustomerProfile AS
SELECT
    cust_id AS CustomerID,
    email_addr AS Email,
    tier AS LoyaltyTier,
    total_points AS LifetimePoints,
    registration_date AS JoinDate
FROM mirrored.loyalty_customers;
```

2. **Deploy Updated Views:**
   - Connect to Lakehouse SQL endpoint
   - Run `ALTER VIEW` statements for each view
   - Verify no SQL errors

3. **Handle New/Missing Columns:**
   - If production has new columns not in contract, add new views (e.g., `vw_CustomerExtended`)
   - If production missing columns from placeholder, use default values or remove from contract (breaking change, coordinate with app team)

**Estimated Time:** 2-4 hours

#### Step 4: Update Data Agent Instructions

**Tasks:**
1. **Review Sample Queries:**
   - Check if sample queries still valid with production data
   - Update if business semantics changed (e.g., tier names: "Gold" → "Platinum")

2. **Update Entity Descriptions:**
   - Update `entityDescriptions` in Data Agent config to reflect production terminology

3. **Re-deploy Data Agent Configuration:**
   - Update agent settings in Fabric portal
   - Or, if using config file, re-run deployment script

**Estimated Time:** 1-2 hours

#### Step 5: Test with Production Data

**Tasks:**
1. **Run Data Agent Tests:**
   - Re-run all sample queries from Phase 3 test plan
   - Verify SQL still generates correctly
   - Verify results make sense (row counts, values)

2. **Test Application End-to-End:**
   - Open web app
   - Sign in as test user
   - Run queries: "How many gold customers?", "Average transaction amount?", etc.
   - Verify responses correct based on production data

3. **Smoke Test New Columns (if any):**
   - If production has new attributes, test queries that reference them
   - Example: "Show me customers with email domain 'gmail.com'" (if email domain now available)

**Estimated Time:** 2-3 hours

#### Step 6: Cutover & Validation

**Tasks:**
1. **Schedule Cutover:**
   - Plan cutover during low-usage window (e.g., evening or weekend)
   - Notify marketing team (brief downtime if switching Fabric workspace)

2. **Execute Cutover:**
   - If using separate workspace for prod: Update backend API config to point to prod Data Agent
   - If using same workspace: Views already updated in Step 3, no app changes needed

3. **Post-Cutover Validation:**
   - Verify marketing team can access app
   - Run queries, verify results
   - Monitor for errors in logs (Function App, Data Agent)

4. **Rollback Plan:**
   - If issues detected, revert view definitions to placeholder mappings
   - Or switch backend API back to placeholder workspace
   - Document issues, iterate on view mappings

**Estimated Time:** 2 hours (plus monitoring)

### Schema Swap Checklist

- [ ] Production schema documented and analyzed
- [ ] Schema mapping document created (`docs/schema-mapping.md`)
- [ ] Fabric Mirroring configured for production PostgreSQL
- [ ] Initial snapshot completed and validated
- [ ] Semantic views updated with production table/column mappings
- [ ] Views tested (all queries return expected results)
- [ ] Data Agent instructions updated (if needed)
- [ ] Application tested end-to-end with production data
- [ ] Cutover executed (views deployed to production)
- [ ] Post-cutover validation passed
- [ ] Marketing team notified and trained on any differences

---

## Risk Register

**Project-Wide Risks & Mitigations**

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| **AAP delays providing production schema** | High | Medium | Proceed with placeholder; ensure abstraction layer solid; communicate timeline impact | Danny |
| **Fabric capacity insufficient (CU throttling)** | Medium | High | Monitor capacity metrics during POC; request additional capacity or upgrade if needed; optimize queries | DevOps |
| **PostgreSQL network connectivity issues** | Medium | High | Validate network access early (Phase 2); use private link if required; test from Fabric notebook | Data Eng |
| **Data Agent generates incorrect SQL frequently** | Medium | High | Extensive sample queries; iterative refinement; return SQL to users for validation; escalate to Microsoft support | Data Eng |
| **Marketing team finds UI not intuitive** | Medium | Medium | User testing during Phase 4; gather feedback; iterate on UX | Frontend Dev |
| **Authentication issues (MSAL, Entra ID)** | Medium | High | Test auth flow early and often; clear error messages; involve AAP IT for Entra ID config | Full-Stack Dev |
| **Schema swap introduces breaking changes** | Medium | High | Rigorous gap analysis; UAT environment for testing; rollback plan; contract views mitigate risk | Livingston, Danny |
| **Production data contains PII, compliance concerns** | Medium | High | Implement column masking; update Data Agent instructions; audit logging; consult AAP legal/compliance | Danny, Data Eng |
| **Query performance too slow (>30 seconds)** | Medium | Medium | Optimize views with indexes; materialized views; set timeout; provide progress indicator | Data Eng |
| **Scope creep (AAP requests additional features)** | High | Medium | Clear SOW; change request process; track in backlog; prioritize MVP first | Danny |

---

## Dependencies & Prerequisites

**What AAP Needs to Provide:**

### Phase 1 (Fabric Workspace)
- [ ] Access to Fabric tenant (Capacity Admin or Fabric Admin role for project team)
- [ ] Decision on which Fabric capacity to use for POC
- [ ] Naming conventions for Azure and Fabric resources

### Phase 2 (Data Mirroring)
- [ ] Azure PostgreSQL connection details:
  - Server hostname
  - Database name
  - User credentials (with SELECT and REPLICATION privileges)
- [ ] Network access approval (firewall rules or private link)
- [ ] Approval to enable logical replication (requires server restart)
- [ ] (Optional) Production schema documentation (if available early)

### Phase 3 (Data Agent)
- [ ] Sample query set from marketing team (common questions they want to ask)
- [ ] Business context: loyalty tier definitions, points rules, geographic regions
- [ ] Stakeholder for UAT (marketing team member to test agent)

### Phase 4 (Web Application)
- [ ] Azure subscription for deployment (or approval to use existing sub)
- [ ] Entra ID tenant admin access (for app registrations)
- [ ] List of authorized users (marketing team members)
- [ ] (Optional) Custom domain for web app (e.g., `dataagent.advanceautoparts.com`)

### Schema Swap
- [ ] Production schema documentation (ER diagram, DDL, data dictionary)
- [ ] Production PostgreSQL connection details
- [ ] UAT window for testing swap before production
- [ ] Approval to cutover to production data

---

## Success Criteria

**How We Know the POC is Successful:**

1. **Technical Criteria:**
   - [ ] Fabric Mirroring replicates PostgreSQL data to OneLake with <5 minute latency
   - [ ] Data Agent generates correct SQL for ≥90% of sample queries
   - [ ] Average query response time <10 seconds
   - [ ] Web application loads in <3 seconds, authenticated via Entra ID
   - [ ] Schema swap completed in <1 day with zero application code changes

2. **Business Criteria:**
   - [ ] Marketing team can answer business questions without involving IT
   - [ ] Marketing team reports positive experience (survey or feedback)
   - [ ] At least 5 distinct users actively use the tool
   - [ ] At least 50 queries executed successfully in first week

3. **Architectural Criteria:**
   - [ ] Schema abstraction layer works as designed (real schema swapped with minimal effort)
   - [ ] System is secure (no unauthorized access, PII protected)
   - [ ] System is maintainable (documentation complete, code in source control)
   - [ ] System is scalable (can handle 20+ concurrent users if needed)

---

## Timeline Summary

| Phase | Duration | Dependencies | Deliverables |
|-------|----------|--------------|--------------|
| **Phase 1: Fabric Workspace** | 3-5 days | Fabric access, capacity decision | Workspace, Lakehouse, service principal |
| **Phase 2: Data Mirroring** | 5-7 days | PostgreSQL access, network, logical replication | Mirrored data, semantic views, placeholder schema |
| **Phase 3: Data Agent** | 3-4 days | Phase 2 complete, sample queries | Configured Data Agent, API access, test results |
| **Phase 4: Web Application** | 1-2 weeks | Phase 3 complete, Azure sub, Entra ID | Deployed web app, CI/CD pipeline |
| **Schema Swap** | 2-3 days | Production schema, UAT approval | Production data live, views updated |

**Total: 3-4 weeks** (excluding waiting on AAP prerequisites)

**Recommended Approach:** Run Phases 1-2 in parallel (platform setup + data engineering), then Phase 3 (Data Agent), then Phase 4 (app development). Schema swap happens post-POC demo or when production schema available.

---

## Next Steps

**Immediate Actions (Week 1):**
1. **Kickoff Meeting:** Danny schedules with AAP stakeholders, review plan, confirm prerequisites
2. **Access Provisioning:** AAP grants Fabric and PostgreSQL access to project team
3. **Phase 1 Start:** DevOps begins Fabric workspace provisioning
4. **Placeholder Schema Design:** Livingston creates `docs/data-schema.md` (if not already done)

**Weekly Checkpoints:**
- Every Monday: Status review (what's done, what's blocked, what's next)
- Track progress against deliverables checklist
- Update risk register with new risks or mitigations

**Demo Plan:**
- End of Phase 2: Demo mirrored data and semantic views to AAP
- End of Phase 3: Demo Data Agent via Fabric portal (test queries)
- End of Phase 4: Demo web application to marketing team
- Post-Schema-Swap: Final demo with production data

---

**Document End**

*This implementation plan is maintained by Danny (Lead/Architect). For questions, updates, or to report blockers, contact the project team via `.squad/agents/danny/`.*
