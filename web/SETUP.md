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
│  Fabric API: service principal (client_credentials)│
│                                                  │
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
  -e ENTRA_TENANT_ID=16b3c013-d300-468d-ac64-7eda0820b6d3 \
  -e FABRIC_WORKSPACE_ID=e7f4acfe-90d7-4685-864a-b5f1216fe614 \
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
   - **Supported account types:** Single tenant (FDPO)
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
    ENTRA_TENANT_ID=16b3c013-d300-468d-ac64-7eda0820b6d3 \
    FABRIC_WORKSPACE_ID=e7f4acfe-90d7-4685-864a-b5f1216fe614 \
    FABRIC_API_BASE=https://api.fabric.microsoft.com/v1

az containerapp secret set \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --secrets entra-client-secret=your-secret

az containerapp update \
  --name aap-loyalty-intelligence \
  --resource-group aap-poc-rg \
  --set-env-vars "ENTRA_CLIENT_SECRET=secretref:entra-client-secret"
```

## 5. Configure Fabric Workspace Access

The Flask backend accesses the Fabric Data Agent API using a service principal (`client_credentials` grant). The SP must have workspace-level access.

### Add the Service Principal to the Fabric Workspace

1. Go to [Fabric Portal](https://app.fabric.microsoft.com) → open workspace `e7f4acfe-90d7-4685-864a-b5f1216fe614`
2. Click **Manage access** (gear icon in workspace header)
3. Click **Add people or groups**
4. Search for the app registration name: **AAP Loyalty Intelligence** (client ID `176f52b8-fc6e-42d4-9f61-c1bceb21d5b4`)
5. Set the role to **Contributor**
6. Click **Add**

The service principal can now call the Fabric Data Agent API for this workspace.

> **Note:** For local development, `AzureCliCredential` or `InteractiveBrowserCredential` is used instead. Run `az login` then `python web/server.py`.

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
Browser --> /auth/login
        --> MSAL redirects to Entra ID login (openid + profile scopes)
        --> User authenticates with Entra ID account
        --> Entra ID redirects to /auth/callback
        --> Flask stores user identity in session
        --> Browser calls /api/chat
        --> Flask middleware validates session
        --> Flask acquires SP token (client_credentials for api.fabric.microsoft.com)
        --> Flask calls Fabric Data Agent API with SP token
        --> SSE response streamed back to browser
```

## Security

### Authentication Model

Users authenticate via Azure Entra ID (MSAL auth code flow with `openid` + `profile` scopes). This establishes user identity and creates a Flask session. Fabric Data Agent API calls use a service principal (`client_credentials` grant for `https://api.fabric.microsoft.com/.default`). The SP is registered in the FDPO tenant and added to the Fabric workspace as Contributor.

**Key principles:**

- **User identity via MSAL** — The auth code flow determines who is using the app. User info is stored in the Flask session cookie.
- **Fabric access via service principal** — All Fabric API calls use the SP's `client_credentials` token. The SP has Contributor access to the workspace.
- **Short-lived tokens** — SP access tokens expire in ~60 minutes and are refreshed automatically.
- **Session isolation** — Each user's session is stored in an encrypted Flask session cookie.

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
| `ENTRA_TENANT_ID` | No | `16b3c013-...` | FDPO tenant ID |
| `FABRIC_WORKSPACE_ID` | No | `e7f4acfe-...` | Fabric workspace GUID |
| `FABRIC_API_BASE` | No | `https://api.fabric.microsoft.com/v1` | Fabric API base URL |
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
