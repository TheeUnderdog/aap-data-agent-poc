# AAP Data Agent POC — Project Overview

**Project:** Advanced Auto Parts Rewards & Loyalty Data Agent  
**Status:** Demo-ready. Web app, data, and Fabric agents operational in MSIT tenant.  
**Updated:** April 2026

---

## What This Is

A proof-of-concept that lets AAP's marketing team query rewards and loyalty data using plain English. A user types "How many gold-tier members signed up last quarter?" and gets an answer back — no SQL, no report request, no waiting on IT.

The system uses Microsoft Fabric's Data Agent to translate natural language into SQL, runs it against a Lakehouse, and returns results through a branded chat web app.

---

## Architecture

```
Azure PostgreSQL ──► Fabric Mirroring ──► OneLake Lakehouse ──► Fabric Data Agent
  (source data)       (CDC replication)     (Delta tables)       (NL → SQL)
                                                                      │
                                                                      ▼
                                                            Python proxy (server.py)
                                                            SSE streaming, Entra ID auth
                                                                      │
                                                                      ▼
                                                            React SPA (Advance Insights)
                                                            AAP-branded chat interface
```

**Auth:** Azure Entra ID everywhere. The Python backend authenticates to Fabric using InteractiveBrowserCredential (dev) or service principal (production). The SPA authenticates users via MSAL.

**API:** Fabric Data Agent exposes an OpenAI-compatible Assistants API. The backend creates threads, sends messages, polls runs, and streams results back to the browser via Server-Sent Events.

**Tenant:** Microsoft MSIT (`72f988bf-86f1-41af-91ab-2d7cd011db47`). API base: `msitapi.fabric.microsoft.com`.

---

## Approach

We built the full stack against placeholder data. The schema is informed by AAP's domain (loyalty tiers, transactions, points, coupons, stores, SKUs) but uses generated sample data — not real AAP data.

Everything queries through a **semantic view layer** (`v_member_summary`, `v_transaction_history`, `v_points_activity`, etc.). When the real schema arrives from AAP, we remap the views. The web app, API, and Data Agent instructions don't change.

The Fabric Data Agent is configured with a semantic model (10 tables, 34 DAX measures, linguistic schema with 169 synonyms) and five persona-specific instruction sets that teach it how to interpret domain terminology and write correct SQL.

---

## Demo Artifacts

### Web App — "Advance Insights"

An AAP-branded single-page app with six chat tabs, each backed by a specialist Fabric Data Agent:

| Tab | Agent | Domain |
|-----|-------|--------|
| **Crew Chief** | Client-side orchestrator | Routes questions to the right specialist, fans out multi-domain queries |
| **Pit Crew** | Customer Service & Support | CSR activities, member lifecycle, audit trail |
| **GearUp** | Loyalty Program Manager | Members, tiers, points, enrollment trends |
| **Ignition** | Marketing & Promotions | Campaigns, coupons, engagement metrics |
| **PartsPro** | Merchandising & Categories | Product sales, SKU performance, category trends |
| **DieHard** | Store Operations | Store revenue, regional performance, traffic patterns |

**UX features:**
- AAP website branding (Open Sans, yellow+black, solid black nav bar)
- Real-time SSE streaming with character count on responses
- Reasoning panel showing agent chain-of-thought as connected bubbles with per-step duration
- Token usage counter (prompt/completion/total) — populated when the Fabric API returns usage data
- Responsive layout: desktop tabs, mobile hamburger sidebar
- Markdown rendering with table support in chat bubbles

### Data Layer

- **Notebook** (`notebooks/01-create-sample-data.py`): Generates ~2.8M rows across 10 Delta tables in the Fabric Lakehouse. Deterministic seed for reproducibility.
- **Semantic model**: DirectLake mode, 10 tables, 8 relationships, 34 DAX measures, linguistic schema with table/column/value synonyms.
- **9 semantic views**: Stable query contract between the Data Agent and the underlying tables.

### Agent Configurations

Five agent personas in `agents/`, each with:
- `config.json` — metadata and persona definition
- `*-instructions.md` — full system prompt teaching the agent domain vocabulary, query patterns, and business rules
- `examples.json` — 6-8 sample Q&A pairs for few-shot grounding

### Infrastructure

- Fabric workspace, Lakehouse, semantic model, and credential binding provisioned via Python scripts against the Fabric REST API
- Azure Static Web Apps deployment configuration ready (`web/staticwebapp.config.json`)
- Docker support for local development (`web/Dockerfile`)

---

## Running the Demo

**Local (developer mode):**
```
cd web
python server.py
```
Opens a browser for Azure login, then serves the app at `http://localhost:5000`. The Python server proxies API calls to Fabric, handling auth and SSE streaming.

