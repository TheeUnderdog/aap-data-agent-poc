# AAP Data Agent POC — Implementation Plan

**Version:** 2.0
**Date:** April 2026
**Project:** Advanced Auto Parts Data Agent Proof of Concept

---

## Executive Summary

This plan provides a fully scripted, phased approach to deploying the AAP Data Agent POC. Every provisioning step uses CLI commands, REST API calls, or deployment scripts — no portal click-through required. All scripts referenced here live (or will live) in this repository under `scripts/`, `config/`, and `infra/`.

**Total Estimated Active Work:** 3–5 days hands-on
**Total Calendar Time:** 2–3 weeks (including wait time for AAP prerequisites and access grants)

> **Convention:** Time estimates in this document are split into **active work time** (hands-on-keyboard) and **wait time** (blocked on external approvals, provisioning delays, data snapshot completion, etc.).

---

## Scripts Inventory

All automation scripts referenced in this plan:

| Script | Description |
|--------|-------------|
| `scripts/setup-workspace.ps1` | Creates Fabric workspace, Lakehouse, and role assignments via REST API |
| `scripts/create-service-principal.sh` | Creates Entra ID app registration + service principal, stores secrets in Key Vault |
| `scripts/configure-postgres.sh` | Sets PostgreSQL WAL parameters, creates mirroring user, configures firewall |
| `scripts/setup-mirroring.ps1` | Creates Fabric mirrored database item via REST API / PowerShell |
| `scripts/deploy-placeholder-schema.sh` | Deploys placeholder tables and sample data to PostgreSQL |
| `scripts/create-semantic-views.sql` | SQL script to create all semantic views in Lakehouse |
| `scripts/configure-data-agent.ps1` | Creates and configures Fabric Data Agent via REST API |
| `scripts/test-data-agent.py` | Python test harness — runs sample queries against Data Agent API |
| `scripts/deploy.sh` | End-to-end Azure resource deployment (wraps Bicep + app deploy) |
| `scripts/register-entra-apps.sh` | Creates SPA and API app registrations via Azure CLI |
| `scripts/schema-swap.ps1` | Orchestrates production schema cutover (views + mirroring update) |
| `infra/main.bicep` | Bicep template for all Azure resources (Static Web App, Functions, Key Vault) |
| `config/data-agent-instructions.md` | Data Agent system prompt / grounding instructions |
| `config/sample-queries.json` | Sample question set for Data Agent training |
| `config/fabric-workspace-config.json` | Runtime config with workspace IDs, endpoints, principal info |

---

## Prerequisites & Authentication

All scripts authenticate using Azure CLI and Fabric REST API tokens.

```bash
# Login to Azure (interactive — run once per session)
az login

# Acquire a Fabric REST API token
FABRIC_TOKEN=$(az account get-access-token \
  --resource https://api.fabric.microsoft.com \
  --query accessToken -o tsv)

# Common header for all Fabric API calls
AUTH_HEADER="Authorization: Bearer $FABRIC_TOKEN"
FABRIC_BASE="https://api.fabric.microsoft.com/v1"
```

---

## Phase 1: Fabric Workspace Setup

**Objective:** Provision Fabric workspace, Lakehouse, service principal, and role assignments — entirely via script.

**Active Work Time:** 2–4 hours
**Wait Time:** 0–2 days (awaiting Fabric tenant access from AAP)
**Owner:** Data Platform Team

**Prerequisites:**
- Access to AAP's Fabric tenant (Capacity Admin or Fabric Admin role)
- Decision on which existing Fabric capacity to use
- Azure CLI installed and authenticated (`az login`)

### 1.1 Create Fabric Workspace

**Script:** `scripts/setup-workspace.ps1`

```bash
# Create workspace
curl -s -X POST "$FABRIC_BASE/workspaces" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "AAP-RewardsLoyalty-POC",
    "description": "POC for natural language data querying over rewards/loyalty data",
    "capacityId": "<capacity-guid>"
  }'
# Response includes workspaceId — capture it
```

```powershell
# PowerShell equivalent (scripts/setup-workspace.ps1)
$body = @{
    displayName = "AAP-RewardsLoyalty-POC"
    description = "POC for natural language data querying over rewards/loyalty data"
    capacityId  = $CapacityId
} | ConvertTo-Json

$workspace = Invoke-RestMethod -Uri "$FabricBase/workspaces" `
    -Method POST -Headers $headers -Body $body -ContentType "application/json"

$workspaceId = $workspace.id
Write-Host "Workspace created: $workspaceId"
```

**Validation:**

```bash
# List workspaces — confirm AAP-RewardsLoyalty-POC exists
curl -s "$FABRIC_BASE/workspaces" -H "$AUTH_HEADER" | jq '.value[] | select(.displayName == "AAP-RewardsLoyalty-POC")'
```

### 1.2 Create Lakehouse

```bash
# Create Lakehouse item in workspace
curl -s -X POST "$FABRIC_BASE/workspaces/$WORKSPACE_ID/items" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "RewardsLoyaltyData",
    "description": "Mirrored PostgreSQL data for rewards and loyalty program",
    "type": "Lakehouse"
  }'
# Response includes Lakehouse itemId and SQL endpoint info
```

**Validation:**

```bash
# List items in workspace — confirm Lakehouse exists
curl -s "$FABRIC_BASE/workspaces/$WORKSPACE_ID/items?type=Lakehouse" \
  -H "$AUTH_HEADER" | jq '.value[]'
