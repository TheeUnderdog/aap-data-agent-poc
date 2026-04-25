# AAP Data Agent POC — Capability Overview

**Prepared for:** Advance Auto Parts  
**Date:** April 2026  
**Document Status:** Executive Summary — Business Audience

---

## 1. Introduction: Natural Language Data Access for Marketing

Advanced Auto Parts' marketing team is sitting on a goldmine of loyalty and rewards data—50,000 engaged members, 500,000+ transactions, years of campaign history—but today, accessing insights requires a ticket to the data team. A single question ("Which campaigns had the best redemption rates?") can take days.

We've built the **AAP Data Agent POC**—a chat-based application that lets marketing users ask questions in plain English and get answers instantly, powered by the same AI and data technologies that power enterprise analytics at Microsoft.

This document walks you through what's possible with this solution, what the experience feels like, and how we move from proof-of-concept to production.

---

## 2. The Business Problem: Data Bottleneck

Marketing teams thrive on speed. Every day without campaign performance data is a missed opportunity to optimize targeting, adjust messaging, or capitalize on seasonal trends.

**Today's workflow:**
- Marketing specialist has a question: "Are our gold-tier members responding better to email or SMS?"
- Sends request to analytics team or database engineers
- Waits 2–5 days for SQL query and results
- Decision window has often closed

**The cost:**
- Delayed campaign iterations (faster-moving competitors ship 3 iterations while you ship 1)
- Under-utilized talent (expensive marketers wait for analysts)
- Missed real-time opportunities (weekend sales spike goes unanalyzed)
- Institutional knowledge trapped with a few power-users who know SQL

The AAP Data Agent POC eliminates this friction. Marketing users get answers in seconds, explore follow-up questions without waiting, and move at the speed of the business.

---

## 3. What We Built: Six Specialized Agents + Branded Web App

The solution is a **web chat application** where users select a specialist agent and ask questions in conversational English. Behind the scenes, our AI agents translate plain language into queries against your loyalty and rewards data, and return insights with complete transparency (users see the exact data and the query used to generate it).

### Six Specialized Agents

Each agent is branded with an auto-parts-inspired name and specializes in one domain:

#### **Crew Chief** — Executive Orchestrator
When you're not sure which specialist to ask, Crew Chief coordinates across all agents to answer cross-functional questions.

*Sample questions:*
- "How are our top-tier members responding to the holiday promo?"
- "Which product categories drive the most reward redemptions?"
- "Show me a cross-department summary of Q4 performance"

#### **Pit Crew** — Customer Service & Support
Handles member lookups, service records, and CSR team insights.

*Sample questions:*
- "How many support tickets were opened this month?"
- "Which stores have the most escalated service issues?"
- "Show me average resolution time by support channel"

#### **GearUp** — Loyalty Program Manager
Deep dives into membership tiers, points activity, and engagement metrics.

*Sample questions:*
- "What's the breakdown of members by tier?"
- "How many active loyalty members do we have?"
- "Which rewards are most popular among Gold-tier members?"

#### **Ignition** — Marketing & Promotions
Analyzes campaign performance, coupon effectiveness, and promotion ROI.

*Sample questions:*
- "Which campaign had the highest response rate this quarter?"
- "Which customer segments respond best to email vs. SMS?"
- "How many customers redeemed the latest coupon offer?"

#### **PartsPro** — Merchandising & Categories
Product and category analysis—top sellers, brand rankings, revenue concentration.

*Sample questions:*
- "What are our top 10 selling products this month?"
- "Show me revenue by product category"
- "Which brands have the highest average transaction value?"

#### **DieHard** — Store Operations
Regional comparisons, location performance, and operational metrics.

*Sample questions:*
- "What are our top 5 stores by revenue?"
- "Show me store performance by region"
- "Which locations have the most loyalty sign-ups per month?"

---

## 4. The Data: Realistic, Ready to Demo

The POC uses **realistic synthetic data** that mirrors the structure and volume of a real AAP loyalty program:

- **50,000 loyalty members** with tier information (Bronze → Platinum)
- **500,000+ transactions** spanning 3+ years of purchase history
- **1.5M+ line items** (transaction details with product-level data)
- **5,000 SKUs** across major product categories
- **500 stores** across the store network
- **Points activity:** Detailed points earned, redeemed, and expired
- **Campaign data:** Coupon rules, issuance, and redemption history
- **CSR interactions:** Service tickets and member activities

This synthetic dataset is statistically realistic—tier distribution, seasonal purchase patterns, coupon redemption rates all match real loyalty program behavior. Marketing users can explore the exact kinds of questions they'll ask in production, with confidence that performance and data quality will translate.

**When moving to production:** The system swaps out the synthetic tables for your actual Snowflake or PostgreSQL schema—no code changes required. The chat interface, agents, and API layer remain unchanged.

---

## 5. Demo Walkthrough: The Experience

Here's what a live demo looks like:

**Step 1: User opens the app**
- A branded AAP welcome page loads
- User sees six agent tabs across the top (Crew Chief, Pit Crew, GearUp, Ignition, PartsPro, DieHard)
- Each agent has a color-coded icon and a one-line description of what it does

**Step 2: Select an agent**
- Marketing manager clicks the **GearUp** (Loyalty Program Manager) tab
- A chat window appears with sample questions to get started
- User types: *"What's the tier breakdown of our members?"*

**Step 3: Get an instant answer**
- System thinks for ~2–3 seconds
- Agent returns: "Based on 50,000 members: Bronze 60%, Silver 25%, Gold 10%, Platinum 5%"
- Below the text, a collapsible data table shows exact counts per tier
- A second collapsible shows the exact SQL query used to fetch this data

**Step 4: Ask a follow-up**
- User: *"How many Platinum members did we gain this month?"*
- Instant answer with the trend