**Deployed:**
Azure Static Web Apps with a managed Functions backend (not yet deployed — see Next Steps).

---

## Snowflake Mirroring

AAP's production loyalty data currently lives in Snowflake, not Azure PostgreSQL. Fabric supports Snowflake mirroring as a first-class connector:

1. **Connection:** Provide Snowflake account URL, warehouse, database, and credentials (username/password or key pair). Fabric connects via the Snowflake SQL API.
2. **Table selection:** Choose which tables/schemas to mirror. Fabric discovers available objects and lets you pick.
3. **Initial snapshot:** Full copy into Lakehouse Delta tables.
4. **Incremental sync:** Fabric uses Snowflake change tracking (or periodic snapshot diffs) to keep Delta tables current. Latency is typically minutes, not real-time CDC like PostgreSQL.
5. **Schema changes:** New columns in Snowflake propagate automatically to the Delta tables.

The mirroring target is the same Lakehouse we already have. Once Snowflake tables land as Delta tables, the semantic view layer maps them to the contract views the Data Agent already uses. No changes to the web app or agent instructions are needed — only the view definitions and possibly the semantic model get updated.

**Prerequisite:** The Snowflake account must allow outbound network access to Fabric's mirroring service. If AAP uses Snowflake Private Link, additional network configuration may be required.

---

## Schema Risks and Migration

We built against a placeholder schema based on a single architecture diagram from AAP. When the actual Snowflake schema arrives, expect these changes:

### High-confidence mappings (minimal rework)

- **Loyalty members / transactions / transaction items** — These are standard retail tables. Our placeholder structure (`loyalty_members`, `transactions`, `transaction_items`) closely mirrors what any loyalty database would have. Column names will differ; the view layer absorbs this.

### Known gaps between placeholder and reality

| Area | What we assumed | What AAP actually has | Impact |
|------|----------------|----------------------|--------|
| **Points & tiers** | Simple `member_points` ledger table | CrowdTwist — an external loyalty engine that manages points, tiers, bonus activities, and campaigns | Views `v_points_activity` and `v_member_summary` will need significant remapping. CrowdTwist data may arrive as denormalized exports rather than normalized tables. |
| **Coupons** | Minimal `coupon_rules` and `coupons` tables | GK Coupon Management — a dedicated system with rules, issuance, status, and reference data | Need a new `v_coupon_activity` view. Agent instructions for Ignition and GearUp need coupon-specific query patterns. |
| **Stores** | Dedicated `stores` reference table | No visible stores table in AAP's architecture | Store data may be attributes on transactions. `v_store_performance` would aggregate from transaction records instead of joining to a store dimension. |
| **Rewards catalog** | Standalone rewards table | No explicit catalog — rewards likely managed within CrowdTwist | `v_reward_catalog` view may need to be rethought or sourced from CrowdTwist exports. |
| **Audit / fraud** | Not modeled | Distinct table group — agent activity, enrollment history, coupon history | New domain. Add `v_audit_trail` view and update Pit Crew agent instructions. |
| **CSR agents** | Basic `csr` table | Agent Details table fed by Customer First system | Mapping should be straightforward; column names will change. |
| **Campaigns** | Standalone `campaigns` table | Managed in CrowdTwist as bonus activities | Ignition agent instructions reference campaign tables that may not exist as standalone entities. |

### What changes when the real schema arrives

1. **View definitions** (`docs/data-schema.md` §5): Rewrite SQL for each `v_*` view to map new column names and table structures. Add `v_coupon_activity` and `v_audit_trail`.
2. **Semantic model**: Update table definitions, relationships, and DAX measures to reflect new columns. Re-bind credentials.
3. **Linguistic schema**: Update synonyms for any renamed tables/columns.
4. **Agent instructions**: Update domain-specific query patterns in the five `*-instructions.md` files where they reference specific table or column names.
5. **Sample data notebook**: Replace with mirrored Snowflake data. The notebook becomes unnecessary.

The web app, API proxy, auth flow, and UX do not change.

---

## Current Status

### Complete
- Fabric workspace provisioned (`AAP-RewardsLoyalty-POC`)
- Lakehouse created with SQL endpoint
- Sample data notebook: 10 tables, ~2.8M rows, loaded and verified
- Semantic model: 10 tables, 8 relationships, 34 DAX measures, DirectLake mode
- Linguistic schema: 50 table synonyms, 66 column synonyms, 53 value synonyms
- Credential binding: semantic model authenticated to Lakehouse SQL endpoint
- 5 Fabric Data Agent configurations with persona instructions and examples
- Web app: AAP-branded chat UI with 6 agent tabs, reasoning panel, token counter, SSE streaming
- Local dev server (`server.py`) with interactive browser auth

