# Decision: Public Repository Preparation

**Date:** 2026-07
**Author:** Danny (Lead/Architect)
**Status:** Implemented

## Decision

Prepare the AAP Data Agent POC repository for public visibility by updating all documentation to reflect current reality (local Flask development) and adding an MIT license.

## Changes Made

1. **README.md** — Complete rewrite: architecture diagram corrected (Flask, not Container Apps), 6 agent tabs (not 5), auth section updated to ChainedTokenCredential, Deploy to Azure moved under "Future" heading, license changed to MIT, added CUA tests and docs.html references
2. **web/SETUP.md** — Added status callout: §1–2 active, §3–6 future/not implemented
3. **LICENSE** — MIT License, Copyright 2026 Dave Grobleski

## Rationale

- Public repos must accurately represent what works today — misleading setup instructions erode trust
- Container Apps deployment docs are preserved (useful reference) but clearly marked as aspirational
- MIT license chosen for maximum adoption potential per Dave's direction

## Team Impact

- **All agents:** README is now the canonical "getting started" path — `pip install` + `az login` + `python web/server.py`
- **Basher:** Container Apps work in SETUP.md is preserved, just marked as future
- **Linus:** Frontend docs updated to mention 6 tabs and docs.html
- **Rusty:** CUA test suite now referenced in README (42 scenarios, 6 feature files)
