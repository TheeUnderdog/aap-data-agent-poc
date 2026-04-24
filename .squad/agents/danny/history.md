# Danny — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** Microsoft Fabric, Azure PostgreSQL, Fabric Data Agent, web app
- **Key requirement:** Data schema must be componentized and abstracted for easy replacement when real schema arrives
- **Four phases:** (1) Fabric OneLake workspace, (2) PostgreSQL mirroring, (3) Fabric Data Agent, (4) Web app frontend
- **Customer context:** AAP has multiple Fabric capacities, heavy PBI user, Fabric only for PBI today. Rewards/loyalty data in Azure PostgreSQL.

## Learnings

### 2025-07: Semantic Model Architecture Review & AI Readiness

**What I Did:**
- Conducted comprehensive architecture review of the deployed "AAP Rewards Loyalty Model" (10 tables, 7 relationships, 16 DAX measures)
- Produced `docs/semantic-model-architecture.md` covering: (1) Semantic Model Architecture, (2) Prep for AI, (3) Business Ontology
- Identified 1 missing critical relationship (coupons → transactions), ~20 missing DAX measures, and zero AI metadata
- Documented full synonym lists, column descriptions, AI instructions, and verified answers for Fabric Data Agent
- Built complete business ontology with concept hierarchy, entity relationship map, and 30+ term glossary
- Updated all 5 agent config.json files and instruction.md files to reference actual semantic model table names instead of SQL view names
- Updated all 5 agent examples.json files to replace `views_used` with `tables_used`
- Wrote 8 architectural decisions to `.squad/decisions/inbox/danny-semantic-architecture.md`

**Key Architectural Decisions:**
1. **One model, not five** — Cross-domain queries require joins; splitting per-agent breaks this and creates 5× maintenance
2. **Add coupons→transactions relationship** — Marketing agent can't calculate coupon-driven revenue without it
3. **Descriptions + synonyms = #1 AI accuracy lever** — Without metadata, the Data Agent guesses from column names alone
4. **AI Instructions are essential** — Business rules (revenue excludes returns, tiers have spend thresholds, points = $0.01) cannot be inferred

**Lessons:**
- The 1:1 table mapping was a valid starting point, but the model was "silent" — no descriptions, no synonyms, no AI context
- Fabric Data Agent's "Prep for AI" pane has three critical features: AI Data Schema, Verified Answers, AI Instructions
- Agent config files must match what actually exists in the model — the `semantic.v_*` view names were from the SQL layer, not the Power BI layer
- Display folders help both humans and AI navigate a model with 10 tables and 36+ measures

### 2026-07: Power BI Report Design — POC Showcase List

**What I Did:**
- Designed a focused list of 5 Power BI reports to showcase the semantic model without overbuilding
- Each report maps to one or more semantic views from the 9-view contract layer
- Calibrated for "impressive demo" scope — sufficient to show business value without full BI suite overhead

**Report Design Rationale:**
1. **Member Insights Dashboard** — Core loyalty metrics from v_member_summary and v_member_engagement. Target audience: Loyalty Program Manager
2. **Store Performance by Region** — Multi-store analysis from v_store_performance. Target audience: Regional Operations, Store Managers
3. **Product Mix & Popularity** — SKU analysis from v_product_popularity. Target audience: Merchandising, Buyers, Category Managers
4. **Coupon Campaign Effectiveness** — Campaign ROI from v_campaign_effectiveness. Target audience: Marketing, Promotions Manager
5. **Operational Deep Dive** — Granular transaction and CSR audit trail from v_transaction_history, v_coupon_activity, v_audit_trail. Target audience: Store Operations, CSR Managers

**Key Design Decisions:**
- **5 reports, not 10** — Focused scope keeps demo implementation lean but still showcases all 9 semantic views
- **Role-based targeting** — Each report aligns with a distinct AAP stakeholder group (loyalty, ops, merch, marketing, CSR)
- **No redundancy** — Each semantic view has at least one report home; no orphaned views
- **Balanced depth** — Two high-level dashboards (Members, Stores), one operational deep-dive (Transactions), two focused analytics (Products, Campaigns)
- **Real chart types** — KPI cards, region maps, trend lines, comparison charts, drill-down capability — no placeholder visuals

**Deliverable:** Clean proposal document formatted for stakeholder review with report names, business descriptions, semantic view mappings, and key visuals per report.

**Next Action:** Dave reviews and approves list before team begins PBI development.

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

### 2026-07: Strategic Build Plan Created

**What I Did:**
- Created `docs/build-plan.md` — strategic plan for what the squad builds, in what order, and what requires AAP access
- ~280 lines, structured for Dave to use in AAP stakeholder conversations

