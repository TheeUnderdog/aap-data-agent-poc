# Skill: SWA + Managed Functions (Python)

## When to Use

When deploying a vanilla SPA (no build step) with a Python API backend to Azure Static Web Apps.

## Pattern

```
project/
├── web/                          # app_location (static files)
│   └── staticwebapp.config.json  # Routing, auth, headers
├── api/                          # api_location (Azure Functions)
│   ├── function_app.py           # Python v2 model
│   ├── requirements.txt
│   ├── host.json
│   └── local.settings.json       # gitignored
└── .github/workflows/
    └── azure-static-web-apps.yml
```

## Key Config

### staticwebapp.config.json
- `navigationFallback.rewrite: "/index.html"` for SPA routing
- `routes: [{ "route": "/*", "allowedRoles": ["authenticated"] }]` to require login
- `auth.identityProviders.azureActiveDirectory` with `clientIdSettingName`/`clientSecretSettingName` (reference app settings, not hardcoded values)
- `responseOverrides.401` redirect to `/.auth/login/aad`

### Azure Functions (Python v2)
- `DefaultAzureCredential` for downstream API auth (managed identity in prod, CLI locally)
- `x-ms-client-principal` header (base64 JSON) for user identity from SWA auth
- `func.AuthLevel.ANONYMOUS` — SWA handles auth before requests reach Functions

### GitHub Actions Workflow
- `app_location: "web"`, `api_location: "api"`, `output_location: ""`
- Secret: `AZURE_STATIC_WEB_APPS_API_TOKEN`

## Gotchas

1. **SSE streaming:** Functions v2 Consumption doesn't support generator-based streaming. Accumulate events and return as batch. Use Flex Consumption for true streaming.
2. **Cold starts:** Assistant caches and in-memory state are lost on cold start. Use external cache (Redis) if persistence matters.
3. **local.settings.json:** Must be gitignored. Contains `FUNCTIONS_WORKER_RUNTIME: "python"`.
4. **MSIT tenant:** Use `msitapi.fabric.microsoft.com` not `api.fabric.microsoft.com`.
