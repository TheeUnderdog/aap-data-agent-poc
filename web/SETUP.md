# Advance Insights — Setup & Deployment Guide

## Architecture

```
┌──────────────────────────────────────────────────┐
│          Azure Static Web Apps (SWA)             │
│                                                  │
│  web/          →  Static frontend (HTML/CSS/JS)  │
│  api/          →  Managed Azure Functions (Python)│
│  /.auth/*      →  Built-in Entra ID auth         │
│                                                  │
│  Functions call Fabric Data Agent API via         │
│  DefaultAzureCredential (managed identity)       │
└──────────────────────────────────────────────────┘
```

## 1. Local Development

The existing Flask proxy still works for local dev — no Azure resources needed.

```bash
# Install dependencies
pip install flask flask-cors azure-identity

# Run (opens browser for Azure login)
python web/server.py
```

Opens at http://localhost:5000. The proxy handles auth and forwards `/api/chat` to the Fabric Data Agent.

## 2. Create Azure Static Web App

### Via Azure Portal

1. Go to [Azure Portal → Static Web Apps](https://portal.azure.com/#create/Microsoft.StaticApp)
2. Configure:
   - **Resource Group:** Choose or create one
   - **Name:** `advance-insights` (or your preferred name)
   - **Plan type:** Free (sufficient for POC)
   - **Region:** Pick one close to your team
   - **Source:** GitHub
   - **Organization / Repository / Branch:** Point to this repo's `main` branch
3. **Build Details:**
   - **Build Preset:** Custom
   - **App location:** `web`
   - **API location:** `api`
   - **Output location:** *(leave empty)*
4. Click **Review + create** → **Create**

Azure will automatically add a GitHub Actions workflow secret (`AZURE_STATIC_WEB_APPS_API_TOKEN`) and create the deployment workflow. The workflow file at `.github/workflows/azure-static-web-apps.yml` is already configured.

### Via Azure CLI

```bash
az staticwebapp create \
  --name advance-insights \
  --resource-group YOUR_RG \
  --source https://github.com/YOUR_ORG/YOUR_REPO \
  --branch main \
  --app-location "web" \
  --api-location "api" \
  --output-location "" \
  --login-with-github
```

## 3. Configure Entra ID Authentication

SWA has built-in auth. To restrict to your Entra ID tenant:

### Register an App (if not already done)

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. **New registration:**
   - **Name:** `Advance Insights`
   - **Supported account types:** Single tenant
   - **Redirect URI:** Web → `https://YOUR-SWA-NAME.azurestaticapps.net/.auth/login/aad/callback`
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Go to **Certificates & secrets** → **New client secret** → copy the value

### Add Settings to SWA

In the Azure Portal, go to your Static Web App → **Configuration** → **Application settings**:

| Setting | Value |
|---------|-------|
| `AAD_CLIENT_ID` | Your app registration client ID |
| `AAD_CLIENT_SECRET` | Your app registration client secret |
| `FABRIC_WORKSPACE_ID` | `82f53636-206f-4825-821b-bdaa8e089893` |
| `FABRIC_API_BASE` | `https://msitapi.fabric.microsoft.com/v1` |

The `staticwebapp.config.json` references `AAD_CLIENT_ID` and `AAD_CLIENT_SECRET` for the Entra ID provider. The `openIdIssuer` is pre-configured for the MSIT tenant.

## 4. Set Up Managed Identity for Fabric API

The Azure Functions backend needs to call the Fabric Data Agent API. In production, this uses a managed identity:

1. Go to your Static Web App → **Identity** → **System assigned** → **On** → **Save**
2. Copy the **Object ID** of the managed identity
3. In [Fabric Portal](https://msit.powerbi.com), go to the workspace → **Manage access**
4. Add the managed identity (by Object ID) as a **Contributor**
5. Grant the managed identity the `Fabric.ReadWrite.All` scope (or the appropriate Fabric API permissions)

> **Note:** For local Functions development, `DefaultAzureCredential` falls back to Azure CLI credentials. Run `az login` first.

## 5. Deployment

Deployments are automatic via GitHub Actions:

- **Push to `main`** → deploys to production
- **Pull request** → deploys a staging preview environment
- **PR closed** → staging environment is cleaned up

The workflow is at `.github/workflows/azure-static-web-apps.yml`.

### Manual Deployment

```bash
# Install SWA CLI
npm install -g @azure/static-web-apps-cli

# Deploy
swa deploy --app-location web --api-location api --deployment-token YOUR_TOKEN
```

## 6. Auth Flow (Production)

```
Browser → SWA built-in auth (/.auth/login/aad)
       → User authenticates with Entra ID
       → SWA sets auth cookie + x-ms-client-principal header
       → Browser calls /api/chat (relative URL)
       → SWA routes to managed Azure Functions
       → Functions use DefaultAzureCredential (managed identity)
       → Functions call Fabric Data Agent API
       → SSE response streamed back to browser
```

## File Structure

```
web/                          # Static frontend (SWA app_location)
├── staticwebapp.config.json  # SWA routing, auth, headers
├── index.html                # SPA entry point
├── config.js                 # Agent config (workspace, agent IDs)
├── css/                      # Stylesheets
├── js/                       # Application JavaScript
├── img/                      # Images & icons
└── server.py                 # Local dev proxy (not deployed)

api/                          # Azure Functions (SWA api_location)
├── function_app.py           # Python v2 — chat, user, health endpoints
├── requirements.txt          # Python dependencies
├── host.json                 # Functions host config
└── local.settings.json       # Local dev settings (gitignored)
```
