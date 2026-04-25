# AAP Data Agent POC — Build Plan

**Purpose:** Strategic plan for what we build, how we sequence the work, and what we need from AAP  
**Audience:** Internal team + Dave for AAP conversations  
**Status:** Active Planning

---

## 1. What We're Building

A working proof of concept that lets AAP marketing users ask questions about rewards and loyalty data in plain English and get instant answers. Four deliverables:

| # | Deliverable | What It Is | Demo Value |
|---|-------------|------------|------------|
| 1 | **Fabric Environment** | Workspace, Lakehouse, mirroring from PostgreSQL — all scripted | Shows AAP their Fabric investment extends beyond PBI |
| 2 | **Semantic Model** | SQL views over mirrored data + a Power BI semantic model | Familiar PBI layer AAP already knows how to use |
| 3 | **Fabric Data Agent** | NL→SQL engine configured with business context and sample queries | The "wow factor" — ask questions, get answers |
| 4 | **Web Application** | React chat interface with SSO, hosted on Azure Static Web Apps | Tangible product AAP stakeholders can interact with |

**What success looks like:** An AAP marketing user opens the web app, signs in with their Entra ID, types "How many gold-tier members made a purchase last quarter?", and gets an accurate answer in under 5 seconds — with the generated SQL visible for trust.

---

## 2. The Two-Phase Build Strategy

The key insight: **we don't need AAP environment access to build most of the POC.** We can write all the scripts, code, and configurations now and deploy them later. This separates _building_ from _deploying_.

```
┌─────────────────────────────────────┐    ┌──────────────────────────────────┐
│  PHASE A: Build Locally             │    │  PHASE B: Deploy to AAP          │
│  (No AAP access needed)             │    │  (Requires AAP environment)      │
│                                     │    │                                  │
│  ✅ Fabric provisioning scripts     │    │  🔑 Run scripts against AAP      │
│  ✅ Bicep templates (all infra)     │    │     Fabric tenant                │
│  ✅ Placeholder schema + seed data  │    │  🔑 Connect mirroring to real    │
│  ✅ Semantic view definitions       │    │     PostgreSQL                   │
│  ✅ Data Agent configuration        │    │  🔑 Remap views to production    │
│  ✅ Web app (full React SPA)        │    │     schema                      │
│  ✅ Backend API (Azure Functions)   │    │  🔑 Configure Entra ID SSO      │
│  ✅ Power BI semantic model def     │    │  🔑 End-to-end testing with      │
│  ✅ CI/CD pipeline                  │    │     real data                    │
│  ✅ Test harness + sample queries   │    │  🔑 UAT with marketing users     │
│                                     │    │                                  │
│  Timeline: 2–3 weeks               │    │  Timeline: 1–2 weeks             │
│  Blocked by: Nothing               │    │  Blocked by: AAP access          │
└─────────────────────────────────────┘    └──────────────────────────────────┘
```

**Why this matters for AAP:** When access is granted, deployment is measured in hours, not weeks. We show up ready to execute.

---

## 3. Phase A — What We Build (Before AAP Access)

### 3.1 Fabric Provisioning Scripts

| Script | Purpose | Owner |
|--------|---------|-------|
| `scripts/setup-workspace.ps1` | Create workspace + Lakehouse via Fabric REST API | Backend Developer |
| `scripts/create-service-principal.sh` | Entra ID app registration + RBAC assignment | Backend Developer |
| `scripts/configure-mirroring.ps1` | Set up PostgreSQL mirroring (parameterized) | Data Engineer |
| `scripts/deploy-placeholder-schema.sql` | DDL + seed data for placeholder tables | Data Engineer |
| `scripts/create-semantic-views.sql` | 7+ contract views over mirrored tables | Data Engineer |
| `scripts/schema-swap.ps1` | Remap views when production schema arrives | Data Engineer |

All scripts are **parameterized** — connection strings, capacity IDs, and credentials are injected at deploy time. No hardcoded values.

### 3.2 Semantic Model (Power BI)

We create a Power BI semantic model definition that sits over the Lakehouse SQL endpoint. This gives AAP two ways to query their data:

- **Data Agent** — Natural language for ad-hoc questions
- **Power BI Reports** — Traditional dashboards connected to the same semantic model

The semantic model definition is authored as a TMDL (Tabular Model Definition Language) file that can be deployed via Fabric REST API. It includes:

- Measures (e.g., `Total Members`, `Avg Transaction Value`, `Points Redeemed MTD`)
- Relationships between views
- Display folders and formatting
- Row-level security definitions (if needed)

**Why both?** AAP is a heavy PBI shop. Giving them a semantic model they can build reports against — alongside the Data Agent — maximizes the value of the mirrored data. The Data Agent can also query through the semantic model for better accuracy on calculated measures.

### 3.3 Data Agent Configuration

Authored as source-controlled JSON/YAML files:

| File | Content |
|------|---------|
| `config/agent-instructions.md` | System prompt with business context, terminology, guardrails |
| `config/sample-queries.json` | 20+ NL→SQL pairs for training (placeholder schema) |
| `config/agent-settings.json` | Timeout, row limits, schema scope, PII rules |

The Data Agent is configured to query **semantic views only** — it never sees raw mirrored tables. This enforces the abstraction layer and simplifies the schema swap.

### 3.4 Web Application

| Component | Technology | What We Build |
|-----------|------------|---------------|
| **Frontend** | Vanilla JS SPA | Chat interface with agent tabs, reasoning panel, token tracking |
| **Backend** | Python proxy (server.py) / Azure Functions (Python) | Proxies to Fabric Data Agent API with SSE streaming |
| **Auth** | Entra ID via proxy | Proxy handles auth to Fabric; SWA provides user auth |
| **Hosting** | Azure Static Web Apps | SPA + managed Functions, built-in Entra ID integration |
| **CI/CD** | GitHub Actions | Build, deploy on push to main |

The web app is a **complete, deployable product** — not a mockup. During Phase A, it develops against a local Python proxy (server.py) that authenticates to Fabric Data Agent API. In production, Azure Static Web Apps + managed Functions serves the same role.

**Key UX decisions:**

- Chat-style interface (not form-based) — feels like asking a person
- SQL shown below each answer — builds trust, enables validation
- Agent reasoning panel — shows routing and processing steps in real time
- Six specialist tabs — each agent has its own color-coded chat tab
- "Suggested questions" on first load — guides new users
- Loading states and error handling — production-quality experience

### 3.5 Test Harness

| Test | Purpose |
|------|---------|
| `tests/agent-accuracy.py` | Run sample queries against Data Agent, measure accuracy |
| `tests/api-integration.test.ts` | Backend API endpoints, auth flow, error handling |
| `tests/e2e.spec.ts` | Playwright end-to-end tests for the web app |
| `tests/schema-validation.sql` | Verify semantic views return expected columns/types |

---

## 4. Phase B — Deploy to AAP Environment

When AAP grants access, deployment follows a scripted sequence:

```
Step 1: Run provisioning scripts (workspace, Lakehouse, RBAC)     → 1–2 hours
Step 2: Connect mirroring to PostgreSQL, verify data sync          → 2–3 hours
Step 3: Deploy semantic views over mirrored data                   → 1 hour
Step 4: Deploy Data Agent configuration, run accuracy tests        → 2–3 hours
Step 5: Deploy semantic model, connect PBI                         → 1–2 hours
Step 6: Deploy web app to Azure Static Web Apps                    → 1–2 hours
Step 7: Configure Entra ID SSO, test end-to-end                   → 1–2 hours
Step 8: UAT with AAP marketing users                              → 1–2 days
```

**Total Phase B active work:** 2–3 days  
**Total Phase B calendar time:** 1–2 weeks (including UAT scheduling)

---

## 5. Semantic Model Strategy

This is a key architectural decision. Three options:

### Option A: Data Agent Only (No Semantic Model)

```
PostgreSQL → Lakehouse → Semantic Views → Data Agent → Web App
```

- **Pros:** Simplest to build, fewer moving parts
- **Cons:** No PBI integration, misses AAP's primary tool

### Option B: Power BI Semantic Model Only (No Data Agent)

