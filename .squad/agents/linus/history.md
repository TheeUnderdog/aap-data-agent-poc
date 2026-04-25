# Linus — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** React/TypeScript, Azure Static Web Apps, MSAL
- **Key requirement:** Simple, clean chat interface for marketing team. No training needed. Must display tabular results and natural language responses.
- **Customer context:** Marketing team users — not developers. Needs to be intuitive.

## Learnings

### Icon Concept Corrections (2026-04-25)
- **Task:** Fixed 4 agent tab icons to correct concepts
- **Icon mapping:** gearup=gear, ignition=spark plug, partspro=piston, diehard=battery+bolt
- **Style:** Flat monochrome #1E1E1E metro design, recognizable at 26×26px
- **Technique:** Single-path silhouettes with `fill-rule="evenodd"` for negative-space detail
- **Files modified:** `web/img/gearup.svg`, `web/img/ignition.svg`, `web/img/partspro.svg`, `web/img/diehard.svg`
- **Outcome:** Committed as 3982aef

### Monochrome Metro Icon Redesign + Bebas Neue Font (2025-07-25)
- **Task:** Redesigned all 6 agent tab icons to flat monochrome metro style; switched wordmark font to Bebas Neue
- **Icon style rules:** Single fill color `#1E1E1E` only. No secondary colors, no gradients, no strokes with different colors. Pure silhouettes recognizable at 26×26px. viewBox="0 0 48 48" for all.
- **Icon design approach:** Use `fill-rule="evenodd"` for cutout/negative-space details within a single path (e.g., partspro document with text lines). Keeps SVG monochrome while allowing visual detail.
- **Icon mapping:** crew-chief=steering wheel, pit-crew=wrench, gearup=star, ignition=megaphone, partspro=document, diehard=storefront
- **Font:** Bebas Neue from Google Fonts — condensed geometric display font, closest to AAP's custom industrial typeface. Only has weight 400. Sized 26px desktop, 20px tablet, 18px small mobile.
- **Tab accent colors:** No CSS changes needed — `--active-accent` variable drives tab name color and active border. Monochrome icons are color-agnostic.
- **Files modified:** All 6 SVGs in `web/img/`, `web/index.html` (font import), `web/css/app.css` (wordmark styles + responsive sizes)

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

### Favicon Replacement (2025-07)
- **Task:** Replaced incorrect favicon with proper AAP racing/checkered flag icon
- **Design:** Dark circle (#1E1E1E) background, white waving checkered flag with 4-row checkerboard pattern (clip-path), white flagpole, 3 speed/motion streaks below flag with decreasing opacity
- **HTML fix:** `index.html` line 10 was pointing to `img/aap-logo.svg` — updated to `img/favicon.svg`
- **Files modified:** `web/img/favicon.svg` (rewritten), `web/index.html` (favicon link)
- **SVG technique:** Uses `clipPath` to mask checkerboard rectangles into a waving flag shape defined by cubic Bézier curves. Speed streaks use opacity fade (0.9 → 0.7 → 0.5) for depth
- **Brand note:** AAP brand identity = racing/motorsports. Checkered flag + speed streaks = core icon motif

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

### Colored Agent Tabs — Inline SVG + textColor (2025-07)
- **Task:** Make each agent tab always display in its brand color (icon AND text), not just when active
- **Approach:**
  - All 6 SVG icons updated: `fill="#1E1E1E"` → `fill="currentColor"` (kept `fill="white"` on diehard lightning bolt)
  - Added `textColor` property to each agent in `web/config.js` — separate from `accent` because some colors (e.g. GearUp yellow #FFCC00) need darkening for text readability (#B38600)
  - `buildTabs()` in `app.js` changed from `<img>` to inline SVG injection via `fetch()` + `innerHTML` — allows SVGs to inherit CSS `color` via `currentColor`
  - Tab color set via `tab.style.color = agent.textColor || agent.accent`
  - CSS uses `opacity: 0.7` (inactive) → `0.85` (hover) → `1.0` (active) instead of `color` overrides — preserves agent color at all states
  - `--active-accent` CSS variable still drives chat area styling (message bubbles, buttons) — unchanged
- **Key technique:** Inline SVG injection is clean for local files (no CORS). The `currentColor` + CSS `color` inheritance chain means one style property controls both icon and text color.
- **Files modified:** 6 SVGs in `web/img/`, `web/config.js`, `web/js/app.js`, `web/css/app.css`

### Inline SVG Injection for All Agent Icons (2025-07)
- **Task:** Fixed 5 locations where agent icons rendered black because `<img>` tags can't pass CSS `color` to SVG `fill="currentColor"` internals
- **Approach:**
  - Created shared `svgCache` object + `injectSvgIcon(container, agent)` async helper function
  - Fetches SVG text, caches it, injects via `innerHTML` into a `<div>` container with `style.color` set to `agent.textColor || agent.accent`
  - Replaced `<img>` with `<div>` + post-render injection at 5 locations: welcome icon, compact header icon (renderChat + addMessageToUI swap), message avatar, typing indicator avatar
  - Updated `buildTabs()` to use the shared cache (was previously doing raw `fetch()` without caching)
  - CSS updated: `.welcome-icon`, `.welcome-compact-icon` now flex containers; added `.avatar-icon` class with SVG child sizing; mobile media query updated
- **Key detail:** diehard.svg has hardcoded `fill="white"` on its lightning bolt — this is preserved since we only set `color` on the container (only `currentColor` fills are affected)
- **Fallback:** If SVG fetch fails, falls back to `<img>` tag (graceful degradation)
- **Files modified:** `web/js/app.js`, `web/css/app.css`

