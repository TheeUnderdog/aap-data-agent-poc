# Rusty — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** pytest, Playwright, httpx
- **Key requirement:** Validate that schema abstraction works — tests should pass regardless of which data schema is loaded. Sample query set from customer will be the acceptance criteria.
- **Customer context:** POC must be demo-ready for Advanced Auto Parts marketing team.

## Learnings

### Pre-Deployment Review (2026-04-27)
- **Context**: Cross-cutting integration review of all deployment artifacts before deploying to Fabric workspace 82f53636-206f-4825-821b-bdaa8e089893
- **Findings**: 
  - ✅ Notebook → SQL Views schema consistency: All table and column references match correctly
  - ✅ SQL Views → Sample Queries consistency: All view and column references are correct
  - ✅ Scripts → .env.fabric consistency: File format and key names match
  - ✅ Deployment order: README instructions match script dependencies
  - ✅ .gitignore: .env.fabric properly excluded
  - 🟡 **Minor issue found**: SQL verification query (line 343) has copy/paste error in comment - says "v_transaction_history" but should reference "v_points_activity" (cosmetic only, in commented-out code)
- **Schema validation**:
  - Notebook creates 10 tables in `mirrored` schema with correct column types
  - Views reference all correct table/column names from mirrored schema
  - Sample queries reference all correct view/column names from semantic schema
  - View count: 9 views (v_member_summary, v_transaction_history, v_points_activity, v_coupon_activity, v_store_performance, v_product_popularity, v_member_engagement, v_campaign_effectiveness, v_audit_trail)
- **Integration points validated**:
  - setup-workspace.ps1 outputs: FABRIC_WORKSPACE_ID, FABRIC_WORKSPACE_NAME, FABRIC_LAKEHOUSE_ID, FABRIC_LAKEHOUSE_NAME, FABRIC_SQL_ENDPOINT, FABRIC_CAPACITY_ID
  - deploy-semantic-views.ps1 reads: FABRIC_SQL_ENDPOINT, FABRIC_LAKEHOUSE_NAME (both present in output)
  - Deployment sequence correct: setup-workspace → import/run notebook → deploy-semantic-views
- **Recommendation**: Deployment-ready with one cosmetic fix optional (commented code typo)