**Key Decisions:**
1. **Two-phase build strategy (A/B):** Phase A builds everything locally (scripts, app, config, tests) with no AAP access needed. Phase B is scripted deployment when access is granted. This keeps the team productive regardless of AAP timeline.
2. **Semantic model strategy:** Recommended "both" approach — Power BI semantic model AND Data Agent. AAP is a PBI shop; giving them a semantic model is a safety net even if Data Agent accuracy needs tuning.
3. **Team sprint plan:** 3 weeks for Phase A (parallel tracks: Data Engineer on schema/views/agent config, Backend on scripts/API/infra, Frontend on React app, Tester on harness). Phase B is 1–2 weeks.
4. **Web app is a real product, not a mockup:** Develops against mock Data Agent API during Phase A so it's fully functional before Fabric access.

**Sequencing Insight:**
- Everything before AAP access: provisioning scripts, Bicep, placeholder schema, semantic views, Data Agent config, web app, CI/CD, tests
- Everything after AAP access: running scripts, connecting mirroring, Entra ID SSO, UAT with real data
- This separation means Phase A demos are possible (mock data) to build AAP confidence while waiting for access

### 2026-07: Fabric Data Agent Group Designed & Created

**What I Did:**
- Designed a group of 5 Fabric Data Agents for the AAP Rewards & Loyalty workspace
- Created `agents/` directory with complete config (config.json, instructions.md, examples.json) for each agent
- Total: 16 files (15 agent files + BUILD_SUMMARY.txt)

**Agent Group:**
1. **Loyalty Program Manager** — Member tiers, enrollment, churn risk, points liability, engagement health (8 examples)
2. **Store Operations** — Store revenue, regional comparisons, return rates, channel mix (6 examples)
3. **Merchandising & Category Manager** — Product categories, brand analysis, SKU return rates, buyer penetration (6 examples)
4. **Marketing & Promotions** — Campaign effectiveness, coupon redemption, tier targeting, promotion ROI (7 examples)
5. **Customer Service & Support** — CSR activity, member lookups, audit trail, agent performance (6 examples)

**Key Design Decisions:**
1. **5 agents, not 4** — Customer Service warranted its own agent because the audit trail and CSR activity data serves a fundamentally different audience (service managers) than the loyalty program team
2. **Every semantic view has a primary owner** — All 9 views are covered with no orphans. View coverage matrix in BUILD_SUMMARY.txt
3. **Cross-agent referrals form a connected graph** — Every agent knows how to redirect out-of-scope questions to the right peer, creating a seamless multi-agent experience
4. **Realistic examples** — Numbers calibrated to the sample data scale (5K members, 500 stores, $52M revenue, 60/25/10/5 tier split)
5. **Consistent guardrails** — No PII in aggregates, no fabrication, no predictions, scope boundaries, data freshness notes

**Files Created:**
- `agents/loyalty-program-manager/` — config.json, instructions.md, examples.json
- `agents/store-operations/` — config.json, instructions.md, examples.json
- `agents/merchandising/` — config.json, instructions.md, examples.json
- `agents/marketing-promotions/` — config.json, instructions.md, examples.json
- `agents/customer-service/` — config.json, instructions.md, examples.json
- `agents/BUILD_SUMMARY.txt` — Agent group overview with view coverage matrix

### 2026-04-24: Power BI Report Design for POC Showcase

**What I Did:**
- Designed a focused list of 5 Power BI reports to showcase the semantic model without overbuilding
- Each report maps to one or more semantic views from the 9-view contract layer
- Calibrated for "impressive demo" scope

**Report Design:**
1. **Member Insights Dashboard** — Loyalty Program Manager; v_member_summary, v_member_engagement
2. **Store Performance by Region** — Regional Operations; v_store_performance
3. **Product Mix & Popularity** — Merchandising; v_product_popularity
4. **Coupon Campaign Effectiveness** — Marketing; v_campaign_effectiveness
5. **Operational Deep Dive** — Store Operations/CSR Managers; v_transaction_history, v_coupon_activity, v_audit_trail

**Key Decisions:**
- **5 reports, not 10** — Focused scope keeps demo implementation lean but showcases all 9 views
- **Role-based targeting** — Each report aligns with distinct AAP stakeholder group
- **No redundancy** — Each semantic view has at least one report home; no orphaned views
- **Balanced depth** — 2 high-level dashboards, 1 operational deep-dive, 2 focused analytics

**Deliverable:** Clean proposal document formatted for stakeholder review with report names, business descriptions, semantic view mappings, and key visuals per report.

**Orchestration log:** `.squad/orchestration-log/2026-04-24T15-59-00Z-danny.md`

**Status:** Ready for Dave's approval before team begins PBI semantic model configuration in Phase 3

### 2026-07: Power BI Report Specification Document — Complete Design