**Step 5: Switch to a different lens**
- User clicks the **Ignition** (Marketing & Promotions) tab
- Types: *"Which campaigns had the best redemption rates?"*
- Gets campaign-by-campaign breakdown with % redemption and confidence metrics
- Can drill into a specific campaign to see tier-level performance

**Step 6: Cross-agent insight**
- User switches to the **PartsPro** (Merchandising) tab
- Types: *"Which product categories drive the most revenue?"*
- Gets a category-by-category breakdown with revenue, transaction counts, and trend direction

**Throughout:** Users get clarity. Every answer includes the data, the query, and confidence indicators. No black box.

---

## 6. Technology Foundation: Simple, Secure, Scalable

Behind the user-friendly chat interface is a clean, enterprise-grade stack:

**Microsoft Fabric — The Data Platform**
- Centralized lakehouse stores all loyalty/rewards tables
- Fabric's Mirroring connects to your PostgreSQL or Snowflake database—real-time data sync into the cloud
- Semantic model layer provides consistent business metrics (tier calculations, points balance, LTV)

**Fabric Data Agents — The Intelligence Layer**
- Purpose-built AI agents trained on loyalty/rewards domain knowledge
- Each agent knows how to navigate your data model and respond with accuracy and transparency
- Returns exact SQL + results so marketing users build trust and understanding

**Azure Functions — API Backend**
- Lightweight proxy that sits between the web app and Fabric
- Handles authentication, request routing, and response marshaling
- Runs only when a question is asked—no always-on infrastructure

**React Web App — Branded Chat Interface**
- Single-page application hosted on Azure Static Web Apps
- Works on desktop and mobile
- AAP branding and UI consistent with your other tools

**Azure Entra ID — Security**
- End-to-end authentication: web app → API → Fabric Data Agents
- No shared passwords; uses Azure enterprise identity
- Audit trail for compliance

The architecture is deliberately simple: no custom ETL pipelines, no complex integrations, no proprietary middleware. Everything is off-the-shelf enterprise technology.

---

## 7. Deployment to Production: From POC to Live

The POC proves the concept works. Production deployment is straightforward because architecture decisions were made *for* seamless transition. Here's the path:

### **Step 1: Schema Confirmation** (1–2 weeks)
- AAP provides the actual schema for loyalty/rewards tables (PostgreSQL, Snowflake, or Fabric native)
- Team maps real schema to the semantic view layer (contracts defined in POC)
- Timeline: AAP IT + Dev team, 3–5 days of collaboration

### **Step 2: Azure Environment Setup** (1 week)
- Provision or reuse AAP's Azure subscription
- Create Fabric workspace in AAP's tenant
- Deploy Azure Functions, Static Web Apps, and supporting services
- Timeline: 3–5 days, mostly automated scripts

### **Step 3: Data Mirroring Configuration** (1–2 weeks)
- Configure Fabric Mirroring from AAP's production database into OneLake Lakehouse
- Validate data freshness (typically hourly or daily refresh depending on your needs)
- Timeline: 5–7 days (includes network setup, credential provisioning, refresh validation)

### **Step 4: Semantic Model Update** (1 week)
- Remap the semantic model from POC synthetic tables to real production tables
- Recalibrate business metrics and measures
- Refresh and validate
- Timeline: 3–4 days

### **Step 5: Agent Tuning** (1–2 weeks)
- Test each agent with real production data
- Adjust agent instructions and example queries based on actual schema and business nuances
- Run UAT question sets to ensure accuracy
- Timeline: 5–7 days

### **Step 6: User Acceptance Testing** (2 weeks)
- Marketing team accesses live app with real data
- Gathers feedback on agent accuracy, UI usability, performance
- Iterate on agent training or UI based on feedback
- Timeline: 10–14 days

### **Step 7: Go-Live** (1 week)
- Enable full marketing team access
- Monitor uptime, query performance, and user adoption
- Provide training and support
- Timeline: 1 week to full rollout

**Total path to production:** 8–12 weeks from schema confirmation to live production.

**Key enabler:** The POC architecture is production-ready. Unlike many proofs of concept, this one isn't a throwaway. We're shipping the real thing; we're just adding your real data.

---

## 8. What's Possible Next: The Roadmap

**Phase 2 features** (after live rollout):

- **More agents:** Sales performance, customer acquisition, profitability analysis, store staffing optimization
- **Real-time dashboards:** Auto-generated charts alongside agent responses (no Power BI required)
- **Saved insights:** Users bookmark answers for next month's campaign review
- **Multi-query workflows:** "First show me tier breakdown, then show me redemptions for each tier"
- **Integration with existing BI:** Export chat insights to Power BI, Tableau, or Excel
- **Scheduled reports:** Agents run queries automatically (e.g., daily campaign performance summary delivered to inbox)
- **Predictive analytics:** Next month's likely churn, optimal promotional timing, segment-level LTV forecasts

All of these are possible without rearchitecting the core system. The foundation is flexible.

---

## 9. Next Steps

**For AAP Leadership:**
1. Review this overview with your data and marketing teams
2. Confirm priority use cases (agents and sample questions should resonate with your team)
3. Commit a database schema point-of-contact to work with our team
4. Schedule deployment kickoff call

**For the Development Team:**
- **Phase A (In progress):** Local development and POC validation complete
- **Phase B (Awaiting AAP confirmation):** Schema mapping and environment provisioning
- **Phase C (Post-Phase B):** User acceptance testing with real data
- **Phase D (Post-UAT):** Go-live and optimization

---

## 10. Contact & Support

For questions about this POC or deployment planning, contact your Microsoft account team.

---

**This proof of concept demonstrates that AAP's marketing team can move at the speed of the business. Let's make it real.**
