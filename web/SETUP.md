# Advance Insights — Setup & Deployment Guide

## Architecture

```
┌──────────────────────────────────────────────────┐
│        Azure Container Apps                      │
│                                                  │
│  Flask + gunicorn (single container)             │
│  ├── Static files (HTML/CSS/JS)                  │
│  ├── /api/chat → Fabric Data Agent proxy (SSE)   │
│  ├── /api/user → Authenticated user info         │
│  ├── /auth/*  → MSAL login/callback/logout       │
│  └── /api/health → Health check                  │
│                                                  │
│  Fabric API calls use user-delegated tokens       │
│  (OBO flow)                                      │
└──────────────────────────────────────────────────┘
```

## 1. Local Development

The Flask server works for local dev — no Azure resources needed.

```bash
# Install dependencies
pip install -r web/requirements.txt

# Run (opens browser for Azure login)
python web/server.py
```

Opens at http://localhost:5000. In local mode, MSAL auth is disabled — the server uses `AzureCliCredential` (if `az login` was run) or `InteractiveBrowserCredential` for Fabric API calls directly.

## 2. Docker Build & Test

Docker **requires** an Entra app registration (MSAL auth). Without it, the container has no way to authenticate users — there's no browser inside Docker for interactive login, and `az login` tokens aren't available.

```bash
# Build the container image
docker build -t aap-loyalty-intelligence ./web

# Run with MSAL auth (required for Docker)
docker run -p 8000:8000 \
  -e ENTRA_CLIENT_ID=your-client-id \
  -e ENTRA_CLIENT_SECRET=your-secret \
  -e ENTRA_TENANT_ID=72f988bf-86f1-41af-91ab-2d7cd011db47 \
  -e FABRIC_WORKSPACE_ID=82f53636-206f-4825-821b-bdaa8e089893 \
  aap-loyalty-intelligence
```

Open http://localhost:8000 → you'll be redirected to Microsoft login → sign in → use the app. The MSAL auth code flow handles everything through the browser you're already using.

## 3. Create Azure Container App

### Via Script (recommended)

```bash
# PowerShell
.\scripts\deploy-web.ps1

# Bash
./scripts/deploy-web.sh
```

The script creates the resource group, Container App Environment, and Container App with managed identity. It's idempotent — safe to re-run.

### Via Azure CLI (manual)

```bash
# Create environment
az containerapp env create \
  --name aap-app-env \
  --resource-group aap-poc-rg \
  --location eastus2

# Create container app
az containerapp create \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --environment aap-app-env \
  --image ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest \
  --target-port 8000 \
  --ingress external \
  --system-assigned \
  --cpu 0.5 --memory 1Gi \
  --min-replicas 1 --max-replicas 10
```

## 4. Configure Entra ID Authentication

### Register an App

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. **New registration:**
   - **Name:** `Advance Insights`
   - **Supported account types:** Single tenant (MSIT)
   - **Redirect URI:** Web → `https://YOUR-APP.azurecontainerapps.io/auth/callback`
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Go to **Certificates & secrets** → **New client secret** → copy the value

### Set Environment Variables

```bash
az containerapp update \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --set-env-vars \
    ENTRA_CLIENT_ID=your-client-id \
    ENTRA_TENANT_ID=72f988bf-86f1-41af-91ab-2d7cd011db47 \
    FABRIC_WORKSPACE_ID=82f53636-206f-4825-821b-bdaa8e089893 \
    FABRIC_API_BASE=https://msitapi.fabric.microsoft.com/v1

az containerapp secret set \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --secrets entra-client-secret=your-secret

az containerapp update \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --set-env-vars "ENTRA_CLIENT_SECRET=secretref:entra-client-secret"
```

## 5. Configure Fabric API Permissions (OBO Auth)

The Flask backend calls the Fabric Data Agent API **on behalf of the signed-in user** — no managed identity is needed for data access. The user's own credentials flow end-to-end.

### Add Delegated Permissions to the App Registration

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Select the **Advance Insights** app registration
3. Go to **API permissions** → **Add a permission**
4. Select **APIs my organization uses** → search for **"Power BI Service"**
5. Select **Delegated permissions** (not Application permissions)
6. Select the needed scopes:
   - `Dataset.Read.All`
   - `Workspace.Read.All`
   - `Item.Execute.All` (for Data Agent queries)
