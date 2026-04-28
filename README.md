# AAP Data Agent POC

A Microsoft Fabric Data Agent proof-of-concept for **Advance Auto Parts** — enables the marketing team to query rewards/loyalty data using natural language through a chat web app.

## Architecture

![AAP Data Agent Architecture](web/img/architecture.svg)

![Web App — Crew Chief orchestrator with multi-agent response](web/img/web-app-screenshot.png)

```
Azure PostgreSQL  →  Fabric Mirroring  →  OneLake Lakehouse
                                              ↓
                                      Fabric Data Agent (NL → DAX)
                                              ↓
                                      Python API (Flask)
                                              ↓
                                      Web App (HTML/JS chat UI)
```

**Data flow:** PostgreSQL → Fabric Mirroring → Lakehouse → Semantic Model → Data Agent → Flask API → Chat UI

## What's Inside

```
web/               Vanilla JS SPA + Flask backend — chat UI with 6 agent tabs
  server.py        Flask app (API proxy + Entra ID auth + SSE streaming)
  js/auth.js       MSAL.js 2.x wrapper (login, token acquisition, refresh)
  js/app.js        SPA controller (routing, UI state, agent switching)
  js/agent-client.js  Fabric Data Agent API client (SSE streaming)
  config.js        App configuration (auth mode, workspace ID, agent GUIDs)
  docs.html        Interactive documentation page (Mermaid diagrams)
agents/            5 Fabric Data Agent configs + instruction files
reports/           Power BI PBIR report definition (LoyaltyOverview)
scripts/           Semantic model definition, sample data generator
notebooks/         Fabric notebooks for data pipeline
docs/              Architecture, schema, semantic model docs
config/            Environment and deployment configs
tests/cua/         CUA visual test suite — 42 Gherkin scenarios across 6 feature files
```

### Data Agents (6 tabs, 5 Fabric agents)

| Tab | Agent | Domain | Key Queries |
|-----|-------|--------|-------------|
| **Crew Chief** | *(client-side orchestrator)* | Routes queries to specialized agents | "Who should I ask about churn?" |
| **GearUp** | Loyalty Program Manager | Members, tiers, points, churn | "How many Platinum members?", "Churn risk breakdown" |
| **DieHard** | Store Operations | Stores, revenue, channels | "Top 5 stores by revenue", "In-store vs online mix" |
| **PartsPro** | Merchandising | Products, categories, SKUs | "Best-selling category?", "Bonus-eligible products" |
| **Ignition** | Marketing & Promotions | Campaigns, coupons, redemption | "Campaign ROI this quarter", "Redemption rate" |
| **Pit Crew** | Customer Service | CSR activities, member support | "Average tickets per day", "Most common issue type" |

### Semantic Model

- **10 tables:** loyalty_members, transactions, stores, products, coupons, coupon_rules, points_ledger, csr, csr_activities, audit_log
- **30+ DAX measures** across membership, revenue, points, store performance, and product domains
- **Direct Lake mode** from Fabric Lakehouse

**Linguistic synonyms** are configured on the model so natural language queries resolve correctly (e.g. "customers" → `loyalty_members`, "sales" → `transactions`, "VIP" → Platinum):

- **10 table synonym groups** — "customers", "sales", "parts", "campaigns", etc. map to the right tables
- **18 column synonym mappings** — "loyalty tier" → `tier`, "revenue" → `total`, "join date" → `enrollment_date`
- **7 value synonym groups** — "VIP"/"elite" → Platinum, "churned"/"lapsed" → inactive, "used"/"applied" → redeemed

See `scripts/configure-linguistic-schema.py` for the full synonym map.

**AI instructions** are embedded in the model's Copilot settings — business context, tier definitions (Bronze → Platinum with spend thresholds and points multipliers), points system rules, and calculation guardrails (e.g. "Revenue should ALWAYS filter to transaction_type = 'purchase'"). These guide the Data Agent's DAX generation so it gets domain-specific queries right.

**Per-agent instruction files** live in `agents/*/` — each of the 5 Fabric Data Agents has:
- **Persona & tone** — tailored for its audience (VP of Loyalty, Marketing Director, etc.)
- **Data access scope** — which tables the agent queries and how
- **Response format rules** — headline metrics first, markdown tables, actionable insights
- **Verified answer examples** — pre-validated Q&A pairs in `verified-answers-*.json`

## Quick Start

```bash
# Install Python deps
pip install flask flask-cors azure-identity

# Login to Azure (for Fabric API access)
az login

# Run local dev server
python web/server.py
# Opens at http://localhost:5000
```

