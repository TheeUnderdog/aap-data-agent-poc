---
name: "fabric-agent-fetch-failure"
description: "Diagnose browser-level fetch failures in the AAP Fabric Data Agent web app."
domain: "error-handling"
confidence: "high"
source: "observed"
---

## Context
Use this when the browser shows `Failed to fetch` for an agent request in the AAP chat app.

## Patterns
- In proxy mode (`web/config.js` → `useProxy: true`), the browser does **not** call Fabric directly. It always posts to same-origin `/api/chat`.
- The string like `ignition` in `[AgentClient] Request to "ignition" failed` is the app's agent key, not the HTTP endpoint name.
- A browser `Failed to fetch` means JS never got an HTTP response. In this app, check proxy availability, ingress/proxy drops, worker timeouts, and auth/token acquisition stalls before response headers.
- `web/server.py` currently calls `get_fabric_token()` before returning the SSE response. If credential acquisition hangs, the browser waits with no headers and may end as `Failed to fetch`.
- Confirm deployment target. The active Flask/container path uses workspace `82f53636-206f-4825-821b-bdaa8e089893`; the legacy Functions path still references inactive workspace `e7f4acfe-90d7-4685-864a-b5f1216fe614`.

## Examples
- Client call path: `web/js/agent-client.js`
- Agent/workspace mapping: `web/config.js`
- Proxy implementation: `web/server.py`
- Legacy mismatch risk: `api/function_app.py`, `api/local.settings.json`
- Prior symptom evidence: `tests/cua/evidence/TEST_REPORT.md`

## Anti-Patterns
- Do not assume the Fabric agent ID is wrong just because the error string names `ignition`.
- Do not start with CORS as the primary suspect when the app is running in same-origin proxy mode.
- Do not ignore old workspace IDs in superseded code paths; stale deployment routing can send valid agent IDs to the wrong workspace.