```
PostgreSQL → Lakehouse → Semantic Model → Power BI Reports
```

- **Pros:** Familiar to AAP, proven technology
- **Cons:** No natural language, just traditional BI — not a "wow" demo

### Option C: Both — Semantic Model + Data Agent ✅ Recommended

```
PostgreSQL → Lakehouse → Semantic Views → Semantic Model → Data Agent
                                       ↘                 ↗
                                        → Power BI Reports
```

- **Pros:** Data Agent queries through semantic model for calculated measures. AAP gets PBI reports AND natural language. Maximum demo value.
- **Cons:** More components to build and maintain
- **Why we recommend this:** AAP already knows PBI. Giving them a semantic model they can immediately use for reports — plus the Data Agent for ad-hoc questions — makes the POC valuable even if the Data Agent piece needs tuning. It's a safety net: worst case, they still get a working PBI model over their mirrored data.

**Semantic model scope (POC):**

| Measure Group | Example Measures |
|---------------|-----------------|
| Membership | Total members, new members MTD, members by tier |
| Transactions | Total revenue, avg transaction value, transaction count |
| Points | Points earned, points redeemed, redemption rate |
| Engagement | Active members (30/60/90 day), purchase frequency |

---

## 6. Team Work Breakdown

### Phase A Sprint Plan

| Week | Data Engineer | Backend Developer | Frontend Developer | Tester |
|------|--------------|-------------------|--------------------|--------|
| **1** | Placeholder schema DDL, seed data scripts, semantic view SQL | Fabric REST API provisioning scripts, service principal setup | React app scaffolding, chat UI component, MSAL auth integration | Test plan, schema validation tests |
| **2** | Data Agent config (instructions, sample queries), semantic model TMDL | Backend API (Azure Functions), Data Agent proxy, Bicep templates | Query history, SQL panel, suggested questions, error states | API integration tests, mock agent tests |
| **3** | Mirroring configuration script, schema swap automation | CI/CD pipeline, deploy scripts, Key Vault integration | E2E polish, loading states, responsive design | E2E tests (Playwright), accuracy test harness |

### Phase B Sprint Plan

| Week | Data Engineer | Backend Developer | Frontend Developer | Tester |
|------|--------------|-------------------|--------------------|--------|
| **4** | Run provisioning, connect mirroring, deploy views + semantic model | Deploy web app + API, configure Entra ID SSO | UX fixes from real data testing | Run all test suites against live environment |
| **5** | Remap views if production schema available, tune Data Agent accuracy | Performance tuning, monitoring setup | UAT support, feedback incorporation | Regression testing, UAT coordination |

---

## 7. What We Need from AAP

Organized by priority and timing:

### Before Phase B (Needed to Deploy)

| # | Item | Why | Priority | Status |
|---|------|-----|----------|--------|
| 1 | **Fabric capacity assignment** | Need a capacity ID to create the workspace | 🔴 Critical | Not started |
| 2 | **PostgreSQL connection details** | Host, port, database, credentials for mirroring | 🔴 Critical | Not started |
| 3 | **Network access** | Firewall rules or private endpoint for Fabric→PostgreSQL | 🔴 Critical | Not started |
| 4 | **`wal_level = logical`** enabled | Required for Fabric Mirroring CDC | 🔴 Critical | Not started |
| 5 | **Entra ID tenant access** | App registration for SSO + service principal | 🟡 Important | Not started |
| 6 | **Column-level schema** (DDL or data dictionary) | Remap semantic views to real tables | 🟡 Important | Partial (table groups known, columns not) |

### Nice to Have (Improves Quality)

| # | Item | Why | Priority |
|---|------|-----|----------|
| 7 | **10–20 real business questions** from marketing | Training data for Data Agent accuracy | 🟡 Important |
| 8 | **Data volume estimates** (row counts per table) | Size mirroring and Lakehouse | 🟢 Helpful |
| 9 | **PII handling rules** | Configure Data Agent guardrails | 🟢 Helpful |
| 10 | **Non-production capacity** confirmation | Avoid impacting existing PBI workloads | 🟢 Helpful |

---