```

SQL endpoint connection string format: `<workspace-name>.datawarehouse.fabric.microsoft.com`

### 1.3 Schema Creation in Lakehouse

Connect to Lakehouse SQL endpoint (via `sqlcmd`, Azure Data Studio, or Fabric SQL editor):

```sql
-- Create schema for mirrored tables
CREATE SCHEMA mirrored;
GO

-- Create schema for semantic views (contract layer)
CREATE SCHEMA semantic;
GO

-- Verify
SELECT name FROM sys.schemas WHERE name IN ('mirrored', 'semantic');
```

### 1.4 Service Principal Setup

**Script:** `scripts/create-service-principal.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="AAP-DataAgent-ServicePrincipal"
KEYVAULT_NAME="aap-data-agent-kv"

# Create Entra ID app registration
APP_ID=$(az ad app create \
  --display-name "$APP_NAME" \
  --sign-in-audience AzureADMyOrg \
  --query appId -o tsv)

# Create service principal for the app
az ad sp create --id "$APP_ID"

# Generate client secret (6-month expiry)
CLIENT_SECRET=$(az ad app credential reset \
  --id "$APP_ID" \
  --years 0.5 \
  --query password -o tsv)

TENANT_ID=$(az account show --query tenantId -o tsv)

echo "App ID:        $APP_ID"
echo "Tenant ID:     $TENANT_ID"
echo "Client Secret: (stored in Key Vault)"

# Store credentials in Key Vault (created in Phase 4, or create early)
az keyvault secret set --vault-name "$KEYVAULT_NAME" \
  --name "FabricSPClientId" --value "$APP_ID"
az keyvault secret set --vault-name "$KEYVAULT_NAME" \
  --name "FabricSPClientSecret" --value "$CLIENT_SECRET"
az keyvault secret set --vault-name "$KEYVAULT_NAME" \
  --name "FabricSPTenantId" --value "$TENANT_ID"
```

### 1.5 Workspace Role Assignment

Grant the service principal Contributor access to the workspace:

```bash
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

curl -s -X POST "$FABRIC_BASE/workspaces/$WORKSPACE_ID/roleAssignments" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d "{
    \"principal\": {
      \"id\": \"$SP_OBJECT_ID\",
      \"type\": \"ServicePrincipal\"
    },
    \"role\": \"Contributor\"
  }"
```

Grant SQL-level read access on semantic schema:

```sql
-- Connect to Lakehouse SQL endpoint as admin
CREATE USER [AAP-DataAgent-ServicePrincipal] FROM EXTERNAL PROVIDER;
GO

GRANT SELECT ON SCHEMA::semantic TO [AAP-DataAgent-ServicePrincipal];
GO
```

### 1.6 Save Workspace Configuration

Write outputs to `config/fabric-workspace-config.json` (committed to repo with placeholder GUIDs; actual values injected at deploy time or stored in Key Vault):

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
    "clientId": "<from-key-vault>",
    "displayName": "AAP-DataAgent-ServicePrincipal",
    "tenantId": "<from-key-vault>"
  }
}
```

### Phase 1 Deliverables

- [ ] Fabric workspace `AAP-RewardsLoyalty-POC` created via API
- [ ] Lakehouse `RewardsLoyaltyData` with SQL endpoint enabled
- [ ] Schemas `mirrored` and `semantic` created
- [ ] Service principal created, credentialed, and stored in Key Vault
- [ ] Contributor role assigned via REST API
- [ ] Configuration saved to `config/fabric-workspace-config.json`

### Phase 1 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fabric capacity at max CU utilization | Medium | High | Query capacity metrics via API before assignment; request additional capacity if needed |
| Service principal permissions insufficient | Medium | Medium | Test end-to-end in Phase 3; adjust role assignments via API |
| Network connectivity to SQL endpoint | Low | Medium | Validate from dev workstation and Azure Functions runtime |

---

## Phase 2: Data Mirroring

**Objective:** Configure PostgreSQL for logical replication, set up Fabric Mirroring, deploy placeholder schema, and create semantic views.

**Active Work Time:** 4–6 hours
**Wait Time:** 0–3 days (awaiting PostgreSQL access, server restart approval)
**Owner:** Data Engineering Team

**Prerequisites:**
- Phase 1 complete
- Azure PostgreSQL Flexible Server access (admin credentials)
- Network connectivity from Fabric to PostgreSQL
- Approval to set `wal_level = logical` (requires server restart)

### 2.1 PostgreSQL Configuration

**Script:** `scripts/configure-postgres.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PG_SERVER="<server-name>"
PG_RG="<resource-group>"

# Enable logical replication (triggers server restart — ~2-5 min downtime)
az postgres flexible-server parameter set \
  --resource-group "$PG_RG" --server-name "$PG_SERVER" \
  --name wal_level --value logical

az postgres flexible-server parameter set \
  --resource-group "$PG_RG" --server-name "$PG_SERVER" \
  --name max_replication_slots --value 10

az postgres flexible-server parameter set \
  --resource-group "$PG_RG" --server-name "$PG_SERVER" \
  --name max_wal_senders --value 10

# Restart server to apply wal_level change
az postgres flexible-server restart \
  --resource-group "$PG_RG" --server-name "$PG_SERVER"

echo "Waiting for server restart..."
az postgres flexible-server wait --name "$PG_SERVER" \
  --resource-group "$PG_RG" --created

# Add firewall rule for Fabric service
az postgres flexible-server firewall-rule create \
  --resource-group "$PG_RG" --name "$PG_SERVER" \
  --rule-name AllowFabricServices \
  --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
# Note: 0.0.0.0 allows all Azure services. For production, use specific Fabric IPs.
```

