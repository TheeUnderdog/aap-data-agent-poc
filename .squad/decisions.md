# Squad Decisions

## Active Decisions

### Schema Abstraction (2026-04-23)
- **Decision:** Implement view-based contract layer for schema independence
- **Rationale:** Enables seamless replacement of placeholder schema with production schema without code changes
- **Implementation:** All components query semantic views, not raw tables
- **Owner:** Danny (Architecture), Livingston (Schema Design)
- **Status:** Approved & Documented in architecture.md and data-schema.md

### Architectural Decisions for AAP Data Agent POC (2026-04-23)
- **Decisions:**
  1. Use Lakehouse (not Warehouse) for mirrored data — Native mirroring integration, Delta Lake schema evolution, cost efficient
  2. Semantic views as contract layer — Isolates schema changes, zero code impact, single point of update
  3. Service principal for Fabric API access — Simplified security model, consistent behavior, easier audit
  4. Static Web Apps + managed Functions — Single deployment, auto-CORS, cost efficient, sufficient for POC
  5. Data Agent config in source control — Version control, repeatability, disaster recovery
  6. Return generated SQL to user — Transparency, debugging, trust, compliance
  7. Generate placeholder data — Testing, demo value, performance validation
  8. Entra ID SSO authentication — Existing identity infrastructure, security, compliance
- **Owner:** Danny (Lead/Architect)
- **Status:** Approved for Implementation
- **Reference:** `.squad/decisions/inbox/danny-architecture-decisions.md`

### Executive Overview Document (2026-04-24)
- **Decision:** Create `docs/overview.md` as primary executive summary for AAP Data Agent POC
- **Rationale:** Dual audience (AAP business/technical stakeholders, Microsoft field team) needs accessible 2–3 page summary explaining opportunity, four-phase approach, schema abstraction strategy, prerequisites, risks, and success criteria
- **Content:** 1,200-word document synthesizing technical architecture into business-friendly narrative with ASCII flow diagram, prerequisite checklist, risk register, and cross-references
- **Owner:** Danny (Lead/Architect)
- **Status:** Delivered & Ready for Stakeholder Review
- **Reference:** `.squad/decisions/inbox/danny-overview-doc.md`

### Placeholder Schema with View-Based Abstraction (2026-04-23)
- **Decision:** Implement view-based abstraction layer as schema contract with 9-table placeholder design
- **Rationale:** Enables zero-code schema swap when production data arrives; all consuming components (Fabric Data Agent, Backend API, Web App, Power BI) depend on stable view interfaces
- **Implementation:** 7 contract views provide stable query surfaces; documented 7-step swap procedure
- **Owner:** Livingston (Data Engineer)
- **Status:** Implemented
- **Reference:** `.squad/decisions/inbox/livingston-schema-design.md`

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
