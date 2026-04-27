# CUA Test Suite — Advance Insights

## What This Is

Structured test scripts for a Computer Use Agent (CUA) to validate the Advance Insights web application. The CUA reads these `.feature` files as step-by-step instructions, opens a browser, and executes them visually.

## Strategy: Gherkin for LLMs

We use Gherkin's `Given/When/Then` structure because it provides clear, deterministic steps — but we write the step text in **natural language optimized for LLM comprehension**, not traditional regex-matched step definitions. This means:

- Steps describe *intent and visual outcomes* rather than DOM selectors or programmatic assertions
- Verification steps say things like "I should see the agent name displayed" rather than `element('#agent-name').should('exist')`
- Context is embedded directly in the step text (e.g., "Given I am on the Crew Chief tab" rather than requiring a step definition lookup)
- Comments (`#`) provide additional context a CUA might need (e.g., expected colors, layout hints, what "success" looks like visually)

The result: `.feature` files that any LLM-based agent can execute without step-definition bindings, while still benefiting from Gherkin's structured scenario organization, tagging (`@smoke`, `@core`), and `Background` reuse.

## Test Format — Gherkin / Cucumber

Tests are written in **Gherkin** syntax (`.feature` files) — the same structured language used by Cucumber, Behave, SpecFlow, and other BDD frameworks. Key concepts:

- **`.feature` files** — Human-readable test specifications using `Feature`, `Scenario`, `Given/When/Then` keywords. Located in `features/`.
- **Gherkin** — The language/grammar that `.feature` files are written in. Designed so non-technical stakeholders can read and validate test intent.
- **Cucumber** — The original BDD test runner that executes Gherkin. Our CUA acts as the "runner" here — reading the steps and executing them visually in a browser instead of through code bindings.
- **Pickle** — In Cucumber's internal architecture, a "pickle" is the compiled/parsed representation of a Gherkin scenario after variable substitution and example expansion. We don't generate pickle files directly — the CUA interprets `.feature` files as-is — but the concept applies: each scenario is an independent, fully-resolved test case.

Our approach uses Gherkin as the specification format but replaces traditional step-definition code with CUA visual execution. This means the same `.feature` files could later be wired to a Playwright/Selenium runner with step definitions if automated regression is needed.

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
