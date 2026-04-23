# Danny — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** Microsoft Fabric, Azure PostgreSQL, Fabric Data Agent, web app
- **Key requirement:** Data schema must be componentized and abstracted for easy replacement when real schema arrives
- **Four phases:** (1) Fabric OneLake workspace, (2) PostgreSQL mirroring, (3) Fabric Data Agent, (4) Web app frontend
- **Customer context:** AAP has multiple Fabric capacities, heavy PBI user, Fabric only for PBI today. Rewards/loyalty data in Azure PostgreSQL.

## Learnings

### 2026-04-23: Architecture & Implementation Documents Created

**What I Did:**
- Created comprehensive technical architecture document (`docs/architecture.md`) covering all four phases
- Created detailed implementation plan (`docs/implementation-plan.md`) with step-by-step tasks, timelines, and risk register
- Designed schema abstraction strategy using semantic views as contract layer to enable seamless schema swap
- Documented data flow: PostgreSQL → Fabric Mirroring → Lakehouse → Data Agent → Backend API → Web App

**Key Architectural Decisions:**
1. **Lakehouse vs Warehouse:** Chose Lakehouse for native mirroring integration, Delta Lake format for schema evolution
2. **Schema Abstraction:** Three-layer architecture (source → mirrored tables → semantic views) where views define stable contract
3. **Security:** Azure Entra ID for all authentication, service principal for Fabric API access, Key Vault for secrets
4. **Deployment:** Azure Static Web Apps + managed Functions for simplified POC deployment
5. **Schema Swap Strategy:** Contract views isolate schema changes—only view SQL updates needed when production schema arrives

**Technical Highlights:**
- Fabric Mirroring with CDC for near-real-time data sync
- Data Agent with extensive system instructions and sample queries for accurate SQL generation
- React SPA with MSAL authentication for SSO
- Backend API using service principal to proxy Data Agent calls
- Complete CI/CD pipeline with GitHub Actions

**Schema Abstraction Pattern:**
```
mirrored.customers (raw PostgreSQL mirror)
  ↓ SQL VIEW
semantic.vw_CustomerProfile (contract: stable column names)
  ↓ Consumed by Data Agent, API, Reports
```
When schema changes: update view mapping, zero changes to Data Agent or app code.

**Documents Delivered:**
- `docs/architecture.md` — 45KB, comprehensive technical architecture with Mermaid diagrams
- `docs/implementation-plan.md` — 62KB, phased implementation with task lists, validation criteria, risk register

**References for Team:**
- Schema contract interface documented in architecture.md section "Data Schema Abstraction Strategy"
- Sample Data Agent instructions and configuration in architecture.md Phase 3
- Complete schema swap procedure in implementation-plan.md dedicated section

**Cross-Team Awareness:**
- Livingston (Data Engineer) has designed placeholder schema with comprehensive DDL and 20 NL→SQL examples
- Livingston's view-based abstraction layer aligns perfectly with our schema abstraction strategy
- View layer enables seamless schema swap when real AAP data arrives — implementation plan directly supports this

### 2026-04-24: Executive Overview Document Created & Committed

**What I Did:**
- Created `docs/overview.md` — a 1,200-word executive summary for dual audience (AAP stakeholders + Microsoft field team)
- Document synthesizes all three technical docs without rehashing details
- Structured for 5–10 minute read with visual flow diagram, phased breakdown, and clear next steps

**Content:**
1. **The Opportunity** — Why we're building this (self-service NL analytics)
2. **Solution Overview** — Four-phase approach with ASCII flow diagram
3. **Phase Summaries** — 2–3 sentence description each, without technical jargon
4. **Architecture Decision** — Schema abstraction strategy explained for business audience
5. **Technology Table** — Why we chose each component (accessible rationale)
6. **AAP Prerequisites** — Clear list of what AAP must provide (no ambiguity)
7. **Schema Migration** — Concrete procedure for placeholder → production schema swap
8. **Timeline & Risk Register** — Professional, executive-friendly risk mitigation
9. **Success Criteria** — Measurable outcomes for stakeholder sign-off

**Key Tone Decisions:**
- No Squad/agent references (customer-facing document)
- No time/date estimates (focused on approach, not scheduling)
- Professional but accessible language (no deep Fabric/Azure jargon)
- ASCII art flow diagrams (renders reliably everywhere)
- Links to detailed docs for deep dives