**Create Mirroring User:**

```sql
-- Run via psql or Azure Data Studio against PostgreSQL
CREATE USER fabric_mirror WITH PASSWORD '<secure-password>';
GRANT CONNECT ON DATABASE <rewards_db> TO fabric_mirror;
GRANT USAGE ON SCHEMA public TO fabric_mirror;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fabric_mirror;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fabric_mirror;
ALTER USER fabric_mirror REPLICATION;
```

**Validation:**

```bash
# Verify WAL level
psql -h "$PG_SERVER.postgres.database.azure.com" -U <admin> -d <db> \
  -c "SHOW wal_level;"
# Expected: logical
```

### 2.2 Placeholder Schema Deployment

**Script:** `scripts/deploy-placeholder-schema.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PG_HOST="<server>.postgres.database.azure.com"
PG_USER="<admin-user>"
PG_DB="<rewards_db>"

# Deploy schema, indexes, and sample data
psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
  -f database/placeholder-schema/01-create-tables.sql
psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
  -f database/placeholder-schema/02-create-indexes.sql
psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" \
  -f database/placeholder-schema/03-insert-sample-data.sql

echo "Placeholder schema deployed. Verifying row counts..."
psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -c "
  SELECT 'customers' AS table_name, COUNT(*) FROM customers
  UNION ALL SELECT 'transactions', COUNT(*) FROM transactions
  UNION ALL SELECT 'rewards', COUNT(*) FROM rewards
  UNION ALL SELECT 'redemptions', COUNT(*) FROM redemptions
  UNION ALL SELECT 'products', COUNT(*) FROM products
  UNION ALL SELECT 'stores', COUNT(*) FROM stores;
"
```

Expected counts: ~100K customers, ~1M transactions, ~100K rewards.

### 2.3 Configure Fabric Mirroring

**Script:** `scripts/setup-mirroring.ps1`

Create a mirrored database item in Fabric via REST API:

```bash
# Create mirrored database item
curl -s -X POST "$FABRIC_BASE/workspaces/$WORKSPACE_ID/items" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "AAP-PostgreSQL-RewardsLoyalty",
    "type": "MirroredDatabase",
    "description": "Mirrored Azure PostgreSQL rewards/loyalty data"
  }'
```

> **Note on Mirroring Configuration:** As of this writing, the Fabric REST API supports creating mirrored database items but detailed mirroring configuration (connection strings, table selection, target schema mapping) may require the Fabric PowerShell module or Python SDK. The script `scripts/setup-mirroring.ps1` implements the full setup:

```powershell
# scripts/setup-mirroring.ps1 — Fabric mirroring configuration
param(
    [string]$WorkspaceId,
    [string]$PgServer,
    [string]$PgDatabase,
    [string]$PgUser,
    [string]$PgPassword,
    [string[]]$Tables = @("customers","transactions","rewards","redemptions","products","stores")
)

$headers = @{ Authorization = "Bearer $FabricToken"; "Content-Type" = "application/json" }

# Step 1: Create mirrored database item
$mirrorBody = @{
    displayName = "AAP-PostgreSQL-RewardsLoyalty"
    type        = "MirroredDatabase"
    definition  = @{
        parts = @(@{
            path    = "mirroring.json"
            payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((@{
                source = @{
                    type             = "AzurePostgreSql"
                    connectionString = "Host=$PgServer.postgres.database.azure.com;Port=5432;Database=$PgDatabase;Username=$PgUser;Password=$PgPassword;SSL Mode=Require"
                }
                target = @{
                    lakehouseId = $LakehouseId
                    schema      = "mirrored"
                }
                tables = $Tables | ForEach-Object { @{ sourceTable = $_; targetTable = "mirrored.$_" } }
            } | ConvertTo-Json -Depth 10)))
            payloadType = "InlineBase64"
        })
    }
} | ConvertTo-Json -Depth 10

$mirror = Invoke-RestMethod -Uri "$FabricBase/workspaces/$WorkspaceId/items" `
    -Method POST -Headers $headers -Body $mirrorBody

Write-Host "Mirrored database created: $($mirror.id)"
Write-Host "Initial snapshot will begin automatically. Monitor status via:"
Write-Host "  GET $FabricBase/workspaces/$WorkspaceId/mirroredDatabases/$($mirror.id)/getStatus"
```

> **Alternative approach:** If the REST API definition format changes, use the Fabric Python SDK (`azure-fabric`) or the `Invoke-FabricRestMethod` PowerShell cmdlet from the `FabricPS-PBIP` community module.

**Validation (after initial snapshot completes):**

```sql
-- Connect to Lakehouse SQL endpoint
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'mirrored'
ORDER BY TABLE_NAME;

-- Verify row counts match source
SELECT 'customers' AS table_name, COUNT(*) FROM mirrored.customers
UNION ALL SELECT 'transactions', COUNT(*) FROM mirrored.transactions
UNION ALL SELECT 'rewards', COUNT(*) FROM mirrored.rewards;
```

**CDC Validation:**

```sql
-- Insert test row in PostgreSQL source
INSERT INTO customers (customer_id, email, loyalty_tier, join_date)
VALUES (999999, 'test@example.com', 'Bronze', CURRENT_DATE);

