# Squad Decisions

## Active Decisions

### Schema Abstraction (2026-04-23)
- **Decision:** Implement view-based contract layer for schema independence
- **Rationale:** Enables seamless replacement of placeholder schema with production schema without code changes
- **Implementation:** All components query semantic views, not raw tables
- **Owner:** Danny (Architecture), Livingston (Schema Design)
- **Status:** Approved & Documented in architecture.md and data-schema.md

### Architectural Decisions for AAP Data Agent POC (2026-04-23)
- **Decisions:**
  1. Use Lakehouse (not Warehouse) for mirrored data — Native mirroring integration, Delta Lake schema evolution, cost efficient
  2. Semantic views as contract layer — Isolates schema changes, zero code impact, single point of update
  3. Service principal for Fabric API access — Simplified security model, consistent behavior, easier audit
  4. Static Web Apps + managed Functions — Single deployment, auto-CORS, cost efficient, sufficient for POC
  5. Data Agent config in source control — Version control, repeatability, disaster recovery
  6. Return generated SQL to user — Transparency, debugging, trust, compliance
  7. Generate placeholder data — Testing, demo value, performance validation
  8. Entra ID SSO authentication — Existing identity infrastructure, security, compliance
- **Owner:** Danny (Lead/Architect)
- **Status:** Approved for Implementation

### Executive Overview Document (2026-04-24)
- **Decision:** Create `docs/overview.md` as primary executive summary for AAP Data Agent POC
- **Rationale:** Dual audience (AAP business/technical stakeholders, Microsoft field team) needs accessible 2–3 page summary explaining opportunity, four-phase approach, schema abstraction strategy, prerequisites, risks, and success criteria
- **Content:** 1,200-word document synthesizing technical architecture into business-friendly narrative with ASCII flow diagram, prerequisite checklist, risk register, and cross-references
- **Owner:** Danny (Lead/Architect)
- **Status:** Delivered & Ready for Stakeholder Review

### Placeholder Schema with View-Based Abstraction (2026-04-23)
- **Decision:** Implement view-based abstraction layer as schema contract with 9-table placeholder design
- **Rationale:** Enables zero-code schema swap when production data arrives; all consuming components (Fabric Data Agent, Backend API, Web App, Power BI) depend on stable view interfaces
- **Implementation:** 7 contract views provide stable query surfaces; documented 7-step swap procedure
- **Owner:** Livingston (Data Engineer)
- **Status:** Implemented

### Two-Phase Build Strategy + Semantic Model Approach (2026-04-25)
- **Decision:** Split all work into Phase A (build locally, no AAP access) and Phase B (deploy to AAP environment)
- **Rationale:** AAP access timeline uncertain — team shouldn't be blocked. All scripts, code, configs written and tested without target environment. Phase A produces demos (mock data) to build AAP confidence. Phase B becomes scripted deployment measured in hours.
- **Impact:** Team sprint plan follows Phase A (weeks 1–3) then Phase B (weeks 4–5). All agents begin work immediately.
- **Owner:** Danny (Lead/Architect)
- **Status:** Approved & Documented in build-plan.md

### Semantic Views Deployed to Fabric (2026-04-24)
- **Decision:** Deploy all 9 semantic contract views to Fabric Lakehouse SQL endpoint
- **Rationale:** Live views enable Data Agent configuration, TMDL authoring, and sample query validation
- **Implementation:** Fixed deploy-views.py parser bug (comment filter was too strict), deployed schema + 9 views
- **Outcome:** All views live and queryable; foundation ready for Phase B AAP deployment
- **Owner:** Livingston (Data Engineer)
- **Status:** Completed & Live

### Semantic Model + Data Agent (Both)
- **Decision:** Build both a Power BI semantic model AND configure the Fabric Data Agent. Recommend Data Agent queries through semantic model.
- **Rationale:** AAP is heavy PBI user — semantic model immediately valuable. Data Agent accuracy may need tuning; semantic model is safety net. Data Agent querying through semantic model gets better results on calculated measures. Maximum demo value.
- **Impact:** Data Engineer authors TMDL definition in Phase A. Adds ~1 day work but significantly de-risks POC.
- **Owner:** Danny (Lead/Architect)
- **Status:** Approved & Documented in build-plan.md