### Remaining manual portal tasks
1. **Entra ID app registration** — needed for production MSAL auth (currently using interactive browser credential for dev)
2. **Azure Static Web Apps deployment** — SWA resource creation and Functions backend deployment
3. **Fabric Data Agent instruction import** — portal-only (no REST API); copy instruction markdown and examples into each of the 5 agents

---

## Next Steps

1. **Import agent instructions into Fabric portal** — Copy the five `*-instructions.md` files and `examples.json` content into each Data Agent's configuration. This is manual portal work (~30 minutes).
2. **End-to-end test with live Fabric agents** — Verify that natural language queries produce correct SQL and accurate results through the web app.
3. **Deploy to Azure Static Web Apps** — Create SWA resource, configure managed Functions backend with service principal auth to Fabric.
4. **Register Entra ID app** — App registration for production MSAL flow (replace interactive browser credential).
5. **Connect Snowflake mirroring** — When AAP provides Snowflake access, set up mirroring to the existing Lakehouse.
6. **Schema migration** — When the real schema lands, remap views, update semantic model, refresh agent instructions.
7. **Token usage validation** — Confirm whether the Fabric Assistants API returns `usage` data in run completions (the UI is ready to display it).

---

## Repository Structure

```
docs/                          Architecture, schema, and this overview
agents/                        5 Fabric Data Agent configs (instructions + examples)
notebooks/                     Sample data generator (PySpark)
web/
  index.html                   SPA entry point
  config.js                    Agent GUIDs, MSAL config, routing keywords
  server.py                    Local auth proxy (Flask + Azure Identity)
  js/app.js                    Chat UI, tabs, reasoning panel, token counter
  js/agent-client.js           Fabric API client with SSE parsing
  js/executive.js              Crew Chief keyword router
  js/auth.js                   MSAL authentication
  css/app.css                  AAP-branded styles
  img/                         Agent icons (SVG)
scripts/                       Fabric REST API provisioning scripts
config/                        Sample queries, semantic model config
```

---

## Key IDs

| Resource | ID |
|----------|----|
| Fabric Workspace | `82f53636-206f-4825-821b-bdaa8e089893` |
| Lakehouse | `0b895197-a0b2-40b4-9ab3-2daeb0e778c0` |
| Semantic Model | `f5483f6a-e81a-4cd8-ac42-88af4b972347` |
| Pit Crew Agent | `e2cf8db6-2e51-45b6-bb2d-edfeeeb8b38a` |
| GearUp Agent | `b03579f9-1074-4578-8165-6954a83b31c5` |
| Ignition Agent | `f0272a61-7e54-408f-bf70-28495982567b` |
| PartsPro Agent | `1062ac57-5132-4cf1-afbd-71e1e973fbc8` |
| DieHard Agent | `e8fc166b-360e-4b0a-922b-05ca8bba3ff4` |

### Phase 2: PostgreSQL Mirroring (4–6 hours active)
Configure Fabric Mirroring to automatically sync rewards and loyalty data from Azure PostgreSQL into Fabric's OneLake storage. Data updates in near-real-time (typically within minutes), so the Data Agent always works with fresh information. We deploy a placeholder schema to prove the architecture works. All provisioning is scripted.

### Phase 3: Fabric Data Agent (4–6 hours active)
Deploy a Fabric Data Agent configured with business context (e.g., "gold tier means $1,500+ annual spend"). The agent learns from sample questions and translates natural language into accurate SQL queries. It runs inside the Fabric workspace and returns results in seconds. Configuration is stored as code and deployed via scripts.

### Phase 4: Web Application (1–2 days active)
Build a lightweight React web app with a chat-like interface. Users authenticate via Azure Entra ID (SSO), ask questions in plain English, and see results with the generated SQL for transparency. The app deploys to Azure Static Web Apps via Bicep templates and CI/CD pipeline.

---

## Why This Architecture Works

### Data Abstraction Layer: Future-Proofing the POC

A core principle of this design is **schema independence**. We use a contract layer (SQL views) between the raw data and the Data Agent:

```
PostgreSQL (raw tables)
    ↓
Lakehouse (mirrored data)
    ↓
[Semantic Views — Contract Layer]
    ↓
Data Agent, APIs, Reports (consume views, not tables)
```

**Why this matters:** When AAP provides the production schema, we remap the views to new table names and columns. The Data Agent, web app, and all other components need **zero code changes**. Views act as an adapter layer, isolating the system from schema volatility.

### Technology Choices

| Component | Choice | Why |
|-----------|--------|-----|
| **Data Lake** | Fabric Lakehouse | Native mirroring integration, Delta Lake format handles schema evolution, cost-efficient |
| **Data Sync** | Fabric Mirroring | Managed service, CDC for incremental sync, no custom ETL code |
| **NL→SQL Engine** | Fabric Data Agent | Built on Azure OpenAI, native Fabric integration, handles complex queries |
| **Authentication** | Azure Entra ID | SSO for all users, service principals for backend access, unified identity model |
| **Deployment** | Azure Static Web Apps + Functions | Serverless, auto-scaling, simple CI/CD pipeline, low cost |
| **Database** | PostgreSQL (existing) | No schema or storage changes needed in source system |

