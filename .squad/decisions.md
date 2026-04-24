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

### Power BI Report Specification Complete (2026-07)
- **Decision:** Comprehensive Power BI report specification document created for 5-report portfolio
- **Rationale:** 5-report portfolio approved conceptually but lacked implementation specs; developers need detailed guidance on layouts, DAX, visuals, filters, colors, and performance
- **Scope:** 5 reports, 46+ visuals, 36 DAX measures, all 9 semantic views covered, implementation checklist
- **Impact:** Developers can build without ambiguity; consistent styling across reports; scope protection against creep
- **Owner:** Danny (Lead/Architect)
- **Status:** Active / Ready for Implementation

### User Directive: Stop Power BI Report Work (2026-04-24T16:32)
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

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