### Web App Develops Against Mock Agent
- **Decision:** Frontend and backend develop against local mock of Data Agent API during Phase A
- **Rationale:** Web app fully functional and testable before Fabric access. Mock returns realistic responses. Switch mock→real agent = configuration change only.
- **Impact:** Frontend Developer unblocked from day 1. No dependency on Fabric environment for app development.
- **Owner:** Danny (Lead/Architect)
- **Status:** Approved & Documented in build-plan.md

### Fabric Provisioning Script Design (2026-04-25)
- **Decision:** Provisioning scripts use Fabric REST API (`api.fabric.microsoft.com/v1`) with Azure CLI token auth, idempotent create-or-reuse semantics, and output a shared `.env.fabric` config file
- **Rationale:** Automation eliminates manual portal clicking. Idempotent semantics allow safe re-execution. Config bridge enables multi-stage provisioning with clear ownership boundaries
- **Implementation:** Two PowerShell scripts: setup-workspace.ps1 (creates workspace/lakehouse), deploy-semantic-views.ps1 (executes SQL views). SqlClient fallback removes hard dependency on SqlServer module. `.env.fabric` in .gitignore keeps secrets local
- **Owner:** Basher (Backend Developer)
- **Status:** Implemented

### Delta Sample Schema Design (2026-04-23)
- **Decision:** Implement 10-table Delta schema with 9 semantic views as contract layer
- **Rationale:** Stores table enables store-level analytics (key Data Agent use case). Coupon rules separated for campaign effectiveness analysis. Added v_coupon_activity, v_campaign_effectiveness, v_audit_trail views. T-SQL syntax for Fabric Lakehouse SQL endpoint compatibility
- **Implementation:** Mirrored schema reserved for mirror output; applications query views only. 337K rows with realistic distributions. Date range 2025-01-01 through 2026-04-23 enables full year of testing
- **Owner:** Livingston (Data Engineer)
- **Status:** Implemented

### User Directive: Phased Build Approach (2026-04-23)
- **Decision:** Do not start web app yet. Focus on Fabric environment + sample schema with Delta data first, then Data Agent, then web app later
- **Rationale:** User direction from Dave Grobleski — phased build approach reduces complexity and enables early validation
- **Impact:** Team prioritizes infrastructure and schema validation in Phase A; web app deferred to later phase
- **Owner:** Dave Grobleski
- **Status:** Documented for Team Memory

### Agent Configuration Verification (2026-04-26)
- **Decision:** All 5 AI agent configurations audited and verified
- **Rationale:** Ensure CSR naming convention and semantic view references are consistent across agent configs before Fabric Data Agent deployment
- **Findings:** 16 files audited (5 agents × 3 files + shared config), all SQL correct, zero legacy references
- **Owner:** Basher (Backend Dev)
- **Status:** Verified — No Issues Found

### Azure Static Web Apps Infrastructure (2026-07)
- **Decision:** Set up Azure Static Web Apps as hosting platform for AAP Data Agent POC web app
- **Rationale:** Simpler deployment than Container Apps, built-in Entra ID auth, auto-scaling, no Service Tree ID needed
- **Implementation:**
  - `web/staticwebapp.config.json` — SWA routing (API → managed Functions, static → SPA), Entra ID auth (MSIT tenant), security headers, role-based access
  - `api/function_app.py` — Python v2 Azure Functions backend (3 endpoints: `/api/chat` SSE proxy, `/api/user` identity, `/api/health`)
  - `.github/workflows/azure-static-web-apps.yml` — GitHub Actions CI/CD (SPA + managed Functions deployment)
  - `web/SETUP.md` — Complete setup guide (portal creation, Entra ID app registration, managed identity binding, auth flow)
  - Updated `web/config.js` — `useProxy: true` works for both local `web/server.py` and SWA managed Functions
- **Team Impact:**
  - **Linus:** Frontend code unchanged — `useProxy: true` + relative URLs work in both local and prod
  - **Livingston:** No data layer changes — Fabric API via managed identity (needs workspace Contributor)
  - **Danny:** Aligns with decision #4 (Static Web Apps + managed Functions)
