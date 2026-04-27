# Auth Simplification — DefaultAzureCredential

**Date:** 2026-07
**Author:** Basher (Backend Dev)
**Status:** Implemented

## Decision
Replace MSAL auth code flow with stateless `DefaultAzureCredential` for all environments.

## Context
- App and Fabric Data Agents will run in the same FDPO tenant when deployed
- Local dev is Dave's corporate laptop with `az login` to Microsoft tenant
- No cross-tenant auth needed; no user-facing login flow needed for POC

## Changes
- Removed: MSAL imports, login/callback/logout routes, session-based token handling, IS_PRODUCTION flag
- Added: Single `get_fabric_token()` using `DefaultAzureCredential`
- Docker mounts `~/.azure` for local credential passthrough
- Removed dependencies: msal, requests, PyJWT

## Impact
- **Linus (Frontend):** No `/auth/login` redirect exists anymore. Auth status endpoint always returns `authenticated: true`. Frontend login button can be removed or hidden.
- **Danny (Architecture):** This is a POC simplification. Production deployment with multi-user auth would need to reintroduce user-level auth (not necessarily MSAL — could be Container Apps built-in auth).
- **Deployment:** Azure Container Apps needs managed identity with Fabric workspace Contributor role.
