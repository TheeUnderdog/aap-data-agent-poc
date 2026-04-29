# Orchestration Log: Architecture Pivot — Semantic Models Over SQL Views

**Date:** 2026-04-24T16:42:00Z  
**Owner:** Coordinator  
**Status:** Completed  

---

## Executive Summary

User corrected the architecture direction. The Fabric Data Agent consumes Fabric semantic models (workspace-level items), not SQL views. The `create-semantic-model.py` script was rewritten to source directly from 10 Delta tables (dbo schema) instead of 9 SQL views. This eliminates unnecessary middleware and aligns with Fabric best practices.

---

## What Changed

### Architecture Pivot
- **Old approach:** Delta tables → SQL views → Semantic model (optional) → Data Agent
- **New approach:** Delta tables → Semantic model → Data Agent

### The Error
Livingston initially discovered that SQL views do NOT appear as workspace-level items in Fabric. This led to creating a semantic model as a workaround layer. However, the semantic model should source directly from Delta tables, not from the SQL views.

### The Fix
Coordinator rewrote `scripts/create-semantic-model.py`:
- **Before:** Semantic model definition referenced 9 SQL views via the SQL Analytics Endpoint
- **After:** Semantic model definition references 10 Delta tables in dbo schema directly

**Delta tables sourced:**
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

---

## Semantic Model Definition

**Relationships (7 total):**
1. members ← transactions (many-to-one: member_id)
2. transactions ← rewards_catalog (many-to-one: reward_id)
3. members ← loyalty_program_tiers (many-to-one: tier_id)
4. transactions ← csr (many-to-one: csr_id)
5. csr ← csr_activities (one-to-many: csr_id)
6. transactions ← fraud_incidents (one-to-one: transaction_id)
7. members ← member_engagement (one-to-one: member_id)

**DAX Measures (16 total):**
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

## Obsolete Artifacts

The following scripts are now **obsolete** and should not be deployed:

1. **scripts/deploy-views.py** — Deploys SQL views to the SQL Analytics Endpoint. No longer needed since the semantic model sources Delta tables directly.
2. **scripts/create-semantic-views.sql** — Contains 9 view definitions. No longer part of the query abstraction.
3. **scripts/verify-views.py** — Validates SQL view existence. No longer needed for verification.

These can be archived or deleted. They were useful for understanding the SQL endpoint but do not fit the final architecture.

---

## Impact on Deployment

### Fabric Data Agent (Phase 3)
- **Status:** Ready to proceed
- **Dependency:** `scripts/create-semantic-model.py` must run successfully before Data Agent deployment
- **Query Layer:** Fabric Data Agent will query the semantic model (not SQL views)

### Power BI Authoring
- **Status:** Halted (per directive)
- **Rationale:** Power BI work deferred until Data Agent validation complete
- **Future Path:** Power BI can also query the semantic model if needed

### Validation
- Run `scripts/create-semantic-model.py --dry-run` to preview the semantic model TMSL definition
- Verify all 10 tables are referenced in the model
- Confirm all 7 relationships are properly defined
- Test 16 DAX measures in the Fabric portal

---

## Coordination Notes

**Key Decisions:**
- SQL views were a good learning exercise but not the right abstraction for Fabric
- Semantic models are the canonical Fabric query layer (like Power BI datasets)
- Direct Delta table sourcing is simpler and more maintainable than an intermediate SQL layer

**Team Awareness:**
- Livingston: SQL view work is now archived; focus shifts to semantic model validation
- Basher: Notebook deployment script still useful; no changes needed to `scripts/run-notebook.py`
- Coordinator: Document the decision in decisions.md and mark SQL view scripts as archived

**Next Steps:**
1. Verify `create-semantic-model.py` runs successfully
2. Deploy semantic model to Fabric workspace
3. Validate Data Agent can query the semantic model
4. Begin Phase 3 Data Agent development
