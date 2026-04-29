# Rusty — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** pytest, Playwright, httpx
- **Key requirement:** Validate that schema abstraction works — tests should pass regardless of which data schema is loaded. Sample query set from customer will be the acceptance criteria.
- **Customer context:** POC must be demo-ready for Advanced Auto Parts marketing team.

## Learnings

### Pre-Deployment Review (2026-04-27)
- **Context**: Cross-cutting integration review of all deployment artifacts before deploying to Fabric workspace 82f53636-206f-4825-821b-bdaa8e089893
- **Findings**: 
  - ✅ Notebook → SQL Views schema consistency: All table and column references match correctly
  - ✅ SQL Views → Sample Queries consistency: All view and column references are correct
  - ✅ Scripts → .env.fabric consistency: File format and key names match
  - ✅ Deployment order: README instructions match script dependencies
  - ✅ .gitignore: .env.fabric properly excluded
  - 🟡 **Minor issue found**: SQL verification query (line 343) has copy/paste error in comment - says "v_transaction_history" but should reference "v_points_activity" (cosmetic only, in commented-out code)
- **Schema validation**:
  - Notebook creates 10 tables in `mirrored` schema with correct column types
  - Views reference all correct table/column names from mirrored schema
  - Sample queries reference all correct view/column names from semantic schema
  - View count: 9 views (v_member_summary, v_transaction_history, v_points_activity, v_coupon_activity, v_store_performance, v_product_popularity, v_member_engagement, v_campaign_effectiveness, v_audit_trail)
- **Integration points validated**:
  - setup-workspace.ps1 outputs: FABRIC_WORKSPACE_ID, FABRIC_WORKSPACE_NAME, FABRIC_LAKEHOUSE_ID, FABRIC_LAKEHOUSE_NAME, FABRIC_SQL_ENDPOINT, FABRIC_CAPACITY_ID
  - deploy-semantic-views.ps1 reads: FABRIC_SQL_ENDPOINT, FABRIC_LAKEHOUSE_NAME (both present in output)
  - Deployment sequence correct: setup-workspace → import/run notebook → deploy-semantic-views
- **Recommendation**: Deployment-ready with one cosmetic fix optional (commented code typo)

### Schema Reference Fix — mirrored → dbo (2026-07-24)
- **Context**: Livingston removing `mirrored.` schema prefix from PySpark notebook (Fabric Spark doesn't support CREATE SCHEMA). Semantic views needed matching update.
- **Action**: Replaced all 27 `mirrored.tablename` references with `dbo.tablename` in `scripts/create-semantic-views.sql`
- **Verified clean**:
  - `config/sample-queries.json` — no `mirrored.` refs (queries use `semantic.v_*` views only) ✅
  - `scripts/deploy-views.py` — no `mirrored.` refs ✅
  - `scripts/deploy-semantic-views.ps1` — no `mirrored.` refs ✅
- **Schema syntax**: `CREATE SCHEMA semantic` with `IF NOT EXISTS` check via `sys.schemas` is valid T-SQL for Fabric SQL endpoint ✅
- **Learnings**:
  - Fabric SQL endpoint exposes default Lakehouse tables under `dbo` schema
  - Fabric Spark writes to default Lakehouse (no schema prefix supported)
  - SQL endpoint supports `CREATE SCHEMA` (T-SQL), but Spark does not
  - The `semantic` schema creation is unaffected — only source table references needed updating

### Per-Agent Gherkin Test Directories (2026-04-29)

**Scope:** Created per-agent BDD test suites as web app migrates to folder-per-agent structure.

**Files Created:**
- `web/agents/crew-chief/tests/agent.feature` — Routing and orchestration scenarios
- `web/agents/pit-crew/tests/agent.feature` — Pit Crew domain tests
- `web/agents/gearup/tests/agent.feature` — GearUp (Inventory) tests
- `web/agents/ignition/tests/agent.feature` — Ignition (Marketing) tests
- `web/agents/partspro/tests/agent.feature` — PartsPro (Product) tests
- `web/agents/diehard/tests/agent.feature` — DieHard (Performance) tests

**Coverage Pattern:**
1. **Feature tags:** `@agent @{slug}` on all files
2. **Scenario tags:** `@id:{slug}-{scenario-id}` on all scenarios
3. **Background:** Shared setup — open `http://localhost:5000`, wait for load, switch to agent tab
4. **Scenarios:** Welcome page identity, sample questions visibility, clickability, domain-relevant chat, response type validation
5. **Special handling:** Crew Chief includes routing/fan-out verification instead of single Fabric call

**Key Details:**
- Each feature file owns its agent's test suite
- Agent-specific assertions (e.g., GearUp color checks: gold accent `#FFCC00`, text `#B38600`)
- Shared BDD step definitions remain in root `tests/` for reuse
- Follows AAP domain terminology (rewards, loyalty, auto parts retail)

**Test Data:**
- Sample questions defined per agent in Gherkin (reflects agent routing keywords)
- Chat responses validated against agent's expected domain (inventory, marketing, performance, etc.)

**Integration:**
- Tests run with `pytest -k agent` to target per-agent suites
- Each agent's folder now owns its test directory, enabling per-agent CI/CD runs if needed
- Scalable — new agents add new feature files without modifying shared test infrastructure
- Frontend config changes (Linus) enable test scenarios; backend endpoint (Basher) may be validated by API-level tests

**Impact:**
- ✅ Per-agent test coverage mirrors folder structure
- ✅ Agent-specific assertions catch routing/branding regressions
- ✅ Decoupled test suites enable parallel CI/CD runs
- ✅ Maintainable — tests live with agents they test

**Status:** Complete, ready for test execution