- **Known limitation:** Functions v2 Consumption doesn't support true SSE streaming. Chat responses accumulated and returned as batch. Acceptable for POC; upgrade to Flex Consumption if real-time streaming needed.
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### Crew Chief Executive Orchestrator Naming (2026-04-24)
- **Decision:** The executive orchestrator agent in the web UX is named "Crew Chief" (not "The Boss")
- **Rationale:** User direction (Dave) — keeps auto racing theme consistent with other agents (Pit Crew, GearUp, Ignition, PartsPro, DieHard)
- **Scope:** UX branding for AAP Data Agent POC chatbot
- **Owner:** Dave Grobleski (User)
- **Status:** Documented for Team Memory

### Schema Documentation Must Match Implementation (2026-04-25)
- **Decision:** Implementation is the source of truth; documentation follows implementation
- **Problem:** `docs/data-schema.md` was written as design spec before data generation notebook. When implementation diverged (different table names, column names, structures), stale docs misled consuming code (semantic model had fabricated schemas)
- **Hard rules:**
  1. Never write consuming code from design specs — always verify against actual data source (notebook, Lakehouse, DB DDL)
  2. Update design docs immediately after implementation — if they diverge, document both and explain why
  3. Add schema gap analysis sections comparing planned vs. built
  4. Before writing any schema-dependent code (semantic models, Data Agent, API queries), verify all table/column names and types against source of truth
- **Implementation:** Reconciled `docs/data-schema.md` to match `notebooks/01-create-sample-data.py` schemas, updated all sample queries, documented design vs. reality gaps
- **Impact:** Prevents future schema-based errors; establishes "code is truth" culture
- **Owner:** Saul (Data Engineer)
- **Status:** Implemented

