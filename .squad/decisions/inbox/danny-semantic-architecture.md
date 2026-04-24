# Decision: Semantic Model Architecture Review

**Date:** 2025-07  
**Author:** Danny (Lead/Architect)  
**Requested by:** Dave Grobleski  
**Status:** Proposed — Awaiting Implementation

---

## Context

The "AAP Rewards Loyalty Model" was deployed with a 1:1 mapping of 10 Lakehouse Delta tables, 7 relationships, and 16 DAX measures. This was a rapid deployment without a formal architecture exercise. Five AI agent personas will query this model via Fabric Data Agent. A comprehensive review was needed.

## Decisions

### D1: Single Shared Semantic Model (Confirmed)
- **Decision:** Keep ONE semantic model shared by all 5 agent personas
- **Rationale:** Cross-domain queries require joins across tables (e.g., Loyalty Manager needs transactions for spend analysis). Splitting per-agent would create 5× maintenance burden, inconsistent measure definitions, and break cross-domain navigation.
- **Impact:** No structural change needed

### D2: Add Missing Relationship — Coupons → Transactions
- **Decision:** Add relationship from `coupons.redeemed_transaction_id` → `transactions.transaction_id`
- **Rationale:** Marketing agent cannot calculate revenue from coupon-driven purchases without this traversal. The semantic SQL views handled this with explicit JOINs, but the semantic model needs a native relationship for DAX.
- **Impact:** One new relationship. Low risk.
- **Owner:** Data Engineer

### D3: Add ~20 Missing DAX Measures
- **Decision:** Add approximately 20 DAX measures across all agent domains (see docs/semantic-model-architecture.md §1.4 for full list)
- **Rationale:** Current 16 measures cover basic counts/sums. Agents need computed metrics like Return Rate, Churn Risk Members, Points Liability ($), Coupon Redemption Rate by status, Opt-In Rates, etc.
- **Impact:** Measure additions only — no breaking changes
- **Owner:** Data Engineer

### D4: Add Column Descriptions and Synonyms (Prep for AI)
- **Decision:** Every table, column, and measure in the semantic model must have a plain-English description and relevant synonyms
- **Rationale:** Fabric Data Agent accuracy depends entirely on metadata quality. Without descriptions and synonyms, the AI guesses at column meaning from names alone — and gets it wrong. This is the single highest-impact change for agent quality.
- **Impact:** Metadata-only changes. No schema changes.
- **Owner:** Data Engineer (descriptions), Lead Architect (AI instructions)

### D5: Write AI Instructions for Semantic Model
- **Decision:** Add comprehensive natural language AI instructions covering business context, tier definitions, calculation rules, and domain vocabulary
- **Rationale:** The AI cannot infer that "revenue" should exclude returns, that tiers have specific spend thresholds, or that points are valued at $0.01. These must be explicitly stated.
- **Impact:** Prep for AI configuration in Fabric portal
- **Owner:** Lead Architect

### D6: Update Agent Configs to Reference Actual Table Names
- **Decision:** Replace all `semantic.v_*` view references in agent config.json files with actual semantic model table names
- **Rationale:** The deployed semantic model contains raw Delta tables (loyalty_members, transactions, etc.), not the SQL views. Agent configs referencing non-existent views will cause Data Agent failures.
- **Impact:** Config file changes only. All 5 agents affected.
- **Owner:** Backend Dev (completed in this session)

### D7: Add Calculated Columns and Display Folders
- **Decision:** Add calculated columns (Full Name, Days Since Last Purchase, Member Tenure, Year-Month, etc.) and organize measures into display folders by domain
- **Rationale:** Calculated columns enable common agent queries without complex DAX. Display folders make the model navigable for both AI and human users.
- **Impact:** Model enhancement — additive only
- **Owner:** Data Engineer

### D8: Business Ontology Documented
- **Decision:** The business ontology (concept hierarchy, entity relationships, domain glossary) is documented in docs/semantic-model-architecture.md Part 3
- **Rationale:** Shared vocabulary ensures all agents, developers, and stakeholders use consistent terminology
- **Impact:** Reference document — no code changes
- **Owner:** Lead Architect

## Priority Order

1. 🔴 **Critical:** D6 (fix agent configs), D4 (descriptions/synonyms), D5 (AI instructions), D2 (missing relationship), D3 (missing measures)
2. 🟡 **High:** D7 (calculated columns/folders), verified answers configuration
3. 🟢 **Medium:** Hierarchies, Date table, AI Data Schema configuration

## References

- Full analysis: `docs/semantic-model-architecture.md`
- Agent configs: `agents/*/config.json`
- Deployed model: "AAP Rewards Loyalty Model" in Fabric workspace
