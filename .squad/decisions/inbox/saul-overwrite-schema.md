# Decision: Delta overwriteSchema Required on All saveAsTable Calls

**Date:** 2026-07
**Author:** Saul (Data Engineer)
**Status:** Implemented

## Context

Re-running the sample data notebook after a schema change (e.g., adding `campaign_name` to `coupon_rules`) caused a Delta schema mismatch error. Delta's `mode("overwrite")` preserves the existing table schema — it only overwrites data, not structure.

## Decision

All `saveAsTable()` calls in Fabric notebooks that regenerate data from scratch MUST include `.option("overwriteSchema", "true")`. The standard pattern is:

```python
df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable("tablename")
```

## Rationale

- Notebooks should be idempotent — safe to re-run at any time without manual cleanup
- Schema evolution is expected during POC development
- Data is regenerated from scratch each run; preserving stale schemas has no value

## Impact

- `notebooks/01-create-sample-data.py` — All 10 tables updated
- Any future write-Delta notebooks should follow the same pattern
- No impact on semantic model, Data Agent, or downstream consumers (schema only changes when the notebook code changes)
