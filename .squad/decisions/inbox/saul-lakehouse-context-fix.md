# Decision: Lakehouse Context Auto-Detection in Notebooks

**Date:** 2026-07
**Author:** Saul (Data Engineer)
**Status:** Implemented

## Context

Notebooks uploaded to Fabric via REST API embed lakehouse metadata in the notebook definition, but the Spark runtime may not activate the default database context. This causes `saveAsTable()` with unqualified table names to fail with "No default context found."

## Decision

All Fabric notebooks that use `saveAsTable()` with unqualified names MUST include a context-detection cell near the top that:
1. Checks if `spark.catalog.currentDatabase()` is already bound to a lakehouse
2. Auto-discovers and sets an available lakehouse database if not
3. Fails with a clear user-facing error message if no lakehouse is available

## Rationale

- API upload creates a "phantom binding" — UI shows lakehouse attached, but Spark doesn't have the context
- Manual workaround (detach + reattach lakehouse in portal) is fragile and undiscoverable
- Auto-detection is safe: it only sets context if one isn't already set, and only uses databases that already exist

## Impact

- `notebooks/01-create-sample-data.py` updated with Section 0 context cell
- Any future notebooks that write Delta tables should include the same pattern
- No impact on notebooks that already have a working lakehouse binding (the cell is a no-op in that case)
