# CUA Test Suite — Advance Insights

## What This Is

Structured test scripts for a Computer Use Agent (CUA) to validate the Advance Insights web application. The CUA reads these `.feature` files as step-by-step instructions, opens a browser, and executes them visually.

## How the CUA Should Use These Files

1. Read the `.feature` file for the test suite you want to run
2. Open a browser to the app URL (default: http://localhost:5000)
3. For each `Scenario`, follow the `Given/When/Then` steps literally:
   - **Given** = precondition (navigate somewhere, ensure a state)
   - **When** = action (click, type, scroll)
   - **Then** = verification (visually confirm something is true)
   - **And** = continuation of the previous step type
4. Report each scenario as PASS or FAIL with a brief reason if FAIL

## Prerequisites

- The app server must be running: `cd web && python server.py`
- The server must be authenticated: run `az login` first
- Default URL: http://localhost:5000
- The app runs in "proxy mode" — no login screen, goes straight to the main UI

## Test Suites (run in order for first-time validation)

| File | What It Tests | Priority |
|------|---------------|----------|
| `01-page-load.feature` | App loads, all UI elements render | Smoke |
| `02-agent-tabs.feature` | Tab switching, agent selection | Core |
| `03-chat-flow.feature` | Send message, receive response | Core |
| `04-suggestions.feature` | Suggestion panel, sample questions | Secondary |
| `05-reasoning-panel.feature` | Reasoning slide-out, methodology | Secondary |
| `06-copy-button.feature` | Copy agent response to clipboard | Secondary |

## Visual Reference

The app has these main areas:
- **Header bar** (top): AAP logo, "ADVANCE INSIGHTS" wordmark, new chat button, reasoning toggle, user name, sign out
- **Tab strip** (left sidebar): 6 agent tabs with colored icons and names
- **Chat area** (center): Messages between user and agent
- **Input bar** (bottom): Textarea + send button + suggestions lightbulb button
- **Reasoning panel** (right, hidden by default): Slides out when toggled

## Agent Reference

| Tab Name | Color | Domain |
|----------|-------|--------|
| Crew Chief | Black (#1E1E1E) | Executive orchestrator (routes to others) |
| Pit Crew | Blue (#2B6CB0) | Customer Service & Support |
| GearUp | Gold (#B38600) | Loyalty Program Manager |
| Ignition | Orange (#E86C00) | Marketing & Promotions |
| PartsPro | Green (#2D8A4E) | Merchandising & Categories |
| DieHard | Red (#B6121B) | Store Operations |

## Reporting Format

After running a suite, report results as:

```
Suite: 01-page-load
  PASS: App title is correct
  PASS: Header bar is visible with branding
  PASS: All 6 agent tabs are rendered
  FAIL: Suggestions button not found — button title may have changed
  ---
  Result: 3/4 passed
```
