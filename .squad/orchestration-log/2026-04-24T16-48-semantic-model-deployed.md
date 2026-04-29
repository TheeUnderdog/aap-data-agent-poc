# Orchestration Log: Fabric Semantic Model Deployed — AAP Rewards Loyalty Model

**Date:** 2026-04-24T16:48:00Z  
**Owner:** Coordinator  
**Status:** Completed  

---

## Executive Summary

Successfully deployed the Fabric semantic model **"AAP Rewards Loyalty Model"** to the workspace via REST API. The model sources 10 Delta tables from the dbo schema, defines 7 relationships, and includes 16 DAX measures covering revenue, member counts, loyalty points, coupons, fraud detection, and business KPIs. Three TMDL format issues were identified and corrected during deployment—all fixed and documented for future reference.

---

## Deployment Details

### Semantic Model: AAP Rewards Loyalty Model

**Source:** 10 Delta tables (dbo schema)
1. dbo.members
2. dbo.transactions
3. dbo.rewards_catalog
4. dbo.loyalty_program_tiers
5. dbo.member_engagement
6. dbo.csr (Customer Service Representatives)
7. dbo.csr_activities
8. dbo.fraud_incidents
9. dbo.system_metadata
10. dbo.external_enrichment

**Relationships (7):**
1. members ← transactions (many-to-one: member_id)
2. transactions ← rewards_catalog (many-to-one: reward_id)
3. members ← loyalty_program_tiers (many-to-one: tier_id)
4. transactions ← csr (many-to-one: csr_id)
5. csr ← csr_activities (one-to-many: csr_id)
6. transactions ← fraud_incidents (one-to-one: transaction_id)
7. members ← member_engagement (one-to-one: member_id)

**DAX Measures (16):**
1. Total Members
2. Active Members (last 90 days)
3. Total Transactions
4. Total Revenue
5. Average Transaction Value
6. Total Points Earned
7. Total Points Redeemed
8. Points Pending
9. Customer Retention Rate
10. Tier Migration Rate
11. Fraud Incident Count
12. Fraud Detection Rate
13. Average CSR Case Resolution Time
14. CSR Activity Volume
15. Member Lifetime Value
16. Program ROI

---

## TMDL Format Issues Identified & Fixed

### Issue 1: Missing `definition.pbism` File
**Problem:** Initial TMDL generation lacked the required `definition.pbism` file (semantic model metadata file).  
**Fix:** Generated `definition.pbism` with Fabric REST API v1 semantic model schema.  
**Lesson:** Always verify TMDL structure includes both `.tmdl` table/measure definitions and `definition.pbism` metadata file.

### Issue 2: Incorrect pbism Schema Version
**Problem:** Early `definition.pbism` files used incorrect schema version (not `5.0`).  
**Fix:** Updated to schema version `5.0` with correct `$schema` URL: `https://powerbi.microsoft.com/schema/semantic-model/definition/5.0/semantic-model-definition.json`  
**Lesson:** Fabric semantic model TMDL requires `version: "5.0"` in pbism. Schema URL must match the version.

### Issue 3: Unsupported Properties at Table Level
**Problem:** TMDL definition included `description` and `lineageTag` properties at the table level, which TMDL does not support (only at column/measure level).  
**Fix:** Removed unsupported properties from table-level definitions. Kept descriptions at column and measure level only.  
**Lesson:** TMDL supports `description` and `lineageTag` at column and measure levels, NOT at table level. Partition source syntax uses `source =` (not `expression:`).

---

## Deployment Process

### REST API Calls
- **Endpoint:** `api.fabric.microsoft.com/v1`
- **Method:** POST to semantic model creation endpoint
- **Authentication:** Azure CLI service principal token
- **Operation Type:** Long-running operation (LRO)

### Validation Steps
✅ All 10 Delta tables successfully referenced  
✅ All 7 relationships properly defined  
✅ All 16 DAX measures compiled without errors  
✅ Semantic model workspace item created  
✅ REST API long-running operation completed successfully  

---

## Dependencies & Impact

### Data Agent (Phase 3)
- **Status:** Ready to proceed
- **Query Layer:** Fabric Data Agent now queries the semantic model directly
- **No changes needed:** All DAX measures available for agent queries

### Power BI Reports
- **Status:** Can reference semantic model (deferred per directive)
- **Connection:** Power BI Desktop can connect to workspace semantic model
- **Measures:** All 16 DAX measures available for visualization

### Downstream Systems
- Web app can query Data Agent (which queries semantic model)
- All visualizations and reports source from this central model
- Single point of truth for all business metrics

---

## Coordination Notes

**Key Learnings:**
1. TMDL is stricter than Power BI datasets about property support—test schema thoroughly
2. Table-level descriptions are not supported in TMDL; move to column descriptions
3. Schema version (`5.0`) and `$schema` URL must be in sync
4. Partition source syntax: always use `source =`, never `expression:`

**Team Awareness:**
- Livingston: Semantic model now live; SQL views are archived
- Basher: Data Agent configuration can reference this semantic model directly
- Frontend Dev: Web app ready to connect through mock or real agent
- Coordinator: Deployment complete; all TMDL format lessons documented

**Next Steps:**
1. ✅ Semantic model deployed and validated
2. → Begin Phase 3: Configure Fabric Data Agent to query semantic model
3. → Test Data Agent query accuracy against semantic model measures
4. → Validate web app integration with Data Agent
5. → Deferred: Power BI report authoring (pending Data Agent validation)

---

## Artifacts & Documentation

- **Semantic Model:** "AAP Rewards Loyalty Model" (workspace item)
- **TMDL Files:** `.squad/tmdl/` (definition.pbism + table definitions)
- **Measures:** All 16 DAX expressions compiled and deployed
- **Test Queries:** Can be executed against semantic model in Fabric portal
