# Decision: Category-Weighted Product Selection for Return Transactions

**Date:** 2026-07
**Author:** Saul (Data Engineer)
**Status:** Implemented

## Context

The sanity check found all 11 product categories had identical ~8% return rates. This is unrealistic — in auto parts retail, electrical components and accessories are returned far more often than consumables like oil and coolant.

## Decision

Use **category-weighted product selection** for return transactions instead of per-item return flags. When generating items for a return transaction, products are selected using `random.choices()` with category-specific weights rather than uniform `random.choice()`.

## Weight Values

| Category     | Weight | Rationale                              |
|-------------|--------|----------------------------------------|
| Electrical  | 3.0    | Wrong part number, compatibility       |
| Lighting    | 2.5    | Fitment / compatibility                |
| Accessories | 2.2    | Fitment, impulse buy regret            |
| Batteries   | 1.8    | Warranty claims, wrong group size      |
| Brakes      | 1.3    | Wrong application, brand preference    |
| Spark Plugs | 1.1    | Wrong gap, wrong thread                |
| Wipers      | 0.8    | Cheap, but fitment issues              |
| Filters     | 0.5    | Cheap consumable, usually correct      |
| Engine Oil  | 0.3    | Consumable, can't return opened        |
| Coolant     | 0.3    | Consumable liquid, rarely returned     |

Weights are relative — `random.choices()` normalizes them. The 10x spread (0.3 to 3.0) creates meaningful per-category return rate variance without being extreme.

## What This Replaces

Removed the old `BASE_ITEM_RETURN_RATE` (3%) + `CATEGORY_RETURN_MULTIPLIER` mechanism that flipped individual items to "return" inside purchase transactions. Dave explicitly rejected that approach — returns should be whole transactions with a different product mix, not per-item flags on purchases.

## Impact

- Transaction-level return rate: unchanged (8%)
- Per-category return rates: now vary naturally based on product mix in return transactions
- No schema changes
- Sanity check "category return rate variance" should now pass
