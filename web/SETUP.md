# Advance Insights — Auth & Deployment Setup

## 1. Register an Entra ID Application

1. Go to [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
3. Configure:
   - **Name:** `Advance Insights` (or any name you prefer)
   - **Supported account types:** "Accounts in this organizational directory only" (single tenant)
   - **Redirect URI:** Select **Single-page application (SPA)** and enter:
     - `http://localhost:8080` (for local dev)
4. Click **Register**
5. Note the **Application (client) ID** and **Directory (tenant) ID** from the Overview page

### Add Additional Redirect URIs (for Azure deployment)

1. Go to **Authentication** in the left nav
2. Under **Single-page application → Redirect URIs**, add:
   - `https://YOUR-CONTAINER-APP.azurecontainerapps.io` (Azure Container Apps URL)
   - Any other URLs where the app will be hosted

### Grant API Permissions

1. Go to **API permissions** in the left nav
2. Click **Add a permission** → **APIs my organization uses**
3. Search for **Power BI Service** (this covers Fabric APIs)
4. Select **Delegated permissions** → check:
   - `Dataset.Read.All`
   - `Workspace.Read.All`
5. Click **Add permissions**
6. Click **Grant admin consent** (requires admin privileges)

## 2. Fill in config.js

Open `web/config.js` and replace the placeholders:

```javascript
workspaceId: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  // From Fabric portal URL

msalConfig: {
    auth: {
        clientId: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  // From step 1
        authority: "https://login.microsoftonline.com/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  // Tenant ID
        redirectUri: window.location.origin
    },
    ...
},
```

### Finding Your Workspace ID

1. Open [Microsoft Fabric Portal](https://app.fabric.microsoft.com)
2. Navigate to your workspace
3. The URL contains the workspace ID: `https://app.fabric.microsoft.com/groups/WORKSPACE_ID/...`

### Finding Agent GUIDs

1. In the Fabric portal, go to each published Data Agent
2. The URL contains the agent ID: `.../items/AGENT_ID/...`
3. Fill in each agent's `id` field in config.js

## 3. Run Locally

### Option A: Python HTTP Server (quickest)
```bash
cd web
python -m http.server 8080
```
Open http://localhost:8080

### Option B: Docker Container
```bash
cd web
docker build -t aap-insights .
docker run -p 8080:80 aap-insights
```
Open http://localhost:8080

## 4. Deploy to Azure Container Apps

```bash
# Build and push
cd web
docker build -t aap-insights .

# Deploy (one command)
az containerapp up \
  --name aap-insights \
  --source . \
  --target-port 80 \
  --ingress external

# Note the URL from the output, add it as a redirect URI in Entra ID
```

## Auth Flow Summary

```
Browser → MSAL.js redirect to Microsoft login
       → User authenticates with Entra ID
       → Token returned for api.fabric.microsoft.com scope
       → Browser calls Fabric Data Agent REST API directly
       → No backend proxy needed
```