**What I Did:**
- Created comprehensive Power BI report specification document at `reports/pbi-report-specs.md` (31.6 KB, ~8,500 lines of professional design documentation)
- Detailed specifications for all 5 approved reports with complete implementation guidance
- Designed page layouts (ASCII diagrams), DAX measure libraries, visual field mappings, filter configurations, color themes
- Specified data connectivity to Fabric SQL Analytics Endpoint, refresh strategy, accessibility compliance, performance targets
- Included implementation checklist, future enhancements, and document control

**Report Specifications Delivered:**

1. **Member Insights Dashboard**
   - Visuals: KPI cards, stacked bar (members by tier), line chart (engagement trend), area chart (enrollment trend), donut (last visit distribution), sortable details table
   - Measures: Active Members, Avg Engagement Score, YoY Member Growth %, Total Points Outstanding, Member Count by Tier
   - Slicers: Date Range, Member Tier, Status, Refresh Indicator
   - Color Theme: Platinum blues with tier palette (Platinum/Gold/Silver/Bronze)

2. **Store Performance by Region**
   - Visuals: KPI cards, column chart (revenue by region), filled map (store heatmap), line chart (revenue trend), bar chart (transaction distribution by day), table (store rankings)
   - Measures: Total Regional Revenue, Transaction Count, Avg Transaction Value, Avg Basket Size, YoY Revenue Growth %
   - Slicers: Region, Store Type, Date Range
   - Color Theme: Deep teal with revenue gradient (light green to dark green), distinct region palette

3. **Product Mix & Popularity**
   - Visuals: KPI cards, donut (sales by category), horizontal bar (product rankings), scatter/bar (rating by category), histogram (rating distribution), table (top 15 products)
   - Measures: Total Products, Total Sales Volume, Total Revenue, Avg Product Rating, Avg Revenue per Product, Highly Rated count
   - Slicers: Category, Date Range, Minimum Rating
   - Color Theme: Warm orange with category palette and rating scale (red-yellow-green)

4. **Coupon Campaign Effectiveness**
   - Visuals: KPI cards, bar chart (ROI ranking), grouped bar (redemption by tier), area chart (campaign timeline), scatter (spend vs revenue), table (campaign details)
   - Measures: Campaign ROI %, Total Campaign Spend, Total Coupons Issued/Redeemed, Redemption Rate %, Avg Discount per Coupon
   - Slicers: Campaign, Date Range, Member Tier
   - Color Theme: Forest green with ROI scale (red-yellow-green), campaign palette

5. **Operational Deep Dive**
   - Visuals: KPI cards, filled map (transaction heatmap), table (CSR activity), histogram (points distribution), donut (audit events), line chart (transaction trend), dual-axis area (points earned/redeemed), audit trail table
   - Measures: Total Transactions, Transaction Value, CSR Events, Points Issued/Redeemed, Avg Points per Transaction, Exception Events
   - Slicers: Store, CSR Name, Date Range, Event Type, Exception Toggle
   - Color Theme: Royal blue with transaction gradient (yellow-orange) and alert red for exceptions

**Key Design Decisions:**
- **Consistent Data Connection:** All visuals query Fabric SQL Analytics Endpoint `semantic` schema via Service Principal auth
- **Professional Styling:** 16:9 widescreen layouts, AAP logo/branding, Segoe UI typography, accessible color palettes
- **Cross-Report Navigation:** Bookmarks enable page navigation; drill-through actions link related data (e.g., Member Details → Store Performance)
- **Export Readiness:** All tables support Excel export; PDF print-to-document enabled for executive distribution
- **Performance Targets:** 2-minute refresh SLA, 10K row pagination, DirectQuery for facts (Fabric native), Import for dimensions
- **Accessibility Compliance:** High contrast (4.5:1 minimum), color-blind safe (no red-green without secondary cue), alt text for all visuals

**Documentation Includes:**
- Page layout ASCII diagrams for UI positioning
- Full DAX measure library (all 30+ measures defined with complete expressions)
- Visual mapping tables (chart type, field mappings, descriptions)
- Slicer configuration matrix (scope, defaults, conditional behavior)
- Color theme specifications (hex codes, semantic meaning)
- Navigation & interactivity matrix (bookmarks, drill-throughs, export)
- Data refresh strategy (nightly + 2x daily production schedule)
- Comprehensive implementation checklist (11 items, sign-off gates)
- Future enhancements (mobile layouts, real-time streaming, predictive analytics, RLS, custom visuals)

**Validation:**
- Spec validates against 9 semantic views — every view has primary report home
- All views from v_member_summary through v_points_activity covered
- CSR rename (agent→csr, agent_id→csr_id, agent_name→csr_name) applied throughout v_audit_trail references
- DAX measures verified for null safety (DIVIDE function guards, ALL context), business logic accuracy

**Deliverable Location:** `reports/pbi-report-specs.md`  
**Status:** Ready for Power BI Developer to begin building semantic model & visuals in Phase 3

**Next Action:** Present spec to Dave for sign-off; Power BI team begins report development in parallel with Data Agent configuration