-- Wait 1-2 minutes, then check Lakehouse
SELECT * FROM mirrored.customers WHERE customer_id = 999999;
-- Should return the test row
```

### 2.4 Create Semantic Views (Contract Layer)

**Script:** `scripts/create-semantic-views.sql`

```sql
USE RewardsLoyaltyData;
GO

CREATE VIEW semantic.vw_CustomerProfile AS
SELECT
    customer_id   AS CustomerID,
    email         AS Email,
    first_name    AS FirstName,
    last_name     AS LastName,
    loyalty_tier  AS LoyaltyTier,
    lifetime_points AS LifetimePoints,
    join_date     AS JoinDate,
    last_purchase_date AS LastPurchaseDate
FROM mirrored.customers;
GO

CREATE VIEW semantic.vw_TransactionHistory AS
SELECT
    transaction_id   AS TransactionID,
    customer_id      AS CustomerID,
    transaction_date AS TransactionDate,
    store_id         AS StoreID,
    total_amount     AS TotalAmount,
    points_earned    AS PointsEarned
FROM mirrored.transactions;
GO

CREATE VIEW semantic.vw_RewardsSummary AS
SELECT
    customer_id              AS CustomerID,
    points_balance           AS PointsBalance,
    points_earned_lifetime   AS PointsEarnedLifetime,
    points_redeemed_lifetime AS PointsRedeemedLifetime,
    last_points_activity_date AS LastActivityDate
FROM mirrored.rewards;
GO

CREATE VIEW semantic.vw_RedemptionHistory AS
SELECT
    redemption_id      AS RedemptionID,
    customer_id        AS CustomerID,
    redemption_date    AS RedemptionDate,
    points_redeemed    AS PointsRedeemed,
    reward_description AS RewardDescription
FROM mirrored.redemptions;
GO

CREATE VIEW semantic.vw_StoreLocations AS
SELECT
    store_id   AS StoreID,
    store_name AS StoreName,
    city       AS City,
    state      AS State,
    zip_code   AS ZipCode,
    region     AS Region
FROM mirrored.stores;
GO
```

**Validation:**

```sql
SELECT TOP 10 * FROM semantic.vw_CustomerProfile;
SELECT TOP 10 * FROM semantic.vw_TransactionHistory;
SELECT TOP 10 * FROM semantic.vw_RewardsSummary;

-- Cross-view join (simulates Data Agent query)
SELECT
    cp.LoyaltyTier,
    COUNT(DISTINCT th.CustomerID) AS CustomerCount,
    AVG(th.TotalAmount) AS AvgTransactionAmount
FROM semantic.vw_TransactionHistory th
JOIN semantic.vw_CustomerProfile cp ON th.CustomerID = cp.CustomerID
WHERE th.TransactionDate >= DATEADD(month, -1, GETDATE())
GROUP BY cp.LoyaltyTier;
```

### 2.5 Data Quality Validation

```sql
-- Orphaned transactions check (should return 0)
SELECT COUNT(*) AS OrphanedTransactions
FROM semantic.vw_TransactionHistory th
WHERE NOT EXISTS (
    SELECT 1 FROM semantic.vw_CustomerProfile cp WHERE cp.CustomerID = th.CustomerID
);

-- Invalid loyalty tier check (should return 0 rows)
SELECT DISTINCT LoyaltyTier
FROM semantic.vw_CustomerProfile
WHERE LoyaltyTier NOT IN ('Bronze', 'Silver', 'Gold');
```

### Phase 2 Deliverables

- [ ] PostgreSQL configured for logical replication (`wal_level = logical`)
- [ ] Mirroring user created with appropriate grants
- [ ] Firewall rules set for Fabric connectivity
- [ ] Placeholder schema deployed with sample data
- [ ] Fabric Mirroring created and actively syncing (initial snapshot + CDC verified)
- [ ] Semantic views created and validated in `semantic` schema
- [ ] View definitions source-controlled in `database/views/`

### Phase 2 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PostgreSQL logical replication not supported | Low | High | Verify version ≥ 11 before starting; upgrade if needed |
| Initial snapshot too slow (>8 hours) | Medium | Medium | Use smaller sample data for POC; monitor via API |
| CDC latency >5 minutes | Medium | Medium | Monitor mirroring metrics; tune `max_wal_senders`; escalate to Microsoft support |
| Schema mismatch between source and views | Medium | High | Automated validation queries; contract documented in `docs/schema-contract.md` |

---

## Phase 3: Fabric Data Agent

**Objective:** Create a Fabric Data Agent, configure it with domain instructions and sample queries, expose via REST API, and validate programmatically.

**Active Work Time:** 4–6 hours
**Wait Time:** 0–1 day (if Data Agent feature requires enablement in tenant)
**Owner:** Data Engineering Team

**Prerequisites:**
- Phase 2 complete (mirrored data + semantic views)
- Service principal configured (Phase 1)
- Sample queries prepared (see `config/sample-queries.json`)

### 3.1 Create Data Agent

**Script:** `scripts/configure-data-agent.ps1`

```bash
# Create Data Agent item in workspace
curl -s -X POST "$FABRIC_BASE/workspaces/$WORKSPACE_ID/items" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "RewardsLoyaltyAgent",
    "type": "DataAgent",
    "description": "Natural language interface for AAP rewards and loyalty data"
  }'
