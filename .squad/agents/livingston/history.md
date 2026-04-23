# Livingston — History

## Project Context

- **Project:** AAP Data Agent POC for Advanced Auto Parts
- **User:** Dave Grobleski
- **Stack:** Microsoft Fabric, Azure PostgreSQL, Fabric Data Agent
- **Key requirement:** Data schema must be componentized — placeholder schema for rewards/loyalty based on logical AAP domain knowledge, swappable when real schema arrives
- **Customer context:** AAP has multiple Fabric capacities, heavy PBI user, uses Fabric for PBI only today. Rewards/loyalty data lives in Azure PostgreSQL.

## Learnings

### Data Schema Design (docs/data-schema.md)
- **Created comprehensive placeholder schema** for AAP rewards/loyalty program including 9 table groups: members, transactions, points, rewards, campaigns
- **Implemented view-based abstraction layer**: All consuming components (Data Agent, API, Web App) query 7 contract views (`v_member_summary`, `v_transaction_history`, etc.) instead of raw tables — enables zero-code-change schema swapping
- **Full PostgreSQL DDL with proper indexes**: Designed realistic schema based on auto parts retail domain knowledge (50K members, 500K transactions, 500 products across categories like batteries, engine parts, brakes)
- **Sample query library**: 20 natural language → SQL query pairs covering member analysis, transaction metrics, points/rewards tracking, campaign effectiveness, and advanced analytics
- **Schema swap procedure documented**: Step-by-step process for replacing placeholder with real AAP schema when provided, including validation checklist and rollback plan
- **Key design principle**: Components depend on the INTERFACE (views), not the IMPLEMENTATION (tables) — makes schema componentized and swappable as required

**Cross-Team Awareness:**
- Danny (Lead/Architect) has created technical architecture and phased implementation plan covering all 4 phases
- Danny's schema abstraction strategy documentation directly references our view-based contract approach
- Architecture includes detailed Phase 2 (PostgreSQL mirroring) and Phase 3 (Data Agent) guidance that will consume our schema contract views
