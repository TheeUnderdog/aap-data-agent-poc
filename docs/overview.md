# AAP Data Agent POC — Executive Overview

**Project:** Advanced Auto Parts Data Agent Proof of Concept  
**Status:** Architecture & Planning Complete | Implementation Ready  
**Document Purpose:** High-level project summary for stakeholders and implementation team

---

## The Opportunity

Advanced Auto Parts' marketing team needs to answer questions about customer rewards and loyalty data—**in plain English**. Today, they rely on IT to write SQL queries or build Power BI reports. This POC unlocks self-service analytics through **natural language querying**, powered by Microsoft Fabric's Data Agent capability and AAP's existing Fabric infrastructure.

**Expected Outcome:** Marketing team members can type questions like "How many gold-tier customers purchased in the last month?" and instantly get accurate, AI-generated SQL results—no data engineering team needed.

---

## How It Works: The Solution in Four Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  Azure PostgreSQL          Microsoft Fabric              Web App            │
│  (Rewards/Loyalty)         (Data Agent)                (React SPA)         │
│        │                         │                         │                │
│    Rewards Data             NL→SQL Conversion         Marketing Team       │
│  Transactions, Tiers,   Powered by AI                 User Interface       │
│  Loyalty Points         Query Orchestration           Chat-like Questions   │
│        │                         │                         │                │
│        ├─────────────────────────┼─────────────────────────┤              │
│        │    Phase 1: Workspace   │                         │              │
│        │    Phase 2: Mirroring   │    Phase 3: Agent       │              │
│        │    Phase 4: Backend & App                         │              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Fabric Workspace (3–5 days)
Set up a dedicated Microsoft Fabric workspace with a Lakehouse for storing mirrored data. This is the foundation—a secured space within AAP's existing Fabric environment where all data and analytics components live.

### Phase 2: PostgreSQL Mirroring (5–7 days)
Configure Fabric Mirroring to automatically sync rewards and loyalty data from Azure PostgreSQL into Fabric's OneLake storage. Data updates in near-real-time (typically within minutes), so the Data Agent always works with fresh information. We deploy a placeholder schema to prove the architecture works.

### Phase 3: Fabric Data Agent (5–7 days)
Deploy a Fabric Data Agent configured with business context (e.g., "gold tier means $1,500+ annual spend"). The agent learns from sample questions and translates natural language into accurate SQL queries. It runs inside the Fabric workspace and returns results in seconds.

### Phase 4: Web Application (3–5 days)
Build a lightweight React web app with a chat-like interface. Users authenticate via Azure Entra ID (SSO), ask questions in plain English, and see results with the generated SQL for transparency. The app runs in Azure Static Web Apps (serverless, low cost).

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

**Effort:** 1–2 days for data engineer. **Code changes required:** Zero in the app, API, or Data Agent logic.

---

## Project Timeline & Effort

| Phase | Description | Duration | Owner |
|-------|-------------|----------|-------|
| **1** | Fabric workspace setup | 3–5 days | Data Platform Team |
| **2** | PostgreSQL mirroring & placeholder schema | 5–7 days | Data Engineer |
| **3** | Data Agent configuration & testing | 5–7 days | Data Engineer, Architect |
| **4** | Web app development & deployment | 3–5 days | Frontend + Backend Engineers |
| **Integration & UAT** | End-to-end testing, security review | 3–5 days | Full Team |
| **Total** | — | **3–4 weeks** | — |

*Timelines assume AAP provides PostgreSQL access and Fabric capacity assignment immediately.*

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
