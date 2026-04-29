# Session Log: Data Generator Gaps Analysis

**Date:** 2026-04-26T00:55Z  
**Agent:** Saul (Data Engineer)  
**Trigger:** Dave's Fabric Data Agent test revealed empty columns in weekday/weekend × channel performance query

---

## Summary

Saul audited the sample data generator used in the POC data pipeline and identified 13 critical gaps affecting Data Agent query quality:

- **3 Critical:** Day-of-week weighting, channel independence, temporal violations (txns before enrollment)
- **6 Significant:** Time-of-day patterns, store uniformity, member geography, hub/retail parity, campaign lift, data integrity  
- **4 Minor:** Points balance sequencing, coupon references, region distribution, status changes

---

## Key Finding

Root cause of Dave's empty-column bug: `weighted_random_date()` has zero day-of-week logic, so "weekday in-store" queries return meaningless results because all days have identical channel mix (~71.5% weekday regardless of store_type or tier).

---

## Recommended Action

Implement fixes #1-#4 (high-impact, low-effort):
1. Add DOW_WEIGHTS to weighted_random_date()
2. Make channel weights conditional on store_type/DOW/tier
3. Clamp transaction dates ≥ enrollment date
4. Use log-normal distribution for store traffic

---

## Deliverable

`.squad/decisions/inbox/saul-data-gaps-analysis.md` — 13-gap comprehensive report with prioritized roadmap
