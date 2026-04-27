# Copilot Instructions — AAP Data Agent POC

## Project Overview

A Microsoft Fabric Data Agent proof-of-concept for Advanced Auto Parts (AAP). Enables their marketing team to query rewards/loyalty data using natural language through a chat web app.

**Architecture:** Azure PostgreSQL → Fabric Mirroring → OneLake Lakehouse → Fabric Data Agent → Azure Functions API → React SPA

## Key Architecture Decisions

- **Schema abstraction via view layer:** The data schema is a placeholder. All components (Data Agent, API, web app) query through semantic views (`v_member_summary`, `v_transaction_history`, etc.), never raw tables. When the real schema arrives, only the view definitions change. See `docs/data-schema.md` §5 for the contract.
- **Lakehouse over Warehouse:** Fabric Mirroring writes directly to Lakehouse Delta tables; sufficient for POC scope.
- **Azure Functions backend:** Proxies requests to Fabric Data Agent API with Entra ID auth. No direct Fabric access from the frontend.
- **Azure Static Web Apps:** Hosts the React SPA with built-in auth integration.

## Data Schema — Placeholder & Abstraction

The schema in `docs/data-schema.md` is **not real AAP data**. It's a domain-informed placeholder for auto parts retail loyalty.

**Table groups:** members, member_tiers, transactions, transaction_items, points_ledger, rewards, reward_redemptions, products, product_categories, stores, campaigns, campaign_responses.

**Contract views** (the stable interface everything depends on):
- `semantic.v_member_summary` — member + tier + points balance
- `semantic.v_transaction_history` — enriched transactions
- `semantic.v_points_activity` — points earned/redeemed
- `semantic.v_reward_catalog` — available rewards
- `semantic.v_store_performance` — store aggregates
- `semantic.v_campaign_effectiveness` — campaign metrics
- `semantic.v_product_popularity` — top products by category

When modifying any component that queries data, **always use the contract views, never raw table names**.

## Project Structure

```
docs/
  architecture.md        — Full technical architecture (all 4 phases)
  implementation-plan.md — Step-by-step implementation tasks
  data-schema.md         — Placeholder schema, DDL, contract views, sample queries
.squad/                  — AI team state (Squad orchestration)
.github/
  agents/squad.agent.md  — Squad coordinator prompt
  workflows/             — Squad automation workflows
```

## Squad Team

This project uses [Squad](https://github.com/bradygaster/squad) for AI-assisted development. The team (cast from Ocean's Eleven):

| Name | Role | Domain |
|------|------|--------|
| Danny | Lead / Architect | Architecture, decisions, code review |
| Livingston | Data Engineer | Fabric workspace, mirroring, data modeling |
| Basher | Backend Dev | Data Agent config, API, auth |
| Linus | Frontend Dev | React web app, chat UI |
| Rusty | Tester / QA | Tests, validation, edge cases |

## Conventions

- **Schema changes are isolated:** If modifying data access, update the view layer in `docs/data-schema.md` first, then update consuming code. Never hardcode table names outside the view definitions.
- **Fabric Data Agent instructions** reference the contract views and sample queries from `docs/data-schema.md` §7.
- **Auth is Entra ID everywhere:** Fabric workspace, API backend, and frontend all use Azure Entra ID. Service principal for API-to-Fabric; MSAL for user-to-API.
- **POC scope:** Keep it simple. RLS and RBAC are production concerns.
