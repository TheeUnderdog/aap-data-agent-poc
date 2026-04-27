# AAP Data Agent POC — Deployment Gaps Analysis

**Owner:** AAP POC Team  
**Date:** 2026-07  
**Status:** Complete  

---

## Executive Summary

The AAP Data Agent POC has **strong automation for the web layer** (Azure Static Web Apps, GitHub Actions CI/CD), but **significant manual work in the Fabric layer** (workspace setup, Data Agent configuration, PBIR report deployment). This gap analysis identifies all 14 deployment gaps, categorizes them by automation feasibility, and recommends a deployment sequence.

**Key Finding:** ~70% of deployment can be automated via REST APIs or CLI; ~30% requires manual portal work due to Fabric platform limitations.

---

## What's Automated Today

### 1. **Web Deployment — ✅ Fully Automated**
- **Scripts:** `scripts/deploy-web.ps1` (PowerShell) + `scripts/deploy-web.sh` (bash equivalent)
- **Coverage:**
  - Azure Static Web App creation + GitHub Actions integration
  - Entra ID app registration + client secret generation
  - Managed identity binding (system-assigned)
  - Application settings configuration
  - SWA auth configuration (`staticwebapp.config.json`)
- **Trigger:** `./scripts/deploy-web.ps1 -ResourceGroup "aap-poc-rg" -AppName "advance-insights" -GitHubRepoUrl "..."`
- **CI/CD:** GitHub Actions workflow (`.github/workflows/azure-static-web-apps.yml`) auto-runs on `main` push → builds SPA + manages Functions deployment

### 2. **Fabric Workspace & Lakehouse — ✅ Mostly Automated**
- **Scripts:** `scripts/setup-workspace.ps1` (REST API-based)
- **Coverage:**
  - Fabric workspace creation (or reuse if exists)
  - Lakehouse creation
  - Exports workspace/Lakehouse IDs to `.env.fabric` for downstream use
- **Trigger:** `./scripts/setup-workspace.ps1 -CapacityId "<guid>"`
- **Limitation:** Requires valid Fabric capacity GUID (user-provided)

### 3. **Semantic Views Deployment — ✅ Fully Automated**
- **Scripts:** `scripts/deploy-semantic-views.ps1` + `scripts/create-semantic-views.sql`
- **Coverage:** Deploys 9 contract views (member summary, transaction history, etc.) to Lakehouse SQL endpoint via T-SQL
- **Trigger:** `./scripts/deploy-semantic-views.ps1` (reads endpoint from `.env.fabric`)

### 4. **Semantic Model Deployment — ✅ Automated**
- **Scripts:** `scripts/create-semantic-model.py` + `scripts/bind-model-credentials.py`
- **Coverage:**
  - TMDL model upload via Fabric REST API
  - Credential binding (OAuth2) via Power BI REST API
  - Refresh trigger
- **Trigger:** `python scripts/create-semantic-model.py`
- **Limitation:** Deploying user must be workspace admin

### 5. **Linguistic Schema (CSR Synonyms) — ✅ Automated**
- **Scripts:** `scripts/configure-linguistic-schema.py`
- **Coverage:** Configures table/column/value synonyms for Data Agent language understanding
- **Trigger:** `python scripts/configure-linguistic-schema.py`

---

## Deployment Gaps — The 14 Issues

### ⚠️ **TIER P0 (Blocking — Needed for Basic Demo)**

#### Gap #1: **Fabric Git Sync Configuration** — Portal Only
- **What it is:** Enable git sync on the workspace to pull PBIR report + future notebooks from GitHub
- **Why manual:** Fabric Git Sync integration API doesn't exist; portal-only feature
- **Automation:** ❌ Cannot automate (API limitation)
- **Manual steps:**
  1. Fabric Portal → Workspace → Workspace settings → Git integration → Connect
  2. Authorize GitHub org, select repo, set main branch
  3. Enable auto-sync on folder (e.g., `/reports`, `/notebooks`)
- **Time estimate:** 10 minutes
- **Frequency:** Once per workspace

