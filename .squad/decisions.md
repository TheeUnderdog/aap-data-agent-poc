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

### FABRIC_AUTH_MODE Implementation (2026-04-26)
- **Decision:** Added `FABRIC_AUTH_MODE` environment variable to control Fabric API authentication
- **Options:** `client_credentials` (default, cross-tenant) or `user_delegated` (same-tenant OBO)
- **Rationale:** Cross-tenant deployments need client_credentials; same-tenant customers can use user delegation
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### Fabric Provisioning Script Design (2026-04-25)
- **Decision:** Use Fabric REST API with Azure CLI token auth, idempotent semantics, `.env.fabric` config file
- **Implementation:** Two PowerShell scripts (setup-workspace.ps1, deploy-semantic-views.ps1), SqlClient fallback for SQL operations
- **Rationale:** Automation eliminates portal work, idempotency allows safe re-execution, config bridge enables multi-stage provisioning
- **Owner:** Basher (Backend Developer)
- **Status:** Implemented

### Container Apps Migration — Implementation Details (2026-04-26)
- **Decision:** Migrated from Azure Static Web Apps to Azure Container Apps
- **Key Choices:** Single-container deployment (Flask + gunicorn), MSAL middleware auth, gunicorn gthread worker for SSE, GitHub Container Registry (ghcr.io)
- **Rationale:** True SSE streaming (no 30-second cap), full auth control, container registry flexibility
- **Impact:** Same image runs locally (docker-compose) and in Azure; frontend code unchanged
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### Auth Simplification — DefaultAzureCredential (2026-07)
- **Decision:** Replace MSAL with stateless `DefaultAzureCredential` for all environments
- **Context:** App and agents will run in same FDPO tenant; local dev uses `az login`
- **Changes:** Removed MSAL, Flask sessions, auth routes; single `get_fabric_token()` using credential chain
- **Impact:** No app registration needed; Docker mounts `~/.azure` for local creds; Container Apps uses managed identity
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### Delegated User Auth (Cross-Tenant) (2026-07)
- **Decision:** Replace client_credentials with delegated user auth — forward user's own token to Fabric
- **Context:** New multi-tenant app reg in Contoso tenant accepts users from any Azure AD tenant
- **Flow:** User logs in via MSAL → gets Fabric token → stored in Flask session → forwarded to Fabric API
- **Impact:** Fabric checks user's workspace permissions (not SP); Linus frontend unchanged; deployed with multi-tenant app reg
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### MSAL Delegated Browser Auth — Restore (2026-07)
- **Decision:** Replace `DefaultAzureCredential` with MSAL authorization code flow (delegated browser auth)
- **Rationale:** Dave wants browser redirect with Microsoft credentials; delegated token carries user identity to Fabric
- **Architecture:** /auth/login → MSAL initiate_auth_code_flow → Microsoft login → /auth/callback → session → /api/chat
- **Impact:** Local dev still works via AzureCliCredential fallback; MSAL dependencies restored
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### ChainedTokenCredential Simplification (2026-07)
- **Decision:** Replace MSAL with simple ChainedTokenCredential (ManagedIdentityCredential → AzureCliCredential → DeviceCodeCredential)
- **Rationale:** Dave wants simplest possible auth — just use Azure credentials server-side
- **Consequences:** No app registration, no browser redirect, no Flask sessions; everyone shows as "Advance Insights User"
- **Docker support:** DeviceCodeCredential replaces `~/.azure` mount approach
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### Simplify Auth to Single-Tenant client_credentials (2025-07-17)
- **Decision:** Remove cross-tenant complexity — single-tenant FDPO client_credentials only
- **Context:** All resources live in FDPO tenant; removed `FABRIC_TENANT_ID`, `FABRIC_AUTH_MODE`, OBO flow
- **Auth model:** User login = identity only (openid+profile); Fabric = client_credentials only
- **Impact:** `.env.example` is simpler; no multi-tenant logic
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### SWA Deployment Scripts (2026-07)
- **Decision:** Created `scripts/deploy-web.ps1` (PowerShell) and `scripts/deploy-web.sh` (Bash) for Azure Static Web App automation
- **Rationale:** Manual portal deployment is error-prone; team needs repeatable deployment for dev/staging/prod
- **Features:** Dual-platform, idempotent, WhatIf/dry-run support, Entra ID automation
- **Owner:** Basher (Backend Dev)
- **Status:** Implemented

### Single PBIR Report for Verified Answers (2026-07)
- **Decision:** Created single-page `LoyaltyOverview` PBIR report with 8 visuals (not 5 full reports)
- **Rationale:** Dave requested "just one simple dashboard"; verified answers need report visuals as anchors; PBIR format enables git sync
- **Files:** `reports/LoyaltyOverview.Report/definition.pbir`, `report.json`, `README.md`
- **Owner:** Basher
- **Status:** Implemented

### Scrub Old Auth Model References from Documentation (2026-04-28)
- **Decision:** Remove all references to OBO, user-delegated, cross-tenant, trusted subsystem, old MSIT tenant IDs
- **Rationale:** Document what IS, not what ISN'T; stale references create confusion
- **Files Changed:** 10 files across docs, code, config
- **Owner:** Basher (Backend Dev)
- **Requested by:** Dave Grobleski
- **Status:** Implemented

