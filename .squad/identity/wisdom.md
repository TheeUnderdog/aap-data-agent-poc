---
last_updated: 2026-04-23T19:30:08.879Z
---

# Team Wisdom

Reusable patterns and heuristics learned through work. NOT transcripts — each entry is a distilled, actionable insight.

## Patterns

**Pattern:** TMDL Semantic Model Structure & Schema Versioning (2026-04-24)  
**Context:** When deploying Fabric semantic models using TMDL format to REST API.  
**Insight:** TMDL deployments require two components: `definition.pbism` (model-level metadata) and table definition files. The pbism file must specify `version: "5.0"` and include matching `$schema` URL (`https://powerbi.microsoft.com/schema/semantic-model/definition/5.0/semantic-model-definition.json`). Mismatch between version and schema URL causes REST API validation errors. Always validate both before deployment.

**Pattern:** TMDL Property Support—Table Level vs. Column/Measure Level (2026-04-24)  
**Context:** When authoring TMDL table definitions for semantic models.  
**Insight:** TMDL is stricter than Power BI datasets about property support. The properties `description` and `lineageTag` are NOT supported at table level—only at column and measure level. Attempting to deploy table-level descriptions causes TMDL validation failures. Move all documentation to column descriptions. Partition source definitions use `source =` syntax (not `expression:`).

**Pattern:** Direct Delta Table Sourcing vs. SQL View Middleware (2026-04-24)  
**Context:** When deciding how to abstract data for semantic models and Data Agents.  
**Insight:** Semantic models should source Delta tables directly, not through SQL views as middleware. SQL views are useful for query abstraction but do not appear as workspace-level items in Fabric and add unnecessary layers. Define business logic in DAX measures instead. Result: simpler architecture, fewer deployment steps, and more maintainable code.

<!-- Append entries below. Format: **Pattern:** description. **Context:** when it applies. -->
