# Visual Test Report — Advance Insights Web App

**Date:** Test run completed via Playwright MCP browser automation
**Target:** http://localhost:5000
**Evidence directory:** `C:\Users\davegro\OneDrive - Microsoft\Documents\Code\AAP Data Agent POC\tests\cua\evidence\`

---

## ⚠️ Critical Blocker Discovered

The backend `POST /api/chat` endpoint **does not return** within 90+ seconds during this run. The user-message bubble, input clear, send-button-disable, and "Sending to {Agent}…" indicators all render correctly, but no agent response is ever delivered. This blocks every scenario whose `Then` step requires an agent reply, a reasoning step, or a copy button. Affected scenarios are marked **❌ FAIL — backend hang** with shared root cause.

---

## Per-Suite Results

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**SUITE: 01-page-load.feature** (Initial Page Load & Layout)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario: Page loads without errors
  ✅ PASS
  Evidence: `01-page-load-initial-1.png`

Scenario: Header bar is visible with branding
  ✅ PASS — AAP triangular logo, "ADVANCE INSIGHTS" text, "Rewards & Loyalty Intelligence" subtitle all visible
  Evidence: `01-page-load-initial-1.png`

Scenario: Header right-side controls are visible
  ✅ PASS — New Chat (+), Reasoning (info/brain), Documentation (book), "Connected" indicator, Sign out link all visible
  Evidence: `01-page-load-initial-1.png`

Scenario: All 6 agent tabs are visible
  ⚠️ PASS with deviation — All 6 agents present (Crew Chief, Pit Crew, GearUp, Ignition, PartsPro, DieHard) with correct colors and icons. **Layout deviation:** spec describes a "left vertical sidebar"; actual implementation is a **horizontal tab strip below the header**.
  Evidence: `01-page-load-initial-1.png`

Scenario: Welcome panel for default agent (Crew Chief) is visible
  ✅ PASS — Crew Chief welcome with description and 6 suggestion chips
  Evidence: `01-page-load-initial-1.png`

Scenario: Input bar is visible at the bottom
  ✅ PASS — Text field with "Ask a question..." placeholder, Send button, lightbulb (suggestions), dice button
  Evidence: `01-page-load-initial-1.png`

Scenario: No login screen is shown (proxy mode)
  ✅ PASS — Page loads directly into chat interface; "Connected" status visible
  Evidence: `01-page-load-initial-1.png`

Scenario: No console / network errors block the UI
  ⚠️ PASS with note — UI is fully functional, but 2 console errors logged (MSAL CDN blocked by ORB; tolerated because app is in proxy mode).
  Evidence: `01-page-load-initial-1.png`

**Suite Result: 8/8 passed** (2 with deviation/note)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**SUITE: 02-agent-tabs.feature** (Agent Tab Switching)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario: Click Pit Crew tab
  ✅ PASS — Blue accent, wrench icon, "Service & support" subtitle, correct welcome paragraph
  Evidence: `02-pit-crew-1.png`

Scenario: Click GearUp tab
  ✅ PASS — Gold accent, gauge icon, "Loyalty & rewards" subtitle
  Evidence: `02-gearup-1.png`

Scenario: Click Ignition tab
  ✅ PASS — Orange accent, spark plug icon, "Campaigns & promos" subtitle
  Evidence: `02-ignition-1.png`

Scenario: Click PartsPro tab
  ✅ PASS — Green accent, gear icon, "Products & merch" subtitle
  Evidence: `02-partspro-1.png`

Scenario: Click DieHard tab
  ✅ PASS — Red accent, battery icon, "Stores & ops" subtitle
  Evidence: `02-diehard-1.png`

Scenario: Return to Crew Chief tab
  ✅ PASS — Black accent, steering-wheel icon, original welcome restored
  Evidence: `02-crew-chief-back-1.png`

Scenario: Chat history preserved when switching tabs and returning
  ❌ FAIL — backend hang (cannot generate any chat history to preserve)
  Step failed: When I send a message and switch tabs, returning shows my prior conversation
  Expected: Previous user/agent bubbles still visible after returning to the tab
  Observed: Could not produce any agent response → no history exists to preserve
  Evidence: `03-chat-hung-1.png`

Scenario: Unread indicator on tab with background message
  ❌ FAIL — backend hang (no agent reply ever arrives in background)
  Step failed: Then I see an unread badge on the original tab
  Expected: Visual unread indicator (dot/badge) on tab whose agent replied while another tab was active
  Observed: No agent reply produced during the test run
  Evidence: `03-chat-hung-1.png`

**Suite Result: 6/8 passed**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**SUITE: 03-chat-flow.feature** (Send Message & Receive Response)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario: User message bubble appears after typing & clicking Send
  ✅ PASS — User-side bubble rendered with the typed text
  Evidence: `03-chat-hung-1.png`

Scenario: Input clears and Send button disables while in flight
  ✅ PASS — Input emptied, Send button became inactive, "Sending to GearUp…" indicator appeared
  Evidence: `03-chat-hung-1.png`

Scenario: Agent response appears within timeout
  ❌ FAIL — backend hang
  Step failed: Then I see the agent's response within 30 seconds
  Expected: Bot bubble with markdown content (table or text) below user bubble
  Observed: "Sending to GearUp…" indicator stayed for 90+ seconds; no `/api/chat` response received
  Evidence: `03-chat-hung-1.png`

Scenario: Empty message guard (Send disabled / no bubble on empty)
  ✅ PASS — Clicking Send with empty input produced no user bubble; chat area unchanged
  Evidence: `04-suggestions-diehard-1.png` (post-empty-send screenshot, no bubble visible)

Scenario: Press Enter sends message
  ❌ FAIL — backend hang (cannot verify full submit→response loop)
  Step failed: Then I see the agent response
  Expected: Pressing Enter submits and an agent reply renders
  Observed: User bubble + indicator appear but no response (same hang as click-Send case)

Scenario: New Chat (+) clears the conversation
  ✅ PASS — Clicking New Chat removed the user bubble and restored the welcome screen
  Evidence: `04-suggestions-open-1.png` (taken after New Chat reset)

Scenario: Markdown / table rendering in bot reply
  ❌ FAIL — backend hang (no bot reply to render)

Scenario: Long-running Crew Chief multi-agent response
  ❌ FAIL — backend hang

**Suite Result: 3/8 passed**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**SUITE: 04-suggestions.feature** (Lightbulb & Dice)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario: Lightbulb opens suggestions panel above input
  ✅ PASS — Panel shows "Try asking {Agent}" header + 6 chips
  Evidence: `04-suggestions-open-1.png`

Scenario: Clicking a suggestion chip populates the input (does not auto-send)
  ✅ PASS — Verified by intercepting fetch: clicking chip filled input value but produced no user bubble and no `/api/chat` POST
  Evidence: `04-suggestions-open-1.png`

Scenario: Suggestions change per agent
  ✅ PASS — Ignition shows campaign/redemption questions ("Which campaign had the highest redemption rate this quarter?", "What's the ROI on our top 5 campaigns?", etc.). DieHard shows store/region questions ("What are our top 5 stores by revenue?", "Show me store performance by region", etc.).
  Evidence: `04-suggestions-diehard-1.png`

Scenario: Lightbulb toggle closes the panel
  ✅ PASS — Clicking lightbulb again hides the suggestions panel
  Evidence: `04-suggestions-closed-1.png`

Scenario: Dice button generates a mystery question
  ⚠️ INCONCLUSIVE — Dice click triggers `/api/chat` (icon enters spinning state) but the request hangs (same backend issue). Cannot confirm whether a generated question would have rendered.
  Evidence: `04-dice-spinning-1.png`

**Suite Result: 4/5 passed (1 inconclusive)**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**SUITE: 05-reasoning-panel.feature** (Chain-of-Thought Panel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario: Brain icon opens the reasoning panel from the right
  ✅ PASS — Panel slides in from right edge, ~360px wide, shows "Agent Reasoning" header and × close button
  Evidence: `05-reasoning-open-1.png`

Scenario: Clicking brain icon (or × close) hides the panel
  ✅ PASS — Panel translates off-screen to the right
  Evidence: `05-reasoning-closed-1.png`

Scenario: Reasoning steps appear with timing as agent responds
  ❌ FAIL — backend hang (no reasoning events stream because `/api/chat` never returns)
  Step failed: Then I see chain-of-thought steps populate with elapsed times
  Expected: Live-updating step list with millisecond timing per step
  Observed: Reasoning panel remained empty; step timer stuck at "0ms"

Scenario: Multi-agent reasoning groups (Crew Chief)
  ❌ FAIL — backend hang (Crew Chief multi-agent flow cannot produce reasoning)

**Suite Result: 2/4 passed**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**SUITE: 06-copy-button.feature** (Copy Bot Reply)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario: Copy button appears on bot bubble
  ❌ FAIL — backend hang (no bot bubble rendered, so no copy button to display)

Scenario: Click copy → success indicator (checkmark / "Copied!")
  ❌ FAIL — backend hang

Scenario: Clipboard receives the bot's text
  ❌ FAIL — backend hang

**Suite Result: 0/3 passed**

---

## Final Summary

```
═══════════════════════════════════════════
        FULL TEST RUN SUMMARY