```

> **Note:** Fabric Data Agent is a newer feature. If the REST API item type `DataAgent` is not yet supported, use the Fabric PowerShell SDK or Python SDK approach:

```powershell
# Fallback: scripts/configure-data-agent.ps1
param(
    [string]$WorkspaceId,
    [string]$LakehouseId
)

$headers = @{ Authorization = "Bearer $FabricToken"; "Content-Type" = "application/json" }

# Create Data Agent
$agentBody = @{
    displayName = "RewardsLoyaltyAgent"
    type        = "DataAgent"
    definition  = @{
        parts = @(@{
            path    = "agent-config.json"
            payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((@{
                dataSources = @(@{
                    type   = "Lakehouse"
                    itemId = $LakehouseId
                    schemas = @("semantic")
                })
                instructions = (Get-Content "config/data-agent-instructions.md" -Raw)
                sampleQueries = (Get-Content "config/sample-queries.json" -Raw | ConvertFrom-Json)
            } | ConvertTo-Json -Depth 10)))
            payloadType = "InlineBase64"
        })
    }
} | ConvertTo-Json -Depth 10

$agent = Invoke-RestMethod -Uri "$FabricBase/workspaces/$WorkspaceId/items" `
    -Method POST -Headers $headers -Body $agentBody
$agentId = $agent.id
Write-Host "Data Agent created: $agentId"
```

### 3.2 Data Agent Instructions

Store in `config/data-agent-instructions.md` (deployed via script, not manually pasted):

```markdown
You are a data analyst assistant for Advanced Auto Parts' loyalty rewards program.
You help marketing team members query customer, transaction, and rewards data
using natural language.

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

### 3.3 Sample Queries

Store in `config/sample-queries.json`:

```json
[
  { "question": "How many customers are in each loyalty tier?" },
  { "question": "What is the average transaction amount in the last 30 days?" },
  { "question": "Show me top 10 customers by lifetime points" },
  { "question": "How many transactions were there last month by loyalty tier?" },
  { "question": "What is the total points balance across all customers?" },
  { "question": "Which stores had the most transactions in the last quarter?" },
  { "question": "How many gold tier customers joined in the last year?" },
  { "question": "What is the average points earned per transaction by tier?" },
  { "question": "Show me monthly transaction trends for the last 6 months" },
  { "question": "How many customers have redeemed rewards in the last 90 days?" }
]
```

### 3.4 API Access Configuration

Retrieve the Data Agent API endpoint and test programmatically:

```bash
# Acquire token for Fabric API via service principal
TOKEN=$(curl -s -X POST \
  "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "scope=https://api.fabric.microsoft.com/.default" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

# Call Data Agent query API
curl -s -X POST \
  "$FABRIC_BASE/workspaces/$WORKSPACE_ID/items/$AGENT_ID/dataAgentQuery" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "query": "How many customers are in the gold loyalty tier?" }'
```

### 3.5 Automated Test Suite

**Script:** `scripts/test-data-agent.py`

```python
#!/usr/bin/env python3
"""Automated test harness for Fabric Data Agent API."""

import json, sys, time, requests
from azure.identity import ClientSecretCredential

# Config
TENANT_ID    = "<tenant-id>"      # or read from env / Key Vault
CLIENT_ID    = "<client-id>"
CLIENT_SECRET = "<client-secret>"
WORKSPACE_ID = "<workspace-id>"
AGENT_ID     = "<agent-id>"
FABRIC_BASE  = "https://api.fabric.microsoft.com/v1"

credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
token = credential.get_token("https://api.fabric.microsoft.com/.default").token
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Load sample queries
with open("config/sample-queries.json") as f:
    queries = json.load(f)

results = []
for i, q in enumerate(queries, 1):
    question = q["question"]
    start = time.time()
    try:
        resp = requests.post(
            f"{FABRIC_BASE}/workspaces/{WORKSPACE_ID}/items/{AGENT_ID}/dataAgentQuery",
            headers=headers,
            json={"query": question},
            timeout=30
        )
        elapsed = time.time() - start
        data = resp.json()
        passed = resp.status_code == 200 and "answer" in data
        results.append({"query": question, "pass": passed, "time_s": round(elapsed, 2),
                        "status": resp.status_code, "sql": data.get("sql", "N/A")})
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {i:2d}. {question} ({elapsed:.1f}s)")
    except Exception as e:
        results.append({"query": question, "pass": False, "error": str(e)})
        print(f"  [FAIL] {i:2d}. {question} — {e}")

passed = sum(1 for r in results if r["pass"])
total = len(results)
print(f"\nResults: {passed}/{total} passed ({100*passed/total:.0f}%)")
if passed / total < 0.9:
    print("WARN: Pass rate below 90% target. Review Data Agent instructions.")
    sys.exit(1)
```

Run: `python scripts/test-data-agent.py`

Target: ≥90% pass rate on sample queries. If below target, iterate on `config/data-agent-instructions.md`.

### 3.6 Performance Benchmarking

The test script above captures latency per query. Targets:
- Simple queries (aggregation, count): <5 seconds
- Complex queries (multi-join, time series): <15 seconds
- No query should timeout at 30 seconds

For concurrent load testing:

```bash
# Simple concurrency test — 5 parallel requests
for i in $(seq 1 5); do
  curl -s -X POST "$FABRIC_BASE/workspaces/$WORKSPACE_ID/items/$AGENT_ID/dataAgentQuery" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"query":"How many gold customers?"}' &