### Lakehouse Context Auto-Detection in Notebooks (2026-07)
- **Decision:** All Fabric notebooks using `saveAsTable()` with unqualified names MUST include context-detection cell
- **Problem:** Notebooks uploaded via REST API have phantom lakehouse binding (UI shows it, Spark runtime doesn't activate context) → `saveAsTable()` fails with "No default context found"
- **Solution:** Context-detection cell that checks if `spark.catalog.currentDatabase()` is bound, auto-discovers available lakehouse if not, fails clearly if none available
- **Rationale:** API upload creates phantom binding. Manual workaround (portal detach/reattach) is fragile. Auto-detection is safe and only runs if context not already set.
- **Impact:** `notebooks/01-create-sample-data.py` updated with Section 0 context cell; any future write-Delta notebooks should use same pattern
- **Owner:** Saul (Data Engineer)
- **Status:** Implemented

### Semantic Model Schema Alignment (2026-04-24)
- **Decision:** Rewrite semantic model script to match actual Delta table schemas from notebook
- **Problem:** Script had fabricated table/column names that didn't match `notebooks/01-create-sample-data.py`
- **Root Cause:** Livingston referenced design docs instead of authoritative notebook source
- **Key Fixes:**
  - Table names: `products` → `sku_reference`, `points_ledger` → `member_points`, removed `audit_log`, added `transaction_items`
  - Column names: `list_price` → `unit_price`, `rule_id` → `coupon_rule_id`, `csr_status` → `is_active`, removed non-existent balance columns
  - Data types: ALL ID columns int64, not string
  - DAX measures: Fixed references, removed 3 that referenced non-existent columns, added 6 new measures
- **Hard Rule:** NEVER fabricate schemas. Verify EVERY table/column/type against actual notebook or live Lakehouse
- **Verification:** Test with DirectLake refresh; if it fails, schema doesn't match reality
- **Status:** ✅ Implemented — Saul verified against notebook
- **Owner:** Saul (Data Engineer)

### Legacy Table Cleanup & Refresh Fix (2026-07-22)
- **Decision 1:** Use OneLake DFS API to delete stale `agents` and `agent_activities` tables (SQL endpoint doesn't support DROP)
- **Decision 2:** OAuth2 credential binding for DirectLake models is portal-only for first bind (Fabric Connections API limitation)
- **Impact:** First-time OAuth2 setup manual; subsequent refreshes work via API. Script: `scripts/drop-legacy-tables.py`, `scripts/bind-model-credentials.py`
- **Owner:** Livingston (Data Engineer)
- **Status:** ✅ Complete (Task 1), ⚠️ Requires manual portal (Task 2)

### Phase A Deployment Completion — April 2026 (2026-04-24)
- **Status:** Partially complete — 8 of 11 automated steps done
- **Completed:** Infrastructure, schema layer (9 views), semantic model (10 tables, 34 DAX measures), credential binding, linguistic schema (50 table synonyms, 66 column synonyms, 53 value synonyms, 53 AI instructions), 5 agent configs ready
- **Blocked Tasks:** (1) Sample data notebook execution failed (Spark error), (2) Semantic model refresh awaiting data, (3) Fabric Data Agent import is portal-only
- **Manual Work Remaining:** Debug notebook (~30–60 min), refresh model (5 min), import 5 agent configs (20–30 min) — ~1–2 hours total
- **Key Lessons:** Notebook REST API lacks detailed errors; Data Agent deployment is portal-only; Linguistic schema deployment robust; ~20% manual portal work is expected for Fabric POCs
- **Owner:** Livingston (Data Engineer)
- **Status:** Documented for team; awaiting Dave's manual portal actions
- **By:** Dave Grobleski (via Copilot)
- **Decision:** Stop work on Power BI reports. PBI is deprioritized/on hold.
- **Rationale:** User request — captured for team memory
- **Status:** Documented for Team Memory

### Semantic Model Deployment & TMDL Format Lessons (2026-04-24T16:48)
- **Decision:** Deploy Fabric semantic model "AAP Rewards Loyalty Model" via REST API with 10 Delta tables, 7 relationships, and 16 DAX measures
- **Implementation:** Coordinator deployed model sourcing dbo schema directly. Three TMDL format issues identified and resolved: (1) missing definition.pbism file, (2) incorrect pbism schema version (corrected to 5.0), (3) unsupported description/lineageTag at table level (removed—only support at column/measure level)
- **Lessons Learned:** TMDL structure requires both definition.pbism and table definitions; schema version must match $schema URL; partition syntax uses `source =` not `expression:`; description/lineageTag supported only at column/measure level, not table level
- **Status:** ✅ Deployed & Validated. All 10 tables, 7 relationships, 16 measures compiled successfully. Ready for Phase 3 Data Agent configuration.
- **Owner:** Coordinator (Deployment), Livingston (Schema Design), Scribe (Documentation)

### Semantic Model Credential Binding (2026-04-24T17:56)
- **Decision:** All semantic model deployments must include a post-deploy credential binding step
- **Problem:** TMDL-deployed models have no credentials bound to data sources → refresh fails with authentication error
- **Solution:** Two-step pattern: (1) Call Power BI REST API `Default.TakeOver` to bind deploying user's OAuth2 credentials, (2) Optionally patch each datasource with explicit OAuth2 credential type, (3) Trigger initial refresh
- **Implementation:** 
  - `scripts/bind-model-credentials.py` — standalone script for existing models
  - `scripts/create-semantic-model.py` — now auto-runs bind+refresh as post-deploy step
- **Impact:** Future redeploys will automatically bind credentials (no manual portal fix needed). Requires two API token scopes: Fabric API + Power BI API. Deploying user must have workspace admin/dataset ownership rights.
- **Owner:** Livingston (Data Engineer)
- **Status:** ✅ Implemented — Phase 2 deployment scripts ready

### Delta overwriteSchema Required on All saveAsTable Calls (2026-07)
- **Decision:** All `saveAsTable()` calls in Fabric notebooks that regenerate data from scratch MUST include `.option("overwriteSchema", "true")`
- **Pattern:**
  ```python
  df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("tablename")
  ```
- **Rationale:** Notebooks should be idempotent — safe to re-run at any time. Delta's `mode("overwrite")` preserves schema by default; without this option, column additions/removals require manual table cleanup
- **Impact:** 
  - `notebooks/01-create-sample-data.py` — All 10 tables updated
  - Any future write-Delta notebooks should follow the same pattern
  - Enables safe schema evolution during POC development
- **Owner:** Saul (Data Engineer)
- **Status:** ✅ Implemented

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
