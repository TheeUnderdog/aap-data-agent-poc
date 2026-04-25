# AAP Data Agent POC — Capability Overview

**Date:** July 2025  
**Summary:** Natural-language chat interface over AAP rewards/loyalty data, powered by Microsoft Fabric Data Agents.

---

## Synthetic Data

The POC runs on generated data that mirrors the Advance Auto Parts loyalty program schema as we understand it now:

- **50,000 members** across Bronze, Silver, Gold, and Platinum tiers
- **500,000+ transactions** spanning 3+ years with seasonal patterns
- **1.5M+ line items** with product-level detail
- **5,000 SKUs** across realistic auto parts categories
- **500 stores** with regional distribution
- Full points ledger, campaign history, coupon redemptions, and CSR activity logs
- Statistically realistic distributions (tier ratios, redemption curves, seasonal spikes)

---

## Fabric Workspace

Deployed entities in the `AAP-RewardsLoyalty-POC` workspace:

| Entity | Name | Notes |
|--------|------|-------|
| Lakehouse | `RewardsLoyaltyData` | All Delta tables, SQL analytics endpoint |
| Notebook | `01-create-sample-data` | Generates all synthetic data into lakehouse tables |
| Notebook | `02-data-sanity-check` | 4-block validation pipeline with LLM diagnostic report |
| Semantic Model | `AAP Rewards Loyalty Model` | 10 tables, 7 relationships, 16 DAX measures |
| Data Agent | Pit Crew (Customer Service) | See agent list below |
| Data Agent | GearUp (Loyalty Program) | See agent list below |
| Data Agent | Ignition (Marketing) | See agent list below |
| Data Agent | PartsPro (Merchandising) | See agent list below |
| Data Agent | DieHard (Store Operations) | See agent list below |

**Tables:** members, transactions, transaction_items, points_ledger, rewards, reward_redemptions, products, product_categories, stores, campaigns, campaign_responses, coupons, coupon_redemptions, csr_interactions

---

## Data Agents

#### **Crew Chief** — Executive Orchestrator
Client-side router that dispatches questions to the right specialist agent based on topic keywords.
- "How are our top-tier members responding to the holiday promo?"
- "Which product categories drive the most reward redemptions?"
- "Show me a cross-department summary of Q4 performance"

#### **Pit Crew** — Customer Service & Support
CSR agent activity, member service patterns, support operations, and ticket analysis.
- "How many support tickets were opened this month?"
- "Show me average resolution time by support channel"
- "What are the top 5 complaint categories?"

#### **GearUp** — Loyalty Program Manager
Member health, tier distribution, points liability, enrollment trends, and churn risk.
- "What's the breakdown of members by tier?"
- "How many points were redeemed last quarter?"
- "Which rewards are most popular among Gold tier members?"

#### **Ignition** — Marketing & Promotions
Campaign performance, coupon redemption funnels, promotion ROI, and segment targeting.
- "Which campaign had the highest response rate this quarter?"
- "How many customers redeemed the latest coupon offer?"
- "What's the ROI on our top 5 campaigns?"

#### **PartsPro** — Merchandising & Categories
Product performance, brand rankings, category trends, and revenue concentration.
- "What are our top 10 selling products this month?"
- "Show me revenue by product category"
- "Which brands have the highest average transaction value?"

#### **DieHard** — Store Operations
Location performance, regional comparisons, channel mix, and operational metrics across 500 stores.
- "What are our top 5 stores by revenue?"
- "Show me store performance by region"
- "Which locations have the most loyalty sign-ups per month?"

---

## Chat Interface

- **Branded web app** — AAP-themed React SPA hosted on Azure Static Web Apps
- **Six agent tabs** — Color-coded icons; click a tab to chat with that specialist
- **Natural language input** — Users type plain English questions, no SQL required
- **Agent Reasoning panel** — Expandable sidebar shows routing decisions, agent calls, and processing steps in real time
- **Welcome page** — Each agent displays a description and sample questions to get started
- **Crew Chief routing** — Cross-functional questions auto-dispatch to the right specialist

---

## Source Code & Documentation

- **Source repository** — All web app code, provisioning scripts, notebooks, agent instructions, and docs in a single Git repo
- **Documentation** — Architecture overview, implementation plan, data schema reference, and this capability overview in `docs/`

---

## Production Path

- Confirm real loyalty/rewards schema and map to semantic model
- Deploy Fabric workspace, Azure Functions, and Static Web App in AAP's Azure tenant
- Configure Fabric Mirroring from AAP's Snowflake into OneLake
- Retune agent instructions against real data and run UAT with marketing team
