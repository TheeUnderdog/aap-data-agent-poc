# Linus — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** React/TypeScript, Azure Static Web Apps, MSAL
- **Key requirement:** Simple, clean chat interface for marketing team. No training needed. Must display tabular results and natural language responses.
- **Customer context:** Marketing team users — not developers. Needs to be intuitive.

## Learnings

### Azure Static Web Apps Backend Ready (2026-04-25)
- **Basher status:** Full SWA deployment stack completed — ready for Linus integration
- **Backend surface:**
  - `POST /api/chat` — SSE proxy to Fabric Data Agent (request body: `{ query: "...", conversation_history: [...] }`, response: server-sent events)
  - `GET /api/user` — Returns authenticated user info (decoded from `x-ms-client-principal` SWA header)
  - `GET /api/health` — Liveness probe
- **Auth:** Entra ID SSO handled by SWA layer — no MSAL needed on backend
- **Local dev:** Use `web/server.py` with `useProxy: true` in `web/config.js` (unchanged from current pattern)
- **Prod deployment:** Set `useProxy: true` targeting `https://<swa-domain>/api/chat` — no code changes needed
- **Setup guide:** See `web/SETUP.md` for portal creation, Entra ID app registration, managed identity binding
- **Frontend can now:**
  - Target production SWA URLs immediately after portal setup
  - Continue local dev with `web/server.py` unchanged
  - Call `/api/user` to get authenticated user context
  - Stream chat responses via `/api/chat` (same SSE interface as local server)