### Migrate to Azure Container Apps from Static Web Apps (2026-07)
- **Decision:** Full migration from SWA to ACA for Flask-only local dev + public repo readiness
- **Rationale:** SWA is deprecated for POC, ACA offers better control, single Docker image, unlimited SSE streaming
- **Implementation:** MSAL middleware in Flask, gunicorn, Container Apps with managed identity, ghcr.io registry
- **Owner:** Danny (Lead/Architect)
- **Status:** Proposed, Basher implementing

### Docker Deployment Architecture (2026-04-26)
- **Decision:** Same Docker image runs identically in local development and Azure production with automatic auth fallback
- **Local Dev:** docker-compose mounts `~/.azure` for AzureCliCredential; option for mock agent
- **Azure Production:** MSAL auth code flow, managed identity for Fabric, Container Apps orchestration
- **Files:** `web/Dockerfile`, `docker-compose.yml`, `scripts/deploy-web.ps1`, `.github/workflows/azure-container-apps.yml`
- **Owner:** Danny (Lead/Architect)
- **Status:** ✅ Implemented

### Deployment Automation & Gaps Analysis (2026-07)
- **Decision:** Create `docs/deployment-gaps.md` (gap analysis) and `scripts/deploy-all.ps1` (master orchestrator script)
- **Rationale:** 70% of deployment automatable via REST APIs; 30% requires portal clicks; master script chains all subscripts
- **Impact:** Deployment time reduced from ~4 hours to ~1 hour total (3 min automated + 45–60 min manual)
- **Owner:** Danny (Lead/Architect)
- **Status:** Approved for Implementation

### Public Repository Preparation (2026-07)
- **Decision:** Prepare repo for public visibility by updating docs to reflect Flask-only local dev reality
- **Changes:** README.md rewrite (Flask not Container Apps, 6 agents not 5, ChainedTokenCredential auth), web/SETUP.md status callouts, MIT License
- **Rationale:** Public repos must accurately represent what works today; aspirational docs erode trust
- **Owner:** Danny (Lead/Architect)
- **Status:** Implemented

### Agent Configuration Verification (2026-04-26)
- **Decision:** All 5 AI agent configurations audited and verified
- **Rationale:** Ensure CSR naming convention and semantic view references are consistent across agent configs before Fabric Data Agent deployment
- **Findings:** 16 files audited (5 agents × 3 files + shared config), all SQL correct, zero legacy references
- **Owner:** Basher (Backend Dev)
- **Status:** Verified — No Issues Found

### Azure Static Web Apps Infrastructure (2026-07) → Azure Container Apps Migration (2026-04-26)
- **Original Decision:** Set up Azure Static Web Apps as hosting platform for AAP Data Agent POC web app
- **Rationale (SWA):** Simpler deployment than Container Apps, built-in Entra ID auth, auto-scaling, no Service Tree ID needed
- **Original Implementation:**
  - `web/staticwebapp.config.json` — SWA routing (API → managed Functions, static → SPA), Entra ID auth (MSIT tenant), security headers, role-based access
  - `api/function_app.py` — Python v2 Azure Functions backend (3 endpoints: `/api/chat` SSE proxy, `/api/user` identity, `/api/health`)
  - `.github/workflows/azure-static-web-apps.yml` — GitHub Actions CI/CD (SPA + managed Functions deployment)
  - `web/SETUP.md` — Complete setup guide (portal creation, Entra ID app registration, managed identity binding, auth flow)
  - Updated `web/config.js` — `useProxy: true` works for both local `web/server.py` and SWA managed Functions
- **Migration Decision:** Replace SWA with Azure Container Apps (2026-04-26)
- **Rationale for Migration:**
  - Functions Consumption tier caps SSE streaming at ~30 seconds → limits real-time chat
  - Manual managed identity binding on each deploy
  - Limited control over auth flow and runtime
  - Container Apps provides full control, flexible registry options, unlimited SSE streaming
- **New Implementation (Container Apps):**
  - `web/Dockerfile` — Multi-stage build (Flask + gunicorn application server)
  - `web/requirements.txt` — Python dependencies (flask, gunicorn, msal, requests)
  - `web/server.py` — Flask backend with MSAL auth middleware, Entra ID integration, `/api/chat` SSE endpoint
  - `.github/workflows/azure-container-apps.yml` — GitHub Actions CI/CD (build, push to ghcr.io, deploy to ACA)
  - `scripts/deploy-web.ps1` — PowerShell idempotent Container Apps deployment
  - `scripts/deploy-web.sh` — Bash parallel deployment script
  - Deleted: `web/staticwebapp.config.json`, `.github/workflows/azure-static-web-apps.yml`
- **Team Impact (Same):**
  - **Linus:** Frontend code unchanged — `useProxy: true` + relative URLs work with Container Apps backend
  - **Livingston:** No data layer changes — Fabric API via managed identity (workspace Contributor role)
  - **Danny:** Aligns with original decision #4 but with enhanced capabilities
- **Key Improvements:**
  - ✅ True SSE streaming (unlimited, no 30-second cap)
  - ✅ Full Entra ID auth control via MSAL middleware
  - ✅ Container registry flexibility (ghcr.io, ACR, Docker Hub)
  - ✅ Managed identity environment-based (no secrets in code)
  - ✅ Production-grade container orchestration
- **Owner:** Basher (Backend Dev)
- **Status:** ✅ Implemented (Commit 7155a0b), Ready for Container Apps provisioning

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