done
wait
```

### Phase 3 Deliverables

- [ ] Data Agent `RewardsLoyaltyAgent` created via script
- [ ] Instructions deployed from `config/data-agent-instructions.md`
- [ ] Sample queries deployed from `config/sample-queries.json`
- [ ] API access verified with service principal token
- [ ] Automated test suite passing ≥90% (`scripts/test-data-agent.py`)
- [ ] Performance benchmarks documented (latency per query)

### Phase 3 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Agent generates incorrect SQL | Medium | High | Extensive sample queries; iterative prompt refinement; return SQL for review |
| Query latency >30 seconds | Medium | Medium | Optimize views; materialized views; timeout + user feedback |
| Agent hallucinates columns/tables | Low | Medium | Restrict to `semantic` schema only; validate SQL before execution |
| PII exposed in results | Medium | High | Instructions emphasize no PII; test with PII-specific queries; column masking |
| Data Agent REST API not yet GA | Medium | Medium | Fallback to Python SDK or PowerShell; document alternative in script |

---

## Phase 4: Web Application

**Objective:** Deploy a React SPA + Azure Functions backend with Entra ID authentication, all provisioned via Bicep/CLI.

**Active Work Time:** 1–2 days
**Wait Time:** 0–2 days (Entra ID admin consent, DNS propagation)
**Owner:** Full-Stack Development Team

**Prerequisites:**
- Phase 3 complete (Data Agent API accessible)
- Azure subscription for deployment
- Entra ID tenant admin access

### 4.1 Azure Resources (Bicep)

**Template:** `infra/main.bicep`

All Azure resources are defined declaratively. Deploy with:

```bash
# scripts/deploy.sh
az group create --name aap-data-agent-rg --location eastus

az deployment group create \
  --resource-group aap-data-agent-rg \
  --template-file infra/main.bicep \
  --parameters \
    staticWebAppName=aap-data-agent-web \
    functionAppName=aap-data-agent-api \
    keyVaultName=aap-data-agent-kv \
    location=eastus
```

The Bicep template provisions:
- **Resource Group** (if not exists)
- **Key Vault** with secrets for service principal credentials and Data Agent API URL
- **Static Web App** (frontend hosting + managed Functions)
- **Function App** (if standalone backend needed)
- **Managed Identity** for Function App → Key Vault access
- **Application Insights** for monitoring

### 4.2 Entra ID App Registrations

**Script:** `scripts/register-entra-apps.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

TENANT_ID=$(az account show --query tenantId -o tsv)

# --- Backend API Registration ---
API_APP_ID=$(az ad app create \
  --display-name "AAP-DataAgent-API" \
  --sign-in-audience AzureADMyOrg \
  --identifier-uris "api://aap-data-agent-api" \
  --query appId -o tsv)

# Expose a scope for the API
API_OBJECT_ID=$(az ad app show --id "$API_APP_ID" --query id -o tsv)
az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$API_OBJECT_ID" \
  --body '{
    "api": {
      "oauth2PermissionScopes": [{
        "adminConsentDescription": "Execute queries via Data Agent",
        "adminConsentDisplayName": "Query.Execute",
        "id": "'$(uuidgen)'",
        "isEnabled": true,
        "type": "User",
        "value": "Query.Execute"
      }]
    }
  }'

echo "API App ID: $API_APP_ID"

# --- SPA Frontend Registration ---
SPA_APP_ID=$(az ad app create \
  --display-name "AAP-DataAgent-SPA" \
  --sign-in-audience AzureADMyOrg \
  --query appId -o tsv)

SPA_OBJECT_ID=$(az ad app show --id "$SPA_APP_ID" --query id -o tsv)

# Set redirect URI for SPA
az rest --method PATCH --uri "https://graph.microsoft.com/v1.0/applications/$SPA_OBJECT_ID" \
  --body '{
    "spa": {
      "redirectUris": ["https://aap-data-agent-web.azurestaticapps.net"]
    }
  }'

# Grant SPA permission to call API
az ad app permission add --id "$SPA_APP_ID" \
  --api "$API_APP_ID" \
  --api-permissions "<scope-id>=Scope"

# Grant admin consent
az ad app permission admin-consent --id "$SPA_APP_ID"

echo "SPA App ID: $SPA_APP_ID"
echo ""
echo "Update frontend/src/authConfig.ts with:"
echo "  clientId: $SPA_APP_ID"
echo "  authority: https://login.microsoftonline.com/$TENANT_ID"
```

### 4.3 Configure Easy Auth (Azure Functions)

```bash
# Enable Microsoft authentication on Function App
az functionapp auth microsoft update \
  --name aap-data-agent-api \
  --resource-group aap-data-agent-rg \
  --client-id "$API_APP_ID" \
  --issuer "https://login.microsoftonline.com/$TENANT_ID/v2.0" \
  --allowed-audiences "api://aap-data-agent-api"

# Require authentication (reject unauthenticated requests)
az functionapp auth update \
  --name aap-data-agent-api \
  --resource-group aap-data-agent-rg \
  --unauthenticated-client-action Return401