---

## What AAP Needs to Provide

To move forward, AAP must deliver:

1. **Production Rewards/Loyalty Schema** (when available)
   - Table structure, column names, relationships
   - Data dictionary or schema documentation
   - Sample data size estimates

2. **Azure PostgreSQL Access**
   - Connection string and credentials
   - Network access (firewall rules or private link)
   - Logical replication enabled (`wal_level = logical`)

3. **Fabric Capacity Assignment**
   - One of AAP's existing Fabric capacities for this workspace
   - Recommended: Non-production capacity to avoid impacting Power BI workloads
   - Minimum F64 capacity for Mirroring + Data Agent workloads

4. **Azure Entra ID Integration**
   - Service principal for Data Agent backend access
   - User group membership for app access control

5. **Sign-Off**
   - Approval from AAP security, data governance, and marketing stakeholders
   - Confirmation on data sensitivity (PII handling, access restrictions)

---

## Schema Migration Strategy: From Placeholder to Production

**Phase 2 uses a placeholder schema** (not the real AAP data model) to prove the architecture works. When production schema arrives:

1. **Map new tables to views** in the `semantic` schema
2. **Update view DDL** to reflect real column names, relationships, and business logic
3. **Add sample queries** to the Data Agent configuration (training data for accuracy)
4. **Run regression tests** with real data
5. **Switch Data Agent to production** (single configuration update)

**Effort:** 4–8 hours active work for data engineer. **Code changes required:** Zero in the app, API, or Data Agent logic.

---

## Project Timeline & Effort

All provisioning is fully scripted (Fabric REST API, Azure CLI, Bicep). Estimates below separate **active work** from **wait time** (blocked on AAP access grants, data snapshots, etc.).

| Phase | Description | Active Work | Wait Time | Calendar |
|-------|-------------|-------------|-----------|----------|
| **1** | Fabric workspace setup | 2–4 hours | 0–2 days | 1–2 days |
| **2** | PostgreSQL mirroring & placeholder schema | 4–6 hours | 0–3 days | 1–4 days |
| **3** | Data Agent configuration & testing | 4–6 hours | 0–1 day | 1–2 days |
| **4** | Web app development & deployment | 1–2 days | 0–2 days | 2–4 days |
| **Schema Swap** | Cutover to production data | 4–8 hours | 0–2 days | 1–3 days |
| **Total** | — | **3–5 days** | — | **2–3 weeks** |

*Calendar time includes wait for AAP prerequisites (Fabric access, PostgreSQL credentials, Entra ID permissions). Active work can be compressed if access is pre-staged.*

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **PostgreSQL network access delayed** | Start Phase 1 in parallel; use dummy schema for agent testing |
| **Schema mismatch between placeholder and real data** | Contract layer (views) isolates schema changes; easy remapping when real schema arrives |
| **Data Agent accuracy (wrong SQL)** | Comprehensive sample queries in agent config; UAT with real questions before launch |
| **Security: Entra ID integration fails** | Test service principal authentication early in Phase 3; fallback to simplified auth if needed |
| **Fabric capacity contention** | Use non-production capacity; monitor mirroring/agent resource usage; scale if needed |

---

## Success Criteria

The POC is successful when:

✅ Marketing users can ask 10+ different questions in plain English  
✅ Data Agent generates correct SQL with >90% accuracy  
✅ Query results return within 5 seconds  
✅ System supports 5+ concurrent users without degradation  
✅ Production schema integration verified with real AAP data  
✅ Stakeholders approve for next phase (production deployment)

---

## Next Steps

1. **AAP provides PostgreSQL details** — connection info, schema availability, network setup
2. **Architect reviews this document with team** — confirm approach, identify blockers
3. **Data Platform team begins Phase 1** — workspace + Lakehouse creation
4. **Data Engineer starts Phase 2** — mirroring configuration + placeholder schema
5. **Weekly sync calls** — track progress, resolve blockers, adapt timeline

---

## Learn More

For deeper technical details, refer to:

- **`docs/architecture.md`** — Complete technical design, component specifications, Phase 1–4 deep dives
- **`docs/implementation-plan.md`** — Step-by-step task lists, validation criteria, schema swap procedure
- **`docs/data-schema.md`** — Placeholder schema DDL, entity relationships, semantic view contract

---

**Document Owner:** Microsoft Field Team  
**Last Updated:** April 2026  
**Status:** Ready for Stakeholder Review
