# Decision: Two-Phase Build Strategy + Semantic Model Approach

**Date:** July 2025  
**Author:** Lead Architect  
**Status:** Proposed  
**Scope:** Build sequencing and semantic model architecture

---

## Decision 1: Two-Phase Build (A/B) Strategy

**Decision:** Split all work into Phase A (build locally, no AAP access) and Phase B (deploy to AAP environment).

**Rationale:**
- AAP access timeline is uncertain — we shouldn't be blocked
- All scripts, code, and configs can be written and tested without the target environment
- Phase A produces demos (with mock data) that Dave can show AAP to build confidence
- Phase B becomes a scripted deployment measured in hours, not weeks

**Impact:** Team sprint plan follows Phase A (weeks 1–3) then Phase B (weeks 4–5). All agents can begin work immediately.

---

## Decision 2: Semantic Model + Data Agent (Both)

**Decision:** Build both a Power BI semantic model AND configure the Fabric Data Agent. Recommend the Data Agent queries through the semantic model.

**Rationale:**
- AAP is a heavy PBI user — a semantic model is immediately valuable to them
- Data Agent accuracy may need tuning; the semantic model is a safety net
- Data Agent querying through the semantic model gets better results on calculated measures
- Maximum demo value: "Here's your PBI model AND a natural language chat interface"

**Impact:** Data Engineer authors TMDL definition in Phase A. Adds ~1 day of work but significantly de-risks the POC.

---

## Decision 3: Web App Develops Against Mock Agent

**Decision:** Frontend and backend develop against a local mock of the Data Agent API during Phase A.

**Rationale:**
- Web app should be fully functional and testable before we have Fabric access
- Mock returns realistic responses so UX can be polished
- Switch from mock to real agent is a configuration change (endpoint URL + credentials)

**Impact:** Frontend Developer is unblocked from day 1. No dependency on Fabric environment for app development.
