# Orchestration Log: Basher — Azure Static Web Apps Infrastructure

**Timestamp:** 2026-04-25T02:23:05Z  
**Agent:** Basher (Backend Dev)  
**Session Mode:** background  
**Task:** Create SWA deployment infrastructure for AAP Data Agent POC web app  

## Summary

Full Azure Static Web Apps stack deployed. Includes SWA routing config, Python v2 Azure Functions backend, GitHub Actions CI/CD workflow, and complete SETUP documentation.

## Files Created

1. **`web/staticwebapp.config.json`** — SWA routing, Entra ID auth (MSIT tenant), security headers (CSP, X-Frame-Options), role-based access control
2. **`api/function_app.py`** — Python v2 Azure Functions: `/api/chat` (SSE proxy), `/api/user` (identity), `/api/health`
3. **`api/requirements.txt`, `api/host.json`, `api/local.settings.json`, `api/.funcignore`** — Functions v2 scaffolding
4. **`.github/workflows/azure-static-web-apps.yml`** — GitHub Actions CI/CD (app + managed Functions deployment)
5. **`web/SETUP.md`** — Complete deployment guide (portal + CLI, Entra ID registration, managed identity binding)
6. **Updated `web/config.js`** — Clarified `useProxy: true` works for both local and SWA
7. **Updated `.gitignore`** — Added Functions artifacts

## Architecture

- **Auth:** Entra ID via SWA (x-ms-client-principal header)
- **Fabric API:** DefaultAzureCredential (managed identity in prod, CLI creds locally)
- **Streaming:** Functions v2 Consumption accumulates events (true streaming needs Flex Consumption)
- **Decision:** SWA chosen over Container Apps (simpler, built-in auth, no Service Tree ID)

## Key Patterns

- Assistant cache per-instance (Functions cold-start, no persistent cross-request)
- SSE proxy mirrors local `web/server.py` logic
- `.env.fabric` isolation keeps secrets local

## Commit

Committed as b18b4ff (as noted in spawn manifest)

## Integration Impact

- **Linus (Frontend):** No code changes; `useProxy: true` + relative URLs work in both local and prod
- **Livingston (Data Engineer):** No schema changes; Fabric API via managed identity
- **Danny (Architecture):** Aligns with decision #4 (Static Web Apps + managed Functions)

## Known Limitation

⚠️ Functions v2 Consumption doesn't support true SSE streaming. Chat responses accumulated and returned as batch. Acceptable for POC; upgrade to Flex Consumption if real-time streaming needed.