7. Click **Add permissions**
8. Click **Grant admin consent for MSIT** (requires admin)

### Fabric Workspace Access

Each user who will use the app must have at least **Viewer** (or **Contributor**) access to the Fabric workspace. The app cannot access data the user cannot access — there is no service account fallback.

> **Note:** For local development, `InteractiveBrowserCredential` is used directly — the same user-delegated model. Run `python web/server.py` and authenticate via browser.

## 6. Deployment (CI/CD)

Deployments are automatic via GitHub Actions:

- **Push to `master`** → builds Docker image, pushes to ghcr.io, deploys to Container App

The workflow is at `.github/workflows/azure-container-apps.yml`.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Azure service principal JSON for `az login` |

### Manual Deployment

```bash
# Build and push
docker build -t ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest ./web
docker push ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest

# Deploy
az containerapp update \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --image ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest
```

## 7. Auth Flow (Production)

```
Browser → /auth/login
       → MSAL redirects to Entra ID login page (requesting Fabric scopes)
       → User authenticates with @microsoft.com account
       → Entra ID redirects to /auth/callback
       → Flask acquires tokens via auth code flow, caches in session
       → Browser calls /api/chat (relative URL)
       → Flask middleware validates session
       → Flask calls acquire_token_silent (user's delegated Fabric token)
       → Flask calls Fabric Data Agent API with user's token
       → SSE response streamed back to browser
```

## Security

### User-Delegated Authentication (OBO)

This application uses an **On-Behalf-Of (OBO)** pattern — the user's own Azure Entra ID credentials flow end-to-end from the browser to the Fabric Data Agent API. The application itself has **zero standing access** to any data.

**Key principles:**

- **No service accounts** — The app never authenticates as itself to access data. Every Fabric API call uses the signed-in user's delegated token.
- **Least privilege** — Users can only query data they are individually authorized to access in Fabric. If a user doesn't have Contributor access to the workspace, the query fails.
- **No managed identity for data** — The Container App's managed identity (if enabled) is only used for infrastructure tasks (pulling container images, reading Key Vault secrets). It is never used to call the Fabric Data Agent API.
- **Token cache isolation** — Each user's MSAL token cache is stored in their encrypted Flask session cookie. Users cannot access each other's tokens.
- **Short-lived tokens** — Access tokens expire in ~60 minutes. Refresh tokens are used via `acquire_token_silent` to get fresh access tokens without re-authentication.

### Production Considerations

| Concern | POC Approach | Production Recommendation |
|---------|-------------|--------------------------|
| Token cache | Flask cookie session | Redis or distributed cache |
| Session secret | Random per-restart | Azure Key Vault secret |
| HTTPS | Container Apps built-in | Same (TLS terminated at ingress) |
| Token encryption | Flask session signing | Add encryption layer |
| Audit logging | Console output | Azure Monitor / Log Analytics |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENTRA_CLIENT_ID` | Prod | *(none)* | Entra ID app registration client ID |
| `ENTRA_CLIENT_SECRET` | Prod | *(none)* | Entra ID app registration client secret |
| `ENTRA_TENANT_ID` | No | `72f988bf-...` | MSIT tenant ID |
| `FABRIC_WORKSPACE_ID` | No | `82f53636-...` | Fabric workspace GUID |
| `FABRIC_API_BASE` | No | `https://msitapi.fabric.microsoft.com/v1` | Fabric API base URL |
| `SESSION_SECRET` | No | *(random)* | Flask session signing key |
| `PORT` | No | `5000` | Local dev server port |

## File Structure

```
web/                          # Single-container app
├── Dockerfile                # Python 3.11 + gunicorn
├── requirements.txt          # Python dependencies
├── server.py                 # Flask app (API + static files + auth)
├── index.html                # SPA entry point
├── config.js                 # Agent config (workspace, agent IDs)
├── css/                      # Stylesheets
├── js/                       # Application JavaScript
└── img/                      # Images & icons

api/                          # Azure Functions (superseded, kept for reference)
├── function_app.py           # Python v2 — chat, user, health endpoints
├── requirements.txt          # Python dependencies
└── host.json                 # Functions host config
```