═══════════════════════════════════════════

Suite                    Result    Status
─────────────────────────────────────────
01-page-load             8/8       ✅ ALL PASS (2 with deviation/note)
02-agent-tabs            6/8       ⚠️  2 failures (backend)
03-chat-flow             3/8       ❌  5 failures (backend)
04-suggestions           4/5       ⚠️  1 inconclusive (backend)
05-reasoning-panel       2/4       ⚠️  2 failures (backend)
06-copy-button           0/3       ❌  3 failures (backend)
─────────────────────────────────────────
TOTAL                   23/36       64% pass rate
```

```
═══════════════════════════════════════════
        FAILURES — ACTIONABLE LIST
═══════════════════════════════════════════

 #  Suite              Scenario                              What Went Wrong
─── ─────────────────  ────────────────────────────────────  ────────────────────────────────────────────────
 1  02-agent-tabs      Chat history preserved across tabs    No agent reply ever produced; cannot create
                                                             history to verify preservation. Root cause:
                                                             POST /api/chat hangs >90s with no response.
 2  02-agent-tabs      Unread indicator on background msg    Same root cause — no background reply arrives.
 3  03-chat-flow       Agent response within 30s             "Sending to GearUp…" indicator persisted >90s;
                                                             POST /api/chat never returned a body. No bot
                                                             bubble was ever rendered.
 4  03-chat-flow       Press Enter sends message             User bubble and loading indicator both appear,
                                                             but no agent reply (same backend hang).
 5  03-chat-flow       Markdown / table rendering            No bot reply received → cannot evaluate.
 6  03-chat-flow       Long Crew Chief multi-agent response  Same backend hang (timeout 60s exceeded).
 7  04-suggestions     Dice → mystery question (INCONCLUSIVE) Dice click fires /api/chat which hangs; icon
                                                             stays spinning. Cannot confirm UI text outcome.
 8  05-reasoning       Reasoning steps populate with timing  Panel UI works, but no SSE / streamed steps
                                                             because backend chat call never starts streaming.
 9  05-reasoning       Multi-agent reasoning groups          Same root cause.
