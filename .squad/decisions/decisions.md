# Squad Decisions

## Scripting Directive (2026-04-23T20:17:00Z)

**By:** Dave Grobleski  
**Status:** Active  

All implementation must be 100% scripted—no manual "log in and click around" portal steps. Scripts and source code wherever possible. Fabric steps should describe what's happening but use IaC/scripting, not point-and-click instructions.

**Applied To:**
- `docs/implementation-plan.md` rewrite (2026-04-23T20:27:00Z)
- All future phase deliverables

**Reference:** Compliance verification in orchestration-log/20260423T202700Z-danny.md

---

## Real AAP Schema Received and Documented (2025-07)

**Proposed by:** Data Engineer  
**Status:** Proposed  

The real AAP Loyalty Database schema has been received (via architecture diagram) and documented in `docs/aap-schema-reference.md`. Includes 8 core table groups, 6 source systems, and mapping to 7 existing semantic contract views.

**Key Findings:**
- **CrowdTwist** external loyalty engine significantly more complex than placeholder
- **Coupons** are major first-class domain requiring dedicated semantic view
- **Audit/Fraud** and **Agent/CSR tracking** are distinct data domains not in placeholder
- No explicit stores table (embedded in transaction records)

**Recommended Actions:**
- Two new views: `v_coupon_activity`, `v_audit_trail`
- Four existing views need remapping with column-level detail
- Placeholder schema remains active until production access granted

**Blocker:** Column-level schema detail (DDL or data dictionary) required from AAP to complete view remapping.

**References:**
- `docs/aap-schema-reference.md` — Full schema reference with mapping and gap analysis
- `docs/data-schema.md` — Placeholder schema (updated with cross-reference)

---

## Implementation Plan v3 — Strategy-Focused Format (2026-04-25)

**Owner:** Lead Architect  
**Status:** Implemented  

Rewrote `docs/implementation-plan.md` as a strategy-focused technical design document (406 lines) rather than a scripted runbook. Scripts are referenced by filename with 1-line descriptions but source code is not inlined.

**Rationale:**
- v2 (1,258 lines) contained full bash/PowerShell/curl blocks making doc unwieldy
- Customer-facing docs communicate architecture and approach, not copy-paste runbooks
- Script source code belongs in `scripts/` directory, not duplicated in planning
- Phase 4 (web app) doesn't need detailed implementation yet—architecture contract sufficient

**What Changed:**
- Full script blocks → script name + 1-line description + referenced filename
- Step-by-step CLI walkthroughs → automation approach narrative
- Phase 4 detailed React/TypeScript code → 1 paragraph + architecture diagram
- Added: Monitoring section, success criteria, prerequisites summary table
- Kept: Scripts inventory, risk register, timeline, validation criteria, schema swap procedure

**Impact:**
- `docs/implementation-plan.md`: 406 lines (down from 1,258)
- No changes to other docs or code
- Old versions preserved as `implementation-plan-scripted.md` (v2) and `implementation-plan-manual.md` (v1)