#### Gap #2: **PBIR Report Deployment** — Depends on Git Sync
- **What it is:** `reports/LoyaltyOverview.Report/definition.pbir` deploys to Fabric workspace
- **Why manual:** Requires Git Sync (Gap #1) to pull the report into the workspace
- **Automation:** ⚠️ Conditional — **Once Git Sync is configured, auto-pull is automatic** via workspace settings
- **Manual steps:** None (auto-synced once workspace is connected to GitHub)
- **Time estimate:** 0 minutes (automatic)
- **Status:** 🔴 Currently blocked — Dave reported "I don't see the PBI report in Fabric" because Git Sync isn't configured

#### Gap #3: **Data Agent Import into Workspace** — Portal Only
- **What it is:** Import 5 Fabric Data Agent `.fabric` files (`agents/*/config.json`) into the workspace
- **Why manual:** Data Agent deployment API is not publicly available; no REST endpoint exists
- **Automation:** ❌ Cannot automate (API limitation)
- **Manual steps:**
  1. Fabric Portal → Workspace → New → Data Agent
  2. Import each agent config JSON file (5 agents: Loyalty Manager, Store Ops, Merchandising, Marketing, CSR)
  3. Link each agent to semantic model "AAP Rewards Loyalty Model"
  4. Verify language model is enabled in workspace settings
- **Time estimate:** 20–30 minutes (5 agents × ~5 min each, including link + test)
- **Frequency:** Once per workspace (or when agent configs change)
- **Tools:** Automation candidate (a Playwright script could automate portal clicks)

#### Gap #4: **Managed Identity Workspace Access** — Manual + CLI Mixed
- **What it is:** Grant the SWA managed identity Contributor role in the Fabric workspace
- **Why semi-manual:** Fabric REST API doesn't support role assignment (Azure RBAC is different). Must use portal or future Fabric RBAC API
- **Automation:** ⚠️ Partial — **Can partially automate via Azure role assignment CLI**, but Fabric workspace role assignment requires portal
- **Manual steps:**
  1. Azure Portal → Static Web App → Identity → System assigned → copy **Object ID**
  2. Fabric Portal → Workspace → Manage access → Add → Paste Object ID → **Contributor**
- **Automation path:** Could use `az role assignment create` if Fabric exposes workspace as Azure resource (not yet standard)
- **Time estimate:** 5 minutes
- **Frequency:** Once per SWA deployment

#### Gap #5: **GitHub Actions SWA Deployment Token** — Partially Automated
- **What it is:** GitHub Actions workflow needs the SWA deployment token stored as a GitHub secret
- **Why semi-manual:** SWA creation adds the secret automatically, **BUT** if the secret expires or is rotated, it must be re-synced
- **Automation:** ✅ **First deployment: automatic** (SWA CLI adds secret to GitHub). **Rotation: manual** (copy new token from Azure Portal → GitHub Settings → Secrets)
- **Manual steps (if rotation needed):**
  1. Azure Portal → Static Web App → Deployment credentials → copy token
  2. GitHub → Settings → Secrets → update `AZURE_STATIC_WEB_APPS_API_TOKEN`
- **Time estimate:** 2 minutes (rotation only; initial deployment automatic)
- **Frequency:** Once on first deploy, then only if token rotated

#### Gap #6: **Azure Static Web App Managed Functions Configuration** — Automated
- **What it is:** Azure Functions backend (`api/function_app.py`) must be built and deployed to SWA
- **Automation:** ✅ **Fully automated** via GitHub Actions (`.github/workflows/azure-static-web-apps.yml`)
- **Trigger:** Auto-runs on every `main` push
- **Status:** No gap — already covered

---

### 🟡 **TIER P1 (Nice-to-Have — Improves the Experience)**

#### Gap #7: **Sample Data Load into Lakehouse** — Partially Automated
- **What it is:** Execute `notebooks/01-create-sample-data.py` to generate 10 tables (~337K rows) in the Lakehouse
- **Why partial:** Notebook upload via REST API works, **but** execution requires manual trigger or external orchestrator
- **Automation:** ⚠️ Partial — **Can upload + trigger via `scripts/run-notebook.py`**, but requires workspace to have a Fabric capacity
- **Manual steps (if using script):**
  1. `python scripts/run-notebook.py --notebook-path "notebooks/01-create-sample-data.py"`
  2. Monitor execution in Fabric Portal → Workspace → Notebooks
  3. Wait for completion (~2–5 minutes)
- **Automation path:** `scripts/run-notebook.py` already exists and calls Fabric Notebooks API
- **Time estimate:** 2–5 minutes (execution) + 1 minute (trigger)
- **Frequency:** Once per data refresh (or on-demand)

#### Gap #8: **Data Agent Language Model Configuration** — Manual Portal Only
- **What it is:** Enable language models (LLM) in workspace + set model inference options
- **Why manual:** Language model configuration API doesn't exist; only available in Fabric workspace settings portal
- **Automation:** ❌ Cannot automate (API limitation)
- **Manual steps:**
  1. Fabric Portal → Workspace → Workspace settings → Data Agent
  2. Enable "Language model services"
  3. Set inference to "Use Azure OpenAI" (or preferred LLM)
- **Time estimate:** 5 minutes
- **Frequency:** Once per workspace

#### Gap #9: **Semantic Model Directness Mode Verification** — Automated
- **What it is:** Verify semantic model is in DirectLake mode (queries Lakehouse directly without importing data)
- **Automation:** ✅ **Can verify + auto-switch via Power BI REST API**
- **Script:** (Does not exist yet; would be trivial to add to `create-semantic-model.py`)
- **Time estimate:** 1 minute (added to deployment script)
- **Frequency:** Once per model deployment

#### Gap #10: **Role-Based Access Control (RBAC) for Agents** — Portal Only
- **What it is:** Assign different Data Agents to different user groups (e.g., Store Ops agent → store managers only)
- **Why manual:** RBAC configuration in Fabric is portal-only; no API exists
- **Automation:** ❌ Cannot automate (API limitation)
- **Manual steps:** (Deferred for production; not required for POC)
- **Time estimate:** N/A
- **Frequency:** N/A

---

### 🔵 **TIER P2 (Future / Production)**

#### Gap #11: **PBI Report Scheduled Refresh** — Not Required for POC
- **What it is:** Schedule the PBIR report to refresh data on a cadence (e.g., daily at midnight)
- **Why deferred:** POC uses static sample data; no real data pipeline yet
- **Automation:** ✅ Can automate (Power BI Refresh REST API exists)
- **Time estimate:** 5 minutes (deferred to Phase 2)
- **Frequency:** N/A (POC only)

#### Gap #12: **Alerts & Monitoring Setup** — Not Required for POC
- **What it is:** Configure Azure Monitor alerts for function errors, SWA latency, Fabric API throttling
- **Why deferred:** Not required for demo; production concern
- **Automation:** ✅ Can automate (Azure Monitor REST APIs + Application Insights SDK)
- **Time estimate:** 15–30 minutes (deferred to Phase 2)
- **Frequency:** N/A (POC only)

#### Gap #13: **Multi-Workspace Deployment** — Not Required for POC
- **What it is:** Deploy to multiple Fabric workspaces (e.g., dev, staging, prod)
- **Why deferred:** Single workspace sufficient for POC
- **Automation:** ✅ Can automate (scripts are already parameterized)
- **Time estimate:** 10 minutes per workspace (deferred to Phase 2)
- **Frequency:** N/A (POC only)

#### Gap #14: **Infrastructure as Code (IaC) — ARM/Bicep** — Not Required for POC
- **What it is:** Define all Azure + Fabric resources in ARM templates or Bicep for reproducible infrastructure
- **Why deferred:** Scripts work; IaC hardening is production concern
- **Automation:** ✅ Can automate (Bicep templates exist for SWA + Azure Functions)
- **Time estimate:** 4–6 hours (deferred to Phase 2)
- **Frequency:** N/A (POC only)

---

## Gaps Summary Table

| Gap # | Issue | P | Automatable | Est. Time | Manual? | Blocker? |
|-------|-------|---|-------------|-----------|---------|----------|
| #1 | Fabric Git Sync Config | P0 | ❌ Portal only | 10 min | Yes | 🔴 YES |
| #2 | PBIR Report Deploy | P0 | ⚠️ Via Git Sync | 0 min | No | 🔴 Blocked by #1 |
| #3 | Data Agent Import | P0 | ❌ Portal only | 20–30 min | Yes | ✅ Can parallelize |
| #4 | Managed Identity Role | P0 | ⚠️ Partial (portal) | 5 min | Yes | ✅ Can parallelize |
| #5 | GitHub Secrets Sync | P0 | ✅ Auto on first run | 2 min (rotation only) | Conditional | ✅ Auto-handled |
| #6 | Functions Deployment | P0 | ✅ Full automation | N/A | No | ✅ Done |
| #7 | Sample Data Load | P1 | ⚠️ Script exists | 2–5 min | Yes (trigger) | ✅ Optional |
| #8 | Language Model Config | P1 | ❌ Portal only | 5 min | Yes | ✅ Optional |
| #9 | Model DirectLake Mode | P1 | ✅ Can verify | 1 min | No | ✅ Nice-to-have |
| #10 | RBAC for Agents | P1 | ❌ Portal only | N/A | N/A | ✅ Deferred |
| #11 | Report Refresh Schedule | P2 | ✅ Automatable | 5 min | No | N/A |
| #12 | Alerts & Monitoring | P2 | ✅ Automatable | 15–30 min | No | N/A |
| #13 | Multi-Workspace | P2 | ✅ Automatable | 10 min/ws | No | N/A |
| #14 | Infrastructure as Code | P2 | ✅ Automatable | 4–6 hrs | No | N/A |

---

## Recommended Deployment Sequence

### **Phase 1: Infrastructure (10–15 minutes, mostly automated)**

1. ✅ **Run `scripts/setup-workspace.ps1`** → Creates Fabric workspace + Lakehouse
   - Provides workspace ID + Lakehouse SQL endpoint in `.env.fabric`

2. ✅ **Run `scripts/deploy-semantic-views.ps1`** → Deploys 9 contract views
   - Validates Lakehouse SQL connectivity

3. ✅ **Run `python scripts/create-semantic-model.py`** → Deploys semantic model + credentials
   - Model ready for Data Agent configuration

4. ✅ **Run `python scripts/configure-linguistic-schema.py`** → Sets up CSR synonyms
   - Language model primed for agent understanding

5. 🟡 **Run `python scripts/run-notebook.py`** (optional) → Loads sample data
   - Can run during manual steps below to parallelize

---

### **Phase 2: Fabric Portal Setup (30–40 minutes manual work)**

*These must be done manually; can happen in parallel with Phase 1 steps 3–5.*

6. 🔴 **Configure Git Sync** (10 min) — **CRITICAL BLOCKER for report deployment**
   - Fabric Portal → Workspace → Settings → Git integration → Connect repo
   - Enable auto-sync on `/reports` folder

7. ✅ **PBIR Report Deploy** (0 min automatic after step 6)
   - Report syncs automatically once Git Sync is enabled
   - Verify in Fabric Portal → Workspace → Reports

8. 🟡 **Enable Language Models** (5 min) — Optional but recommended
   - Fabric Portal → Workspace → Workspace settings → Data Agent → Language model services

9. 🟡 **Grant Managed Identity Workspace Access** (5 min) — Required for API to call Fabric
   - Azure Portal → Static Web App → Identity → Copy Principal ID
   - Fabric Portal → Workspace → Manage access → Add as Contributor

---

### **Phase 3: Web Deployment (5–10 minutes automated)**

10. ✅ **Run `scripts/deploy-web.ps1`** → Creates SWA + Entra ID app + Functions
    - Idempotent — safe to re-run if step fails
    - Outputs SWA hostname + GitHub Actions workflow trigger

11. ✅ **GitHub Actions CI/CD** (2–3 minutes automatic)
    - Auto-runs on `main` push
    - Builds React SPA + deploys managed Functions
    - Workflow visible at GitHub → Actions tab

12. ✅ **Verify Web App** (2 min)
    - Visit `https://advance-insights.azurestaticapps.net` (or custom hostname)
    - Should redirect to Entra ID login → chat UI loads

---

### **Phase 4: Data Agent Configuration (20–30 minutes manual)**

13. 🔴 **Import 5 Data Agents** (20–30 min) — Manual portal work
    - Fabric Portal → Workspace → New → Data Agent → Import
    - Upload each `.fabric` file from `agents/*/config.json`
    - Link agents to semantic model "AAP Rewards Loyalty Model"
    - Test each agent with sample queries

---

## Automation Improvement Plan

### **Immediate (P0 — Unblock POC)** 

| Task | Owner | Est. Time | Notes |
|------|-------|-----------|-------|
| Add **Data Agent importer script** (Playwright) | Backend | 2–3 hrs | Automate Gap #3 portal clicks; would save 20 min per deployment |
| **Document manual steps** clearly (checklist) | Team | 1 hr | Create `docs/manual-deployment-checklist.md` |
| **Create master `deploy-all.ps1` script** | Team | 1–2 hrs | Orchestrator that runs all automated steps + prints manual checklist |

### **Phase 2 (Nice-to-Have)**

| Task | Owner | Est. Time | Notes |
|------|-------|-----------|-------|
| **Fabric Git Sync API** (monitor) | Team | Ongoing | Microsoft may ship this API; watch Fabric release notes |
| **Data Agent deployment API** (monitor) | Backend | Ongoing | Currently portal-only; would unblock Gap #3 automation |
| **Bicep templates** for Azure resources | Data Eng | 4–6 hrs | IaC for reproducible multi-environment deployments |
| **Automated RBAC assignment** | Backend | 2–3 hrs | Once Fabric RBAC API available |

### **Production (P2)**

- Scheduled refresh for semantic model + reports
- Azure Monitor integration + alerts
- Multi-workspace support
- Cross-region failover

---

## Known Limitations & Workarounds

### **Fabric REST API Gaps**

| Feature | Status | Workaround |
|---------|--------|-----------|
| **Workspace Git Sync** | ❌ No API | Manual portal config; stable once set |
| **Data Agent Import** | ❌ No public API | Playwright portal automation (future) |
| **Workspace RBAC** | ⚠️ Limited | Manual portal; Azure RBAC fallback limited |
| **Language Model Config** | ❌ No API | Manual portal; one-time setup |

### **GitHub / SWA Limitations**

| Feature | Status | Workaround |
|---------|--------|-----------|
| **SWA Managed Functions SSE Streaming** | ⚠️ Limited (v2 Consumption) | Chat responses batched; upgrade to Flex Consumption for true streaming (future) |
| **GitHub Secrets Sync to SWA** | ⚠️ Manual rotation | Secret added automatically on SWA creation; rotate manually if needed |

---

## Success Criteria (Post-Deployment)

- ✅ SWA is accessible at production URL
- ✅ Entra ID login works (users see chat UI)
- ✅ PBIR report visible in Fabric workspace
- ✅ All 5 Data Agents are importable + queryable
- ✅ Semantic model in DirectLake mode (queries live Lakehouse)
- ✅ Sample data loaded (~337K rows across 10 tables)
- ✅ API `/api/chat` endpoint responsive
- ✅ Managed identity has Fabric workspace access (API calls succeed)

---

## References

- **Architecture:** `docs/architecture.md`
- **Data Schema:** `docs/data-schema.md`
- **Web Deployment Script:** `scripts/deploy-web.ps1`
- **Fabric Provisioning:** `scripts/setup-workspace.ps1`
- **Semantic Views:** `scripts/create-semantic-views.sql`
- **Web Setup Guide:** `web/SETUP.md`


---

**Next Steps:** Run `scripts/deploy-all.ps1` (master orchestrator) — it will automate Phases 1–3 and print a checklist for Phase 4 manual work.
