# Decision: Category-Specific Return Rate Multipliers

**Author:** Saul (Data Engineer)
**Date:** 2026-07
**Status:** Implemented

## Context

Sanity check (Block 4) flagged that return rates had near-zero variance across product categories (0.1pp spread). This is unrealistic — in auto parts retail, electronics have much higher return rates than consumables like oil and coolant.

## Decision

Added per-category return rate multipliers to the transaction items generation in `notebooks/01-create-sample-data.py`:

- `BASE_ITEM_RETURN_RATE = 0.03` (3% base per-item return rate on purchase transactions)
- `CATEGORY_RETURN_MULTIPLIER` dict covers all 10 product categories
- Return transactions: all items remain returns (unchanged behavior)
- Purchase transactions: each item independently evaluated for return based on `BASE_ITEM_RETURN_RATE * multiplier`

## Impact

- **Sanity check:** Should resolve the "Category return variance — WARN" finding
- **Semantic model / Data Agent:** No schema changes — `is_return` column type and semantics unchanged
- **Downstream queries:** Category-level return analysis queries now produce meaningful variance
- **Overall return rate:** Stays in 5-12% range; just with realistic spread across categories
