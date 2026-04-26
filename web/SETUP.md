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
│  Fabric API calls use managed identity           │
│  (DefaultAzureCredential)                        │
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

Opens at http://localhost:5000. In local mode, MSAL auth is disabled — the server uses `InteractiveBrowserCredential` for Fabric API calls directly.

## 2. Docker Build & Test

```bash
# Build the container image
docker build -t aap-loyalty-intelligence ./web

# Run locally (no auth — local dev mode)
docker run -p 8000:8000 aap-loyalty-intelligence

# Run with MSAL auth enabled
docker run -p 8000:8000 \
  -e ENTRA_CLIENT_ID=your-client-id \
  -e ENTRA_CLIENT_SECRET=your-secret \
  -e ENTRA_TENANT_ID=72f988bf-86f1-41af-91ab-2d7cd011db47 \
  -e FABRIC_WORKSPACE_ID=82f53636-206f-4825-821b-bdaa8e089893 \
  aap-loyalty-intelligence
```

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

## 5. Set Up Managed Identity for Fabric API

The Flask backend calls the Fabric Data Agent API. In production, this uses the Container App's managed identity:

1. The `--system-assigned` flag on container creation enables it automatically
2. Get the **Principal ID:** `az containerapp identity show --name aap-loyalty-intelligence --resource-group aap-poc-rg --query principalId -o tsv`
3. In [Fabric Portal](https://msit.powerbi.com), go to the workspace → **Manage access**
4. Add the managed identity (by Principal ID) as a **Contributor**

> **Note:** For local development, `DefaultAzureCredential` falls back to `InteractiveBrowserCredential`. Run `python web/server.py` and authenticate via browser.

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
       → MSAL redirects to Entra ID login page
       → User authenticates with @microsoft.com account
       → Entra ID redirects to /auth/callback
       → Flask stores user info in session cookie
       → Browser calls /api/chat (relative URL)
       → Flask middleware validates session
       → Flask uses DefaultAzureCredential (managed identity)
       → Flask calls Fabric Data Agent API
       → SSE response streamed back to browser
```

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