No Azure deployment required. The Flask server serves both the static frontend and the API proxy. Authentication uses your `az login` credentials automatically.

## Authentication

All Fabric API access uses the **user's own credential** — the Data Agent executes queries under the authenticated user's identity (OBO pattern). Two auth paths are supported:

### Option 1: Direct Credential (Local Dev)

The user runs `az login` before starting the server. The server's `ChainedTokenCredential` resolves the user's identity and acquires Fabric tokens on their behalf.

```
User → az login → Server (AzureCliCredential) → Fabric Data Agent
```

**Credential chain fallback order:**
1. `ManagedIdentityCredential` — for Azure-hosted deployment
2. `AzureCliCredential` — **primary for local dev** (uses your `az login` session)
3. `DeviceCodeCredential` — headless/Docker fallback

No app registration, no login screen, no MSAL. Just `az login` and go.

### Option 2: MSAL Redirect (Production)

The app handles login via an Entra ID app registration. The browser redirects to Entra ID, MSAL acquires a Fabric-scoped access token, and the server forwards it to Fabric — true pass-through.

```
User → Browser Sign-In → Entra ID → MSAL token → Server → Fabric Data Agent
```

Requires an Entra ID app registration (`clientId` + `tenantId` in `config.js`). The MSAL.js 2.x wrapper in `web/js/auth.js` is fully built — fill in the config values to enable.

### Configuration

| Variable | Purpose | Required |
|----------|---------|----------|
| `FABRIC_WORKSPACE_ID` | Target Fabric workspace | Both modes |
| `ENTRA_TENANT_ID` | Entra tenant ID | MSAL mode only |
| `ENTRA_CLIENT_ID` | App registration client ID | MSAL mode only |

Toggle between modes via `useProxy` in `web/config.js` — `true` uses the server credential chain (Option 1), `false` enables MSAL browser auth (Option 2).

### Security Properties

- **User identity end-to-end** — user's credential reaches Fabric in both modes. No shared service accounts.
- **No stored secrets** — no client secrets, API keys, or service principal credentials for data access.
- **Short-lived tokens** — access tokens expire in ~1 hour with automatic renewal.
- **Fabric-managed permissions** — access control enforced by Fabric based on user identity.
- **HTTPS enforced** — Azure Static Web Apps provides built-in HTTPS in production.

## Fabric Workspace Setup

1. **Create workspace** in [Fabric Portal](https://msit.powerbi.com)
2. **Connect git** to this repo for git sync (semantic model, reports)
3. **Run sample data generator:** `python scripts/generate_sample_data.py`
4. **Load data** via notebooks in `notebooks/`
5. **Configure Data Agents** using configs in `agents/*/config.json`
6. **Deploy report** — `reports/LoyaltyOverview.Report/` syncs via git integration

## Key Docs

| Doc | What |
|-----|------|
| [Interactive Docs](web/docs.html) | Stakeholder-facing documentation page (served by Flask) |
| [Architecture](docs/architecture.md) | Full technical architecture (all 4 phases) |
| [Data Schema](docs/data-schema.md) | Placeholder schema, DDL, contract views |
| [Semantic Model](docs/semantic-model-architecture.md) | Model review, DAX measures, AI readiness |
| [Web Setup](web/SETUP.md) | Deployment guide (local + future Container Apps) |
| [CUA Tests](tests/cua/README.md) | Visual test suite — 42 Gherkin scenarios |
| [Report README](reports/LoyaltyOverview.Report/README.md) | PBIR report + verified answer mapping |

## Tech Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Frontend** | Vanilla HTML/CSS/JS | Single-page app — no build step, no framework. MSAL.js 2.x for browser auth. Mermaid.js for diagrams. |
| **Backend** | Flask (Python) | `web/server.py` — API proxy, SSE streaming, static file server |
| **Auth** | Azure Entra ID | `ChainedTokenCredential` (local) or MSAL redirect (production) |
| **Hosting (local)** | Flask dev server | `python web/server.py` at localhost:5000 |
| **Hosting (prod)** | Azure Static Web Apps | Built-in Entra ID auth integration, HTTPS, CDN |
| **Data Platform** | Microsoft Fabric | Lakehouse (Direct Lake), Semantic Model, Data Agent API |
| **Source DB** | Azure PostgreSQL | Mirrored to Fabric via Fabric Mirroring |
| **AI Layer** | Fabric Data Agent | NL → DAX query generation, per-agent instruction tuning |

## License

[MIT License](LICENSE) — Copyright © 2026 Dave Grobleski