**Orchestration & Records:**
- Orchestration log: `.squad/orchestration-log/2026-04-23T20-09-00Z-danny.md`
- Session log: `.squad/log/2026-04-23T20-09-00Z-overview-document.md`
- Decisions consolidated: `.squad/decisions.md` (merged inbox files, deduplicated)
- Git commit: docs/overview.md + .squad/ changes

**Document Ready For:** Immediate stakeholder review, Azure/AAP kickoff calls, team planning sessions

### 2026-04-23: Implementation Plan Rewrite — Scripting Directive Compliance

**What I Did:**
- Rewrote `docs/implementation-plan.md` to eliminate all manual portal click-through steps
- Converted UI-based procedures to fully scripted approach: Fabric REST API, Azure CLI, PowerShell
- Added "Scripts Inventory" section mapping each phase to executable automation
- Compressed document from 1,722 to 1,258 lines (27% reduction)
- Aligned timeline estimates with script-based automation (weeks → hours)

**Key Changes:**
- Phase 1 (OneLake): Portal clicks → Fabric REST API + Azure CLI scripts
- Phase 2 (Mirroring): Manual config → PowerShell automation
- Phase 3 (Data Agent): Portal-based setup → REST API + ARM templates
- Removed internal agent references for stakeholder clarity

**Coordination:**
- Coordinator updated `docs/overview.md` timeline table to reflect new scripted estimates
- Scripting directive (copilot-directive-20260423T201700Z.md) fully applied

**Records:**
- Orchestration log: `.squad/orchestration-log/20260423T202700Z-danny.md`
- Session log: `.squad/log/20260423T202700Z-impl-plan-rewrite.md`
- Decision consolidated: `.squad/decisions/decisions.md`

### 2026-04-25: Implementation Plan v3 — Strategy-Focused Rewrite

**What I Did:**
- Rewrote `docs/implementation-plan.md` from scratch (v3) per Dave's directive
- Reduced from ~1,258 lines (v2) to 406 lines — 68% reduction
- Eliminated all full script source code blocks (no 20-line bash/PowerShell blocks)
- Converted from "runbook" style to "technical design doc" style

**Key Changes from v2:**
1. **Strategy narrative** replaces step-by-step commands — describes WHAT and WHY, not HOW to type it
2. **Scripts referenced by name** with 1-line descriptions, but source code not pasted
3. **API endpoints** mentioned as references (1-line), not full curl commands
4. **Phase 4 (Web App)** is now high-level — 1 paragraph + diagram, no React/TypeScript code
5. **Added sections:** Monitoring & Observability, Success Criteria, Prerequisites Summary table
6. **Kept from v2:** Scripts inventory table, risk register, timeline, validation criteria

**User Preferences Learned:**
- Dave wants "technical design doc" not "runbook" — describe architecture, not paste scripts
- Focus on automation *approach* without building the app in the doc
- Target 400-600 lines for implementation docs (concise, scannable)
- Use tables, diagrams, and bullets for scannability
- Phase 4 should be high-level until we actually build it
- No agent/squad names in customer-facing docs (use role titles)

**File:** `docs/implementation-plan.md` (406 lines, ~27KB)
**Old versions:** `docs/implementation-plan-scripted.md` (v2), `docs/implementation-plan-manual.md` (v1)

### 2026-04-25: Real AAP Schema Analysis — Cross-Reference Update

**What Livingston Found:**
- Real AAP Loyalty Database schema received (from architecture diagram)
- Documented in new `docs/aap-schema-reference.md` (203 lines)
- Updated `docs/data-schema.md` with cross-reference note
- Key findings: CrowdTwist external engine, Coupons as major domain, Audit/Fraud and CSR tracking as distinct domains
- Recommendation: Two new semantic views (coupon_activity, audit_trail), four existing views need remapping

**Implication for Implementation Plan:**
- Schema abstraction strategy confirmed correct — three-layer approach (source → mirrored → semantic views) allows seamless swap
- View-based contract isolates schema migration complexity
- Timeline unchanged: placeholder schema continues until AAP provides column-level DDL
- No action needed in v3 implementation-plan.md; schema swap procedure already documented and ready