## 8. Risks and Open Questions

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **AAP access delayed** | Phase B slides, but Phase A work is unaffected | Build everything locally first; deploy is scripted and fast |
| **Column-level schema not available** | Can't remap views to production tables | Placeholder schema still works for full demo; swap when ready |
| **Data Agent accuracy < 90%** | Poor user experience, low trust | Extensive sample queries, iterative tuning, show SQL for transparency |
| **Fabric capacity too small** | Mirroring or Data Agent throttled | Recommend F64 minimum; monitor usage, request scale-up if needed |
| **PostgreSQL WAL not enabled** | Can't use Fabric Mirroring | Must be confirmed before Phase B; alternative is scheduled Dataflow Gen2 |
| **Entra ID tenant restrictions** | Can't register apps or create service principals | Need AAP IT cooperation; identify admin contact early |

### Open Questions

| # | Question | Impact | Who Answers |
|---|----------|--------|-------------|
| 1 | Should the Data Agent query through the semantic model or directly against views? | Affects accuracy on calculated measures | Architect (test both approaches) |
| 2 | Does AAP want the web app in their tenant or a Microsoft demo tenant? | Changes Entra ID config and deployment target | AAP + Dave |
| 3 | What Fabric capacity SKU is available? (F64, F128, etc.) | Determines mirroring throughput and concurrent queries | AAP |
| 4 | Is there a CrowdTwist API or is all data already in PostgreSQL? | Affects points/tier data availability in Lakehouse | AAP |
| 5 | Do they want Power BI reports as part of the POC, or is the web app sufficient? | Changes scope — adds report development if yes | Dave + AAP |
| 6 | Is there an existing Azure subscription we deploy the web app into? | Bicep deployment target | AAP |

---

## 9. What We Can Demo at Each Stage

| Milestone | What We Show | When |
|-----------|-------------|------|
| **End of Week 1** | Working React chat UI with mock Data Agent responses | Phase A |
| **End of Week 2** | Full web app with auth, backend API, and mock agent | Phase A |
| **End of Week 3** | Complete package: all scripts, configs, app, tests — ready to deploy | Phase A |
| **Phase B + 2 days** | Live demo: real data, real queries, real answers | Phase B |
| **Phase B + 1 week** | UAT-ready: marketing users testing with their own questions | Phase B |

**The Phase A demos are powerful even without AAP access** — they show the complete user experience and prove the team can deliver. Dave can use these to build confidence with AAP stakeholders while waiting for environment access.

---

## 10. Repository Structure (Actual)

```
AAP Data Agent POC/
├── docs/                           # Architecture, plans, schema docs
├── scripts/
│   ├── setup-workspace.ps1         # Fabric workspace provisioning
│   ├── deploy-views.py             # Deploy semantic views to Lakehouse
│   ├── create-semantic-model.py    # Deploy Power BI semantic model
│   ├── configure-linguistic-schema.py # Deploy AI synonyms + instructions
│   ├── upload-notebook.py          # Upload notebook to Fabric workspace
│   └── drop-legacy-tables.py       # Clean up stale Delta tables
├── config/
│   └── (per-agent configs in agents/ folder)
├── agents/                         # 5 Fabric Data Agent persona configs
│   ├── customer-service/           # Pit Crew
│   ├── loyalty-program-manager/    # GearUp
│   ├── marketing-promotions/       # Ignition
│   ├── merchandising/              # PartsPro
│   └── store-operations/           # DieHard
├── notebooks/
│   ├── 01-create-sample-data.py    # Generate synthetic loyalty data
│   └── 02-data-sanity-check.py     # Validate data quality
├── web/                            # Vanilla JS SPA + config
│   ├── index.html
│   ├── config.js
│   ├── server.py                   # Local dev proxy server
│   └── staticwebapp.config.json    # Azure SWA routing + auth
├── api/
│   └── function_app.py             # Azure Functions backend (Python v2)
├── model/                          # Semantic model TMDL definitions
└── .github/
    └── workflows/
        └── azure-static-web-apps.yml  # CI/CD pipeline
```

---

**Document Owner:** Lead Architect  
**Last Updated:** July 2025  
**Status:** Phase A complete; Phase B awaiting AAP access