```

### 4.4 Backend API Implementation

The backend Azure Function (`backend/query/index.ts`) proxies authenticated requests to the Fabric Data Agent API. Key flow:

1. Validate caller via Easy Auth (`x-ms-client-principal` header)
2. Retrieve secrets from Key Vault (via managed identity)
3. Acquire Fabric API token using service principal credentials
4. Forward natural language query to Data Agent API
5. Return structured response to frontend

See `backend/query/index.ts` for full implementation. The function is already scaffolded in this repo.

### 4.5 Frontend React Implementation

The React SPA (`frontend/`) uses MSAL for Entra ID authentication and provides a chat-style interface. Key components:

- `frontend/src/authConfig.ts` — MSAL configuration (client ID, scopes)
- `frontend/src/App.tsx` — Auth wrapper + routing
- `frontend/src/components/ChatInterface.tsx` — Query input + response display

Build and test locally:

```bash
cd frontend && npm install && npm start   # http://localhost:3000
cd backend  && npm install && func start  # http://localhost:7071
```

### 4.6 CI/CD Pipeline

GitHub Actions workflow (auto-generated by Static Web Apps, customized):

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: upload
          app_location: frontend
          api_location: backend
          output_location: build
```

Deploy: `git push origin main` → GitHub Actions builds and deploys automatically.

### Phase 4 Deliverables

- [ ] Azure resources provisioned via Bicep (`infra/main.bicep`)
- [ ] Entra ID app registrations created via CLI script
- [ ] Easy Auth configured on Function App
- [ ] React SPA with MSAL authentication deployed
- [ ] Backend API proxying to Data Agent API
- [ ] CI/CD pipeline active on `main` branch
- [ ] End-to-end test passed (sign in → query → response)

### Phase 4 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CORS issues between frontend and backend | Medium | Medium | Static Web App managed API auto-configures CORS |
| MSAL token acquisition failures | Medium | High | Test auth flow thoroughly; fallback to redirect if popup blocked |
| Backend timeout calling Data Agent | Medium | Medium | 30s timeout; loading indicator; graceful error handling |
| Key Vault access denied | Low | High | Verify managed identity; test independently; check RBAC policies |

---

## Schema Swap Procedure

**Objective:** Replace placeholder schema with production AAP schema — zero application code changes required (views absorb all mapping changes).

**Active Work Time:** 4–8 hours
**Wait Time:** 0–2 days (production credentials, UAT approval)
**Owner:** Data Engineering Team

**Prerequisites:**
- AAP provides production PostgreSQL connection details
- Production schema documented (tables, columns, relationships)
- UAT window for testing

### Step 1: Schema Gap Analysis

1. Receive production DDL / ER diagram from AAP
2. Run comparison script to generate mapping document:

```bash
# Connect to production PostgreSQL and dump schema metadata
psql -h <prod-server> -U <user> -d <db> -c "
  SELECT table_name, column_name, data_type
  FROM information_schema.columns
  WHERE table_schema = 'public'
  ORDER BY table_name, ordinal_position;
" > prod-schema-metadata.csv
```

3. Create `docs/schema-mapping.md` with column-level mappings between production and placeholder

### Step 2: Update Mirroring for Production

```powershell
# scripts/schema-swap.ps1 — Update mirroring connection to production

# Option A: Update existing mirrored database connection
$updateBody = @{
    source = @{
        connectionString = "Host=$ProdServer;Port=5432;Database=$ProdDb;Username=$ProdUser;Password=$ProdPassword;SSL Mode=Require"
    }
    tables = $ProdTables | ForEach-Object { @{ sourceTable = $_; targetTable = "mirrored.$_" } }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "$FabricBase/workspaces/$WorkspaceId/mirroredDatabases/$MirrorId" `
    -Method PATCH -Headers $headers -Body $updateBody -ContentType "application/json"

# Option B: Create new mirrored database (if changing connection not supported)
# Use same approach as Phase 2.3 with production connection details
```

### Step 3: Update Semantic Views

The key benefit of the abstraction layer — only views change, not the application:

```sql
-- Example: production table is loyalty_customers, not customers
CREATE OR ALTER VIEW semantic.vw_CustomerProfile AS
SELECT
    cust_id           AS CustomerID,
    email_addr        AS Email,
    first_nm          AS FirstName,
    last_nm           AS LastName,
    tier              AS LoyaltyTier,
    total_points      AS LifetimePoints,
    registration_date AS JoinDate,
    last_purchase_dt  AS LastPurchaseDate
FROM mirrored.loyalty_customers;
GO

-- Repeat for all views, mapping production columns to contract names
-- Store updated SQL in database/views/ and run via sqlcmd
```

### Step 4: Update Data Agent Config

```bash
# Update instructions if business terminology changed (e.g., tier names)
# Edit config/data-agent-instructions.md, then redeploy:
python scripts/configure-data-agent.ps1 -WorkspaceId $WS -AgentId $AGENT -UpdateInstructions
```

### Step 5: Validate with Production Data

```bash
# Re-run the automated test suite against production data
python scripts/test-data-agent.py

