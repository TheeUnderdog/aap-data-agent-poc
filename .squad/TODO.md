# Squad TODO

> AAP Data Agent POC — remaining work items, organized by owner.

## Deployment Pipeline (Fabric)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 1 | Sample data notebook | Saul | Done | 10 Delta tables, ~2.8M rows loaded |
| 2 | Semantic views | Saul | Done | 10 views deployed via deploy-semantic-views.ps1 |
| 3 | Semantic model (DirectLake) | Saul | Pending | Run scripts/create-semantic-model.py — check ENTRA_TENANT_ID |
| 4 | Linguistic schema | Saul | Pending | Run scripts/configure-linguistic-schema.py — 169 synonyms |
| 5 | SP workspace access | Basher | Pending | Add SP 176f52b8 as Contributor to AAP-RewardsLoyalty-POC workspace |
| 6 | Data Agent configuration | Dave | Pending | Manual — 5 agents in Fabric portal (~5 min), import instructions + examples.json |

## Web App

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 7 | Documentation page | Linus | In Progress | web/docs.html exists — needs content for all 3 audience sections |
| 8 | Docs nav icon | Linus | Pending | Book icon in top-bar-right, opens docs.html in new tab |
| 9 | Screenshot capture | Linus | Pending | Browser automation to fill placeholder img tags in docs.html |
| 10 | Local dev test | Basher | Pending | Verify server.py + config.js work end-to-end with Fabric agents |
| 11 | Docker build + test | Basher | Pending | docker-compose up, verify auth and SSE streaming |

## Azure Deployment

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 12 | Azure Container Apps deploy | Basher | Pending | Push image, configure env vars, verify health endpoint |
| 13 | Entra app registration | Basher | Pending | Redirect URIs for production domain |
| 14 | Azure Static Web Apps (if needed) | Basher | Pending | Alternative to Container Apps for SPA hosting |

## QA & Validation

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 15 | End-to-end smoke test | Rusty | Blocked | Blocked on items 3-6 (Fabric pipeline) |
| 16 | Agent response quality | Rusty | Blocked | Verify all 6 agents return meaningful answers |
| 17 | Crew Chief routing | Rusty | Blocked | Multi-agent fan-out and synthesis |
| 18 | Mobile responsive check | Rusty | Pending | Hamburger menu, agent sidebar |

## Docs & Housekeeping

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| 19 | Archive stale markdown | Scribe | Pending | Move build-plan.md, MANUAL_DEPLOYMENT_STEPS.md to docs/archive/ |
| 20 | Merge decision inbox | Scribe | Pending | 10 decisions in .squad/decisions/inbox/ need triage |
| 21 | Session log rollup | Scribe | Pending | Consolidate learnings from auth scrub, deployment sessions |

## Completed

| # | Task | Owner | Completed |
|---|------|-------|-----------|
| -- | Cross-tenant/OBO scrub | Basher | 19 files cleaned, all MSIT refs removed |
| -- | FDPO tenant consolidation | Danny | Single-tenant arch, all configs updated |
| -- | Sample data generation | Saul | Notebook ran successfully in Fabric |
| -- | Semantic views deployment | Saul | 10 views live on SQL endpoint |
| -- | Auth simplification | Basher | SP client_credentials, no OBO/delegated |
