# Danny — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** Microsoft Fabric, Azure PostgreSQL, Fabric Data Agent, web app
- **Key requirement:** Data schema must be componentized and abstracted for easy replacement when real schema arrives
- **Four phases:** (1) Fabric OneLake workspace, (2) PostgreSQL mirroring, (3) Fabric Data Agent, (4) Web app frontend
- **Customer context:** AAP has multiple Fabric capacities, heavy PBI user, Fabric only for PBI today. Rewards/loyalty data in Azure PostgreSQL.

## Learnings

### 2026-04-23: Architecture & Implementation Documents Created

**What I Did:**
- Created comprehensive technical architecture document (`docs/architecture.md`) covering all four phases
- Created detailed implementation plan (`docs/implementation-plan.md`) with step-by-step tasks, timelines, and risk register
- Designed schema abstraction strategy using semantic views as contract layer to enable seamless schema swap
- Documented data flow: PostgreSQL → Fabric Mirroring → Lakehouse → Data Agent → Backend API → Web App

**Key Architectural Decisions:**
1. **Lakehouse vs Warehouse:** Chose Lakehouse for native mirroring integration, Delta Lake format for schema evolution
2. **Schema Abstraction:** Three-layer architecture (source → mirrored tables → semantic views) where views define stable contract
3. **Security:** Azure Entra ID for all authentication, service principal for Fabric API access, Key Vault for secrets
4. **Deployment:** Azure Static Web Apps + managed Functions for simplified POC deployment
5. **Schema Swap Strategy:** Contract views isolate schema changes—only view SQL updates needed when production schema arrives

**Technical Highlights:**
- Fabric Mirroring with CDC for near-real-time data sync
- Data Agent with extensive system instructions and sample queries for accurate SQL generation
- React SPA with MSAL authentication for SSO
- Backend API using service principal to proxy Data Agent calls
- Complete CI/CD pipeline with GitHub Actions

**Schema Abstraction Pattern:**
```
mirrored.customers (raw PostgreSQL mirror)
  ↓ SQL VIEW
semantic.vw_CustomerProfile (contract: stable column names)
  ↓ Consumed by Data Agent, API, Reports
```
When schema changes: update view mapping, zero changes to Data Agent or app code.

**Documents Delivered:**
- `docs/architecture.md` — 45KB, comprehensive technical architecture with Mermaid diagrams
- `docs/implementation-plan.md` — 62KB, phased implementation with task lists, validation criteria, risk register

**References for Team:**
- Schema contract interface documented in architecture.md section "Data Schema Abstraction Strategy"
- Sample Data Agent instructions and configuration in architecture.md Phase 3
- Complete schema swap procedure in implementation-plan.md dedicated section

**Cross-Team Awareness:**
- Livingston (Data Engineer) has designed placeholder schema with comprehensive DDL and 20 NL→SQL examples
- Livingston's view-based abstraction layer aligns perfectly with our schema abstraction strategy
- View layer enables seamless schema swap when real AAP data arrives — implementation plan directly supports this