# Run end-to-end: open web app → sign in → query
```

### Step 6: Cutover

- If using same workspace: views already updated — no app changes needed
- If using separate workspace: update `FabricDataAgentApiUrl` in Key Vault → restart Function App
- Rollback: revert view definitions to placeholder SQL (`git checkout database/views/`)

### Schema Swap Checklist

- [ ] Production schema documented and gap analysis complete
- [ ] Schema mapping in `docs/schema-mapping.md`
- [ ] Fabric Mirroring pointed to production PostgreSQL
- [ ] Initial snapshot completed and row counts validated
- [ ] Semantic views updated with production column mappings
- [ ] Data Agent instructions updated (if terminology changed)
- [ ] `scripts/test-data-agent.py` passing ≥90% on production data
- [ ] End-to-end app test passed
- [ ] Cutover executed
- [ ] Rollback plan documented and tested

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AAP delays providing production schema | High | Medium | Proceed with placeholder; abstraction layer isolates impact |
| Fabric capacity throttling (CU limits) | Medium | High | Monitor via API; request additional capacity; optimize queries |
| PostgreSQL network connectivity issues | Medium | High | Validate early in Phase 2; private link if required |
| Data Agent generates incorrect SQL | Medium | High | Sample queries + iterative prompt tuning; return SQL for user review |
| Marketing team finds UI not intuitive | Medium | Medium | User testing in Phase 4; gather feedback; iterate |
| Authentication issues (MSAL/Entra ID) | Medium | High | Test auth flow early; clear error messages; involve AAP IT |
| Schema swap introduces breaking changes | Medium | High | Rigorous gap analysis; UAT testing; rollback via git revert |
| Production data has PII/compliance concerns | Medium | High | Column masking; Data Agent instructions; audit logging |
| Scope creep | High | Medium | Clear SOW; change request process; prioritize MVP |

---

## Dependencies & Prerequisites

### What AAP Needs to Provide

**Phase 1 (Fabric Workspace)**
- [ ] Fabric tenant access (Capacity Admin or Fabric Admin role)
- [ ] Decision on which Fabric capacity to use
- [ ] Naming conventions for resources

**Phase 2 (Data Mirroring)**
- [ ] Azure PostgreSQL connection details (server, database, credentials)
- [ ] Network access approval (firewall rules or private link)
- [ ] Approval to enable logical replication (requires server restart)
- [ ] (Optional) Production schema documentation if available early

**Phase 3 (Data Agent)**
- [ ] Sample query set from marketing team
- [ ] Business context: loyalty tier definitions, points rules, regions
- [ ] Stakeholder for UAT

**Phase 4 (Web Application)**
- [ ] Azure subscription for deployment
- [ ] Entra ID tenant admin access
- [ ] List of authorized users (marketing team)
- [ ] (Optional) Custom domain for web app

**Schema Swap**
- [ ] Production schema documentation (ER diagram, DDL, data dictionary)
- [ ] Production PostgreSQL connection details
- [ ] UAT window and cutover approval

---

## Success Criteria

**Technical:**
- [ ] Fabric Mirroring replicates data with <5 minute latency
- [ ] Data Agent generates correct SQL for ≥90% of sample queries
- [ ] Average query response time <10 seconds
- [ ] Web app loads in <3 seconds with Entra ID authentication
- [ ] Schema swap completed in <1 day with zero application code changes

**Business:**
- [ ] Marketing team can answer business questions without IT involvement
- [ ] Positive user feedback from marketing team
- [ ] ≥5 distinct active users
- [ ] ≥50 successful queries in first week

**Architectural:**
- [ ] Schema abstraction layer validated (swap with minimal effort)
- [ ] Secure: no unauthorized access, PII protected
- [ ] Maintainable: documentation complete, all config in source control
- [ ] All provisioning reproducible via scripts (no portal dependencies)

---

## Timeline Summary

| Phase | Active Work | Wait Time | Total Calendar | Key Deliverables |
|-------|-------------|-----------|----------------|------------------|
| **Phase 1: Fabric Workspace** | 2–4 hours | 0–2 days | 1–2 days | Workspace, Lakehouse, service principal |
| **Phase 2: Data Mirroring** | 4–6 hours | 0–3 days | 1–4 days | Mirrored data, semantic views |
| **Phase 3: Data Agent** | 4–6 hours | 0–1 day | 1–2 days | Configured agent, API access, tests |
| **Phase 4: Web Application** | 1–2 days | 0–2 days | 2–4 days | Deployed app, CI/CD |
| **Schema Swap** | 4–8 hours | 0–2 days | 1–3 days | Production data live |

**Total Active Work:** 3–5 days
**Total Calendar Time:** 2–3 weeks (including AAP prerequisites and access grants)

**Recommended Approach:** Run Phases 1–2 in parallel (workspace + data setup). Phase 3 follows immediately. Phase 4 can overlap with Phase 3 (frontend/backend scaffolding). Schema swap executes when AAP provides production schema.

---

## Next Steps

**Immediate Actions:**
1. Kickoff meeting with AAP stakeholders — review plan, confirm prerequisites
2. AAP grants Fabric tenant and PostgreSQL access
3. Run `scripts/setup-workspace.ps1` (Phase 1)
4. Run `scripts/configure-postgres.sh` + `scripts/deploy-placeholder-schema.sh` (Phase 2, parallel)

**Weekly Checkpoints:**
- Status review: what's done, what's blocked, what's next
- Track progress against deliverables checklist
- Update risk register

**Demo Plan:**
- End of Phase 2: Demo mirrored data + semantic views
- End of Phase 3: Demo Data Agent via API (test queries)
- End of Phase 4: Demo web application to marketing team
- Post-Schema-Swap: Final demo with production data

---

*This implementation plan is maintained by the project team. For questions or to report blockers, contact the project leads.*