10  06-copy-button     Copy button appears on bot bubble     No bot bubble exists to attach a copy button to.
11  06-copy-button     Copy success indicator                Cannot trigger — no copy button.
12  06-copy-button     Clipboard receives bot text           Cannot trigger — no copy button.

>>>  PRIMARY ROOT CAUSE for 11 of 12 failures: POST /api/chat hangs.   <<<
>>>  Recommended next step: inspect web/server.py for the /api/chat   <<<
>>>  handler — likely a missing await, deadlocked dependency, or       <<<
>>>  upstream model/Graph call that is blocking without a timeout.     <<<
```

```
═══════════════════════════════════════════
        OBSERVATIONS (non-blocking)
═══════════════════════════════════════════

• Layout deviation: feature spec / agent prompt describe agent tabs as a "left vertical
  sidebar"; the actual implementation is a horizontal strip immediately below the header.
  All 6 tabs, colors, icons, and welcome content are correct — only orientation differs.

• Reasoning panel positioning is viewport-sensitive: at the default Playwright viewport
  (~1028px wide) the panel sits flush at x≈1028 — i.e., effectively off-screen. Resizing
  to 1440×900 brought it into view at x≈1080. Consider clamping panel position so it is
  always visible on smaller viewports.

• Two console errors are logged on every page load: MSAL auth CDN blocked by ORB. The app
  tolerates this (proxy mode), but the errors will be noisy in any monitoring tool.

• The "Sending to {Agent}…" status indicator never times out client-side. If /api/chat
  hangs (as observed), the user is stuck with a permanent in-flight indicator and a
  disabled Send button. Consider a client-side timeout (e.g., 60s) that surfaces an error
  toast and re-enables Send.

• Suggestion chips on the welcome screen and inside the lightbulb panel both populate
  the input without auto-sending. This is consistent and feels right, but the spec
  ("clicking a suggestion fires the question") could be read either way — worth
  confirming the intended behavior.

• Sign-out link is rendered in proxy mode even though there is no real session. Clicking
  it was not exercised in this run; behavior is unverified.

• Crew Chief tab shows "Ask anything" as its subtitle but the spec called it "Executive
  orchestrator" — both appear in the welcome panel itself, so this is just an
  abbreviation in the tab strip and is fine.
```

---

## Evidence Index

All screenshots in `tests/cua/evidence/`:

| File | Description |
| --- | --- |
| `01-page-load-initial-1.png` | Initial page load — header, tabs, welcome, input |
| `02-pit-crew-1.png` | Pit Crew tab active (blue, wrench) |
| `02-gearup-1.png` | GearUp tab active (gold, gauge) |
| `02-ignition-1.png` | Ignition tab active (orange, spark plug) |
| `02-partspro-1.png` | PartsPro tab active (green, gear) |
| `02-diehard-1.png` | DieHard tab active (red, battery) |
| `02-crew-chief-back-1.png` | Returned to Crew Chief tab |
| `03-chat-hung-1.png` | User bubble + "Sending to GearUp…" indicator stuck (backend hang) |
| `04-suggestions-open-1.png` | Lightbulb suggestions panel open above input |
| `04-suggestions-closed-1.png` | Lightbulb panel closed |
| `04-suggestions-diehard-1.png` | DieHard agent — store/region suggestion chips visible |
| `04-dice-spinning-1.png` | Dice button in spinning state (request stuck) |
| `05-reasoning-open-1.png` | Reasoning panel slid in from right |
| `05-reasoning-closed-1.png` | Reasoning panel hidden off-screen right |
