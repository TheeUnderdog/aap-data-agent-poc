# Data Quality Issues — Sample Data

Tracking unrealistic results from the Fabric Data Agents during demo testing.
When enough issues are collected, use them to fix the generation script or agent instructions.

**Real-world AAP scale reference:**
- ~4,700 stores across the US
- ~40M SpeedPerks loyalty members
- Publicly traded (NYSE: AAP), ~$11B annual revenue

**Current sample data scale:**
- 500 stores, 50K members, 500K transactions, 200K coupons, 5K SKUs
- 3-year span (2023-01-01 to 2026-04-01)

---

## Issues Found

### 1. Campaign results show 1 issued / 1 redeemed / 100% rate
- **Seen:** Ignition returns "BTS % Off #68 (1 issued, 1 redeemed)" and similar tiny counts with 100% redemption
- **Question asked:** "Which campaigns had the highest response rate this quarter?"
- **Root cause:** Two compounding problems:
  1. **Agent queries `rule_name` instead of `campaign_name`.** Rule names like "Holiday BOGO #3" look like campaign names to the LLM, but they're individual coupon rules (100 total). The actual campaign grouping column is `campaign_name` (10 campaigns: Holiday Blitz, Spring Tune-Up, etc.)
  2. **Narrow time filter + rule-level granularity** produces single-digit counts per rule
- **Fix options:**
  - (a) Rename rule names to not look like campaigns: "Rule-003: BOGO" instead of "Holiday BOGO #3"
  - (b) Add a `campaigns` table so the agent has a clear campaign entity to query
  - (c) Update Ignition agent instructions to say: "For campaign analysis, always GROUP BY `campaign_name` from `coupon_rules`, not by `rule_name`"
  - (d) All of the above
- **Recommended:** (d) -- fix the data model AND the instructions
- **Status:** Open

---

## Notes

- Add new issues below as they surface during demo testing
- For each: what was asked, what came back, what should it look like
- Fix priority: generation script bugs first, then agent instruction tuning
