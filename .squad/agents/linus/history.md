# Linus — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** React/TypeScript, Azure Static Web Apps, MSAL
- **Key requirement:** Simple, clean chat interface for marketing team. No training needed. Must display tabular results and natural language responses.
- **Customer context:** Marketing team users — not developers. Needs to be intuitive.

## Learnings

### Responsive Design Implementation (2026-07)
- **Breakpoints:** Desktop (≥1024px baseline), Tablet (768–1023px), Mobile (<768px), Small mobile (<375px)
- **Approach:** Desktop-first with cascading `max-width` media queries — preserves existing desktop layout as baseline
- **Key patterns:**
  - Tab strip: horizontal scroll with `scroll-snap-type: x mandatory` on mobile; tab descriptions hidden below tablet
  - Sample questions: flexbox column stack on mobile (vertical list vs grid)
  - Input bar: sticky bottom on mobile with `env(safe-area-inset-bottom)` for iPhone notch
  - Message input: `font-size: 16px` on mobile prevents iOS auto-zoom
  - `100dvh` (dynamic viewport height) handles mobile browser chrome (address bar)
  - All touch targets ≥44px on mobile (tabs, send button, sign-out, sample questions)
  - Tables: horizontal scroll with `-webkit-overflow-scrolling: touch`
  - Copy button: always visible (opacity 0.6) on touch devices since no hover
  - Login button: full-width on mobile for easy thumb tap
- **Files modified:** `web/css/app.css` (responsive media queries added, base layout dvh)
- **No JS changes needed** — all responsive behavior handled via CSS media queries

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

### Mobile Hamburger Menu + New Chat + Reasoning Sidebar (2025-01-24)
- **Task 1: Hamburger menu JavaScript** — Completed
  - Added `toggleSidebar()` and `closeSidebar()` global functions
  - Tab clicks auto-close sidebar on mobile
  - `#active-agent-label` updates on agent switch (shows current agent name when tabs hidden)
  - Escape key closes sidebar
  - Sidebar overlay (`.sidebar-overlay`) toggles with sidebar
  - Mobile CSS already in place — just wired up the JS
- **Task 2: "New Chat" button** — Completed
  - Added icon button in `top-bar-right` with plus icon
  - `handleNewChat()` clears current agent's chat history and re-renders welcome screen
  - Styled via `.btn-icon` (similar to reasoning toggle)
  - Subtle but accessible — fits AAP brand
- **Task 3: Reasoning / Chain-of-Thought sidebar** — Completed
  - **UI:** Fixed right sidebar (~360px desktop, full-width mobile), slides in via `transform: translateX(100%)`
  - **Toggle:** Icon button (info/lightbulb icon) in top-bar-right
  - **Layout:** Header with title + close button, scrollable steps container
  - **Step types:** `routing`, `agent-call`, `agent-response`, `thinking`, `error` — each color-coded
  - **Data model:** `reasoningSteps[]` with `{ type, agent, message, timestamp, duration }`
  - **Rendering:** Auto-scrolls to bottom, fade-in animations, timestamps in monospace
  - **Integration points:**
    - `app.js:sendMessage()` — clears steps, adds initial "Analyzing query..." step, tracks API call timing
    - `executive.js:askCrewChief()` — adds routing decision, per-agent call tracking, synthesis step
    - Exposed `window.addReasoningStep()` and `window.completeLastReasoningStep()` for cross-file use
  - **Mobile:** Full-width slide-over from right, same top offset as desktop
  - **Current state:** Scaffold working with basic steps. Richer reasoning data will come as backend integration deepens.
- **Files modified:**
  - `web/index.html` — added reasoning sidebar HTML, icon buttons in top-bar
  - `web/css/app.css` — reasoning panel styles, btn-icon styles, mobile overrides
  - `web/js/app.js` — hamburger menu, new chat, reasoning panel state/rendering
  - `web/js/executive.js` — reasoning hooks for Crew Chief routing
- **Architecture notes:**
  - Reasoning panel is stateless per query — clears on new message send
  - Uses vanilla JS event-driven pattern (global functions exposed on `window`)
  - Designed to scale — as agent-client.js evolves to emit richer SSE events, reasoning steps can show SQL queries, data retrieved, etc.
  - No framework dependencies — keeps bundle small and perf fast for mobile

