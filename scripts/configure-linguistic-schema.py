#!/usr/bin/env python3
"""
Configure linguistic schema (synonyms) and AI instructions for the
AAP Rewards Loyalty semantic model via the Fabric REST API.

Updates the semantic model definition to include:
  1. Copilot/Instructions/instructions.md — AI business context
  2. Copilot settings — enable Q&A / Copilot features
  3. Linguistic metadata (synonyms) — table, column, and value synonyms
     embedded in the model definition

The Fabric semantic model definition supports a Copilot/ folder structure:
  Copilot/
  ├── Instructions/
  │   ├── instructions.md       ← AI instructions text
  │   └── version.json
  ├── settings.json             ← Copilot/Q&A settings
  └── version.json

Synonyms are delivered via the linguistic metadata on the model culture,
which Fabric stores as part of the LSDL (Linguistic Schema Definition Language).

Usage:
    python scripts/configure-linguistic-schema.py --dry-run
    python scripts/configure-linguistic-schema.py
    python scripts/configure-linguistic-schema.py --model-name "My Model"

References:
    - https://learn.microsoft.com/rest/api/fabric/articles/item-management/definitions/semantic-model-definition
    - https://learn.microsoft.com/power-bi/create-reports/copilot-prepare-data-ai
    - https://learn.microsoft.com/power-bi/natural-language/q-and-a-tooling-advanced
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

# Ensure UTF-8 output regardless of system locale
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"
FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"

DEFAULT_MODEL_NAME = "AAP Rewards Loyalty Model"

# ─── Table Synonyms ──────────────────────────────────────────────────────
# Source: docs/semantic-model-architecture.md §2.3
TABLE_SYNONYMS = {
    "loyalty_members": [
        "members", "customers", "loyalty customers", "rewards members",
        "program members", "enrollees",
    ],
    "transactions": [
        "sales", "purchases", "orders", "transaction history",
        "purchase history",
    ],
    "stores": [
        "locations", "shops", "retail locations", "branches",
        "store locations",
    ],
    "sku_reference": [
        "products", "items", "SKUs", "parts", "auto parts", "merchandise",
        "catalog", "product catalog",
    ],
    "coupons": [
        "vouchers", "discount codes", "promo codes", "promotions", "offers",
    ],
    "coupon_rules": [
        "campaigns", "coupon campaigns", "promotion rules", "discount rules",
    ],
    "member_points": [
        "points", "points history", "points transactions", "rewards points",
        "points log", "points activity", "points ledger",
    ],
    "csr": [
        "agents", "service reps", "customer service agents",
        "support agents", "representatives",
    ],
    "csr_activities": [
        "service calls", "CSR actions", "agent activity",
        "support interactions", "service log",
    ],
    "transaction_items": [
        "line items", "order items", "purchase items", "cart items",
        "item details",
    ],
}

# ─── Column Synonyms ─────────────────────────────────────────────────────
# Source: docs/semantic-model-architecture.md §2.3
COLUMN_SYNONYMS = {
    "loyalty_members.tier": [
        "loyalty tier", "member tier", "rewards tier",
        "membership level", "tier level",
    ],
    "loyalty_members.member_status": [
        "status", "account status", "membership status",
    ],
    "loyalty_members.enrollment_date": [
        "join date", "signup date", "registration date", "member since",
    ],
    "transactions.total": [
        "amount", "sale amount", "transaction amount", "order total",
        "revenue",
    ],
    "transactions.transaction_date": [
        "date", "sale date", "purchase date", "order date",
    ],
    "transactions.channel": [
        "sales channel", "purchase channel", "order channel",
    ],
    "transactions.transaction_type": [
        "type", "sale type",
    ],
    "stores.region": [
        "area", "territory", "district", "market",
    ],
    "stores.store_type": [
        "type", "format", "store format",
    ],
    "sku_reference.category": [
        "product category", "part category", "department",
    ],
    "sku_reference.brand": [
        "manufacturer", "make", "brand name",
    ],
    "sku_reference.unit_price": [
        "price", "retail price", "product price",
    ],
    "sku_reference.is_bonus_eligible": [
        "bonus eligible", "bonus points eligible", "earns bonus points",
    ],
    "coupons.status": [
        "coupon status", "redemption status", "state",
    ],
    "coupon_rules.rule_name": [
        "campaign name", "promotion name", "coupon name",
    ],
    "coupon_rules.discount_type": [
        "discount kind", "offer type",
    ],
    "coupon_rules.target_tier": [
        "targeted tier", "tier targeting", "eligible tier",
    ],
    "member_points.activity_type": [
        "point type", "points action", "earn or redeem",
    ],
    "csr.csr_name": [
        "agent name", "rep name", "CSR agent",
    ],
    "csr.is_active": [
        "active status", "status", "employment status",
    ],
    "csr_activities.activity_type": [
        "action type", "interaction type", "service type",
    ],
}

# ─── Value Synonyms ──────────────────────────────────────────────────────
# Source: docs/semantic-model-architecture.md §2.3
VALUE_SYNONYMS = {
    "transactions.transaction_type": {
        "purchase": ["sale", "buy", "bought"],
        "return": ["refund", "returned"],
    },
    "transactions.channel": {
        "in-store": ["store", "brick and mortar", "in person", "walk-in"],
        "online": ["web", "website", "ecommerce", "digital"],
        "phone": ["call", "telephone", "phone order"],
    },
    "loyalty_members.tier": {
        "Bronze": ["basic", "starter", "entry level"],
        "Silver": ["second tier", "mid-tier"],
        "Gold": ["third tier", "premium"],
        "Platinum": ["top tier", "highest tier", "VIP", "elite"],
    },
    "loyalty_members.member_status": {
        "active": ["current", "enrolled", "participating"],
        "inactive": ["churned", "lapsed", "dormant", "cancelled"],
    },
    "coupons.status": {
        "redeemed": ["used", "applied", "claimed"],
        "expired": ["lapsed", "timed out"],
        "voided": ["cancelled", "removed", "revoked"],
    },
    "member_points.activity_type": {
        "earn": ["earned", "accrual", "credit"],
        "redeem": ["redeemed", "spent", "burned", "used"],
        "bonus": ["bonus points", "bonus reward"],
    },
    "stores.store_type": {
        "hub": ["full-service store", "main store"],
        "satellite": ["small format", "mini store"],
    },
}

# ─── AI Instructions ─────────────────────────────────────────────────────
# Source: docs/semantic-model-architecture.md §2.4
AI_INSTRUCTIONS = """BUSINESS CONTEXT:
This is the AAP (Advanced Auto Parts) Rewards & Loyalty program database.
AAP is a national auto parts retailer with approximately 500 stores across the United States.
The rewards program has ~5,000 members across four tiers: Bronze, Silver, Gold, and Platinum.

TIER DEFINITIONS:
- Bronze: Entry level. All new members start at Bronze. 1× points multiplier.
- Silver: $500+ annual spend. 1.5× points multiplier.
- Gold: $1,500+ annual spend. 2× points multiplier.
- Platinum: $3,000+ annual spend. 3× points multiplier.

POINTS SYSTEM:
- Members earn 1 base point per dollar spent (before multiplier).
- Points value: approximately $0.01 per point for liability calculations.
- Points can expire after 12 months of account inactivity.

IMPORTANT CALCULATION RULES:
- Revenue should ALWAYS filter to transaction_type = 'purchase'. Returns should not be included in revenue.
- Return Rate = Return Count / Purchase Count (not total transactions).
- Coupon Redemption Rate = Redeemed / Issued (not expired or voided in denominator).
- "Active members" means member_status = 'active'.
- Churn risk: members with 180+ days since last purchase are considered at risk.

DATA TIME RANGE:
- Transaction data spans January 2025 through April 2026.
- Always mention the date range when reporting trends.

PRODUCT CONTEXT:
- "Skip SKU" (is_skip_sku = true) means the product is excluded from earning loyalty points.
- "Bonus eligible" (is_bonus_eligible = true) means the product earns extra bonus points.
- Auto parts categories include: Batteries, Oil & Fluids, Brakes, Filters, Wipers, Spark Plugs, Lighting, Coolant, Accessories, Electrical.

COUPON SYSTEM:
- Coupons are issued under campaign rules (coupon_rules table).
- discount_type is 'percent' (percentage off) or 'fixed_dollar' (flat amount off).
- target_tier restricts the campaign to members of a specific tier. NULL means all tiers.
- Coupon lifecycle: issued → redeemed OR expired OR voided.

STORE TYPES:
- "hub" stores are full-service, larger format stores.
- "satellite" stores are smaller neighborhood format.

TABLE NAME GUIDANCE:
- The "csr" table contains Customer Service Representatives (agents, reps, support staff).
  When users say "agents", "reps", "representatives", or "support agents", they mean the csr table.
- The "csr_activities" table contains CSR interaction logs (service calls, agent activity).
  When users say "service calls", "agent activity", or "support interactions", they mean csr_activities.
- The "coupon_rules" table contains campaign definitions.
  When users say "campaigns", "promotions", or "promotion rules", they mean coupon_rules.
- The "member_points" table tracks all points activity (earn, redeem, adjust, expire).
  When users say "points history" or "points transactions", they mean member_points.
- The "loyalty_members" table has member profiles.
  When users say "customers", "members", or "enrollees", they mean loyalty_members.
- The "sku_reference" table contains product/SKU catalog data.
  When users say "products", "items", "SKUs", or "parts", they mean sku_reference.
- The "transaction_items" table contains line-item details for each transaction.
  When users say "line items", "order items", or "purchase items", they mean transaction_items.
"""


def read_env_file(path: Path) -> dict:
    """Read a .env file into a dictionary."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r'^\s*([A-Z_]+)\s*=\s*([^#]+?)(?:\s*#.*)?$', line)
            if m:
                env[m.group(1)] = m.group(2).strip()
    return env


def get_credential(auth_method: str, tenant_id: str = ""):
    """Get Azure credential for Fabric API authentication."""
    try:
        from azure.identity import DeviceCodeCredential, InteractiveBrowserCredential
    except ImportError:
        print("❌ azure-identity not found. Install: pip install azure-identity")
        sys.exit(1)

    kwargs = {"tenant_id": tenant_id} if tenant_id else {}
    if auth_method == "device-code":
        print("🔑 Device code auth — check terminal for instructions...")
        return DeviceCodeCredential(**kwargs)
    else:
        print("🔑 Browser auth — a login window will open...")
        return InteractiveBrowserCredential(**kwargs)


def find_model_id(workspace_id: str, model_name: str, headers: dict) -> str:
    """Find a semantic model by name in the workspace. Returns model ID or exits."""
    r = requests.get(
        f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels",
        headers=headers,
    )
    if r.status_code != 200:
        print(f"❌ Failed to list semantic models ({r.status_code}): {r.text[:300]}")
        sys.exit(1)

    for sm in r.json().get("value", []):
        if sm["displayName"] == model_name:
            return sm["id"]

    print(f"❌ Semantic model '{model_name}' not found in workspace {workspace_id}")
    sys.exit(1)


def get_model_definition(workspace_id: str, model_id: str, headers: dict) -> dict:
    """GET the current semantic model definition (TMDL parts)."""
    url = f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{model_id}/getDefinition"

    r = requests.post(url, headers=headers, json={"format": "TMDL"})

    if r.status_code == 200:
        return r.json()

    if r.status_code == 202:
        operation_id = r.headers.get("x-ms-operation-id", "")
        location = r.headers.get("Location", "")
        retry_after = int(r.headers.get("Retry-After", "5"))
        print(f"   ⏳ Fetching definition (operation: {operation_id})...")

        for attempt in range(30):
            time.sleep(max(retry_after, 3))
            poll_url = location or f"{FABRIC_API}/operations/{operation_id}"
            poll_r = requests.get(poll_url, headers=headers)

            if poll_r.status_code == 200:
                poll_data = poll_r.json()
                status = poll_data.get("status", "").lower()
                if status == "succeeded":
                    result_url = f"{FABRIC_API}/operations/{operation_id}/result"
                    result_r = requests.get(result_url, headers=headers)
                    if result_r.status_code == 200:
                        return result_r.json()
                    print(f"   ❌ Result fetch failed ({result_r.status_code})")
                    sys.exit(1)
                elif status == "failed":
                    print(f"   ❌ getDefinition failed: {json.dumps(poll_data, indent=2)}")
                    sys.exit(1)
                else:
                    print(f"   ⏳ Status: {status} (attempt {attempt + 1}/30)")
        print("   ❌ Timed out waiting for getDefinition")
        sys.exit(1)

    print(f"❌ getDefinition failed ({r.status_code}): {r.text[:500]}")
    sys.exit(1)


def update_model_definition(workspace_id: str, model_id: str, definition: dict, headers: dict):
    """POST the updated semantic model definition (long-running operation)."""
    url = f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{model_id}/updateDefinition"

    r = requests.post(url, headers=headers, json={"definition": definition})

    if r.status_code == 200:
        print("   ✅ Definition updated successfully!")
        return

    if r.status_code == 202:
        operation_id = r.headers.get("x-ms-operation-id", "")
        location = r.headers.get("Location", "")
        retry_after = int(r.headers.get("Retry-After", "5"))
        print(f"   ⏳ Update in progress (operation: {operation_id})...")

        for attempt in range(60):
            time.sleep(max(retry_after, 3))
            poll_url = location or f"{FABRIC_API}/operations/{operation_id}"
            poll_r = requests.get(poll_url, headers=headers)

            if poll_r.status_code == 200:
                poll_data = poll_r.json()
                status = poll_data.get("status", "").lower()
                if status == "succeeded":
                    print("   ✅ Definition updated successfully!")
                    return
                elif status == "failed":
                    error = poll_data.get("error", {})
                    print(f"   ❌ Update failed: {json.dumps(error, indent=2)}")
                    sys.exit(1)
                else:
                    print(f"   ⏳ Status: {status} (attempt {attempt + 1}/60)")
        print("   ❌ Timed out waiting for updateDefinition")
        sys.exit(1)

    print(f"❌ updateDefinition failed ({r.status_code}): {r.text[:500]}")
    sys.exit(1)


def encode_part(path: str, content: str) -> dict:
    """Create a base64-encoded definition part."""
    return {
        "path": path,
        "payload": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "payloadType": "InlineBase64",
    }


def build_copilot_parts() -> list:
    """
    Build the Copilot/ folder definition parts for AI instructions and settings.

    Structure matches the Fabric semantic model definition spec:
      Copilot/Instructions/instructions.md  — AI instructions text
      Copilot/Instructions/version.json     — version metadata
      Copilot/settings.json                 — Copilot/Q&A enabled
      Copilot/version.json                  — Copilot folder version
    """
    parts = []

    # AI instructions — the core business context block
    parts.append(encode_part(
        "Copilot/Instructions/instructions.md",
        AI_INSTRUCTIONS.strip(),
    ))

    # Version files — $schema is required by Fabric parser
    copilot_version_schema = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/copilot/1.0.0/schema.json"
    instructions_version_schema = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/copilot/instructions/1.0.0/schema.json"

    parts.append(encode_part(
        "Copilot/Instructions/version.json",
        json.dumps({"$schema": instructions_version_schema, "version": "1.0.0"}, indent=2),
    ))

    parts.append(encode_part(
        "Copilot/version.json",
        json.dumps({"$schema": copilot_version_schema, "version": "1.0.0"}, indent=2),
    ))

    # Note: Copilot/settings.json is NOT included — unknown property names
    # cause parse errors. Copilot features are enabled via the Fabric portal.

    return parts


def build_linguistic_metadata_json() -> str:
    """
    Build the Q&A linguistic metadata JSON content with all synonyms.

    This follows the Power BI Linguistic Schema (LSDL) format used by
    Q&A and Copilot to understand alternative names for tables, columns,
    and values in natural language queries.
    """
    entities = {}

    for table_name, synonyms in TABLE_SYNONYMS.items():
        entity = {
            "Definition": {
                "Binding": {
                    "ConceptualEntity": table_name,
                },
            },
            "State": "UserAuthored",
            "Words": [[s] for s in synonyms],
        }

        # Add column synonyms for this table
        properties = {}
        for col_key, col_synonyms in COLUMN_SYNONYMS.items():
            tbl, col = col_key.split(".", 1)
            if tbl == table_name:
                properties[col] = {
                    "Definition": {
                        "Binding": {
                            "ConceptualProperty": col_key,
                        },
                    },
                    "State": "UserAuthored",
                    "Words": [[s] for s in col_synonyms],
                }

        # Add value synonyms for columns in this table
        for col_key, val_map in VALUE_SYNONYMS.items():
            tbl, col = col_key.split(".", 1)
            if tbl == table_name:
                if col not in properties:
                    properties[col] = {
                        "Definition": {
                            "Binding": {
                                "ConceptualProperty": col_key,
                            },
                        },
                        "State": "UserAuthored",
                        "Words": [],
                    }
                # Add value synonyms as Terms
                terms = {}
                for value, val_synonyms in val_map.items():
                    terms[value] = {
                        "State": "UserAuthored",
                        "Words": [[s] for s in val_synonyms],
                    }
                properties[col]["Terms"] = terms

        if properties:
            entity["Properties"] = properties

        entities[table_name] = entity

    linguistic_metadata = {
        "Version": "1.0.0",
        "Language": "en-US",
        "DynamicImprovement": "HighConfidence",
        "Entities": entities,
    }

    return json.dumps(linguistic_metadata, indent=2)


def build_pbism_content() -> str:
    """Build definition.pbism with Q&A enabled."""
    return json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "5.0",
        "settings": {
            "qnaEnabled": True,
        },
    }, indent=2)


def merge_definition(existing_def: dict, new_parts: list) -> dict:
    """
    Merge new definition parts into existing definition.
    Replaces parts with matching paths, adds new ones.
    """
    existing_parts = existing_def.get("parts", [])
    parts_by_path = {p["path"]: p for p in existing_parts}

    for new_part in new_parts:
        parts_by_path[new_part["path"]] = new_part

    return {"parts": list(parts_by_path.values())}


def print_synonym_summary():
    """Print a human-readable summary of all synonyms being configured."""
    print("   ╔══════════════════════════════════════════════════════╗")
    print("   ║  TABLE SYNONYMS                                    ║")
    print("   ╚══════════════════════════════════════════════════════╝")
    for table, syns in TABLE_SYNONYMS.items():
        print(f"   📋 {table}")
        print(f"      → {', '.join(syns)}")
    print()

    print("   ╔══════════════════════════════════════════════════════╗")
    print("   ║  COLUMN SYNONYMS                                   ║")
    print("   ╚══════════════════════════════════════════════════════╝")
    for col_key, syns in COLUMN_SYNONYMS.items():
        print(f"   📎 {col_key}")
        print(f"      → {', '.join(syns)}")
    print()

    print("   ╔══════════════════════════════════════════════════════╗")
    print("   ║  VALUE SYNONYMS                                    ║")
    print("   ╚══════════════════════════════════════════════════════╝")
    for col_key, val_map in VALUE_SYNONYMS.items():
        print(f"   🏷️  {col_key}")
        for value, syns in val_map.items():
            print(f"      \"{value}\" → {', '.join(syns)}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Configure linguistic schema and AI instructions for AAP Rewards Loyalty semantic model"
    )
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser",
                        help="Authentication method")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME,
                        help=f"Semantic model name (default: {DEFAULT_MODEL_NAME})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without calling the Fabric API")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   📊 AAP Rewards Loyalty — Linguistic Schema Config    ║")
    print("║   Synonyms + AI Instructions via Fabric REST API       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # ─── Read environment ─────────────────────────────────────────────
    env = read_env_file(ENV_FILE)
    workspace_id = env.get("FABRIC_WORKSPACE_ID", "")
    if not workspace_id:
        print("❌ Missing FABRIC_WORKSPACE_ID in .env.fabric")
        sys.exit(1)

    print(f"   Workspace:  {workspace_id}")
    print(f"   Model Name: {args.model_name}")
    print(f"   Mode:       {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    # ─── Build all definition parts ───────────────────────────────────
    print("── Building definition parts ─────────────────────────────")
    print()

    # 1. Copilot folder parts (AI instructions + settings)
    copilot_parts = build_copilot_parts()
    print(f"   ✅ Copilot/Instructions/instructions.md ({len(AI_INSTRUCTIONS)} chars)")
    print(f"   ✅ Copilot version files")
    print()

    # 2. Linguistic metadata (synonyms) as a standalone JSON part
    linguistic_json = build_linguistic_metadata_json()
    linguistic_part = encode_part(
        "Copilot/linguisticMetadata.json",
        linguistic_json,
    )
    copilot_parts.append(linguistic_part)
    print(f"   ✅ Copilot/linguisticMetadata.json ({len(linguistic_json)} chars)")

    total_table_synonyms = sum(len(v) for v in TABLE_SYNONYMS.values())
    total_column_synonyms = sum(len(v) for v in COLUMN_SYNONYMS.values())
    total_value_synonyms = sum(
        sum(len(vs) for vs in vm.values())
        for vm in VALUE_SYNONYMS.values()
    )
    print(f"      • {len(TABLE_SYNONYMS)} tables with {total_table_synonyms} synonyms")
    print(f"      • {len(COLUMN_SYNONYMS)} columns with {total_column_synonyms} synonyms")
    print(f"      • {len(VALUE_SYNONYMS)} columns with {total_value_synonyms} value synonyms")
    print()

    # 3. Updated definition.pbism with Q&A enabled
    pbism_content = build_pbism_content()
    pbism_part = encode_part("definition.pbism", pbism_content)
    copilot_parts.append(pbism_part)
    print(f"   ✅ definition.pbism (qnaEnabled: true)")
    print()

    # ─── Synonym detail summary ───────────────────────────────────────
    print("── Synonym Configuration Detail ──────────────────────────")
    print()
    print_synonym_summary()

    # ─── AI Instructions preview ──────────────────────────────────────
    print("── AI Instructions Preview ──────────────────────────────")
    print()
    for line in AI_INSTRUCTIONS.strip().split("\n")[:10]:
        print(f"   {line}")
    print(f"   ... ({len(AI_INSTRUCTIONS.strip().splitlines())} total lines)")
    print()

    # ─── Definition parts summary ─────────────────────────────────────
    print("── Definition Parts to Add/Update ───────────────────────")
    print()
    for part in copilot_parts:
        payload_size = len(base64.b64decode(part["payload"]))
        print(f"   📄 {part['path']} ({payload_size:,} bytes)")
    print()

    if args.dry_run:
        print("═══════════════════════════════════════════════════════")
        print("   🔍 DRY RUN — no API calls made.")
        print("   To apply changes: re-run without --dry-run")
        print("═══════════════════════════════════════════════════════")
        print()

        # Save generated artifacts for inspection
        debug_dir = SCRIPT_DIR
        debug_path = debug_dir / "linguistic-schema-preview.json"
        debug_path.write_text(linguistic_json, encoding="utf-8")
        print(f"   📄 Linguistic metadata saved to: {debug_path}")

        instructions_path = debug_dir / "ai-instructions-preview.md"
        instructions_path.write_text(AI_INSTRUCTIONS.strip(), encoding="utf-8")
        print(f"   📄 AI instructions saved to: {instructions_path}")
        print()
        return

    # ─── Authenticate and execute ─────────────────────────────────────
    print("── Connecting to Fabric API ─────────────────────────────")
    print()

    tenant_id = env.get("ENTRA_TENANT_ID", "")
    credential = get_credential(args.auth, tenant_id=tenant_id)
    token = credential.get_token(FABRIC_SCOPE).token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Find model ID
    print(f"   Looking up '{args.model_name}'...")
    model_id = find_model_id(workspace_id, args.model_name, headers)
    print(f"   ✅ Found model ID: {model_id}")
    print()

    # Get current definition
    print("   Fetching current model definition...")
    current_def = get_model_definition(workspace_id, model_id, headers)
    existing_count = len(current_def.get("definition", {}).get("parts", []))
    print(f"   ✅ Retrieved {existing_count} existing definition parts")
    print()

    # Merge new parts into existing definition
    existing_definition = current_def.get("definition", {"parts": []})
    merged = merge_definition(existing_definition, copilot_parts)
    print(f"   Merged definition: {len(merged['parts'])} total parts")
    print()

    # Update definition
    print("   Uploading updated definition...")
    update_model_definition(workspace_id, model_id, merged, headers)
    print()

    print("═══════════════════════════════════════════════════════")
    print("   🎉 Linguistic schema and AI instructions configured!")
    print()
    print("   What was deployed:")
    print(f"      • AI instructions ({len(AI_INSTRUCTIONS.strip().splitlines())} lines of business context)")
    print(f"      • {total_table_synonyms} table synonyms across {len(TABLE_SYNONYMS)} tables")
    print(f"      • {total_column_synonyms} column synonyms across {len(COLUMN_SYNONYMS)} columns")
    print(f"      • {total_value_synonyms} value synonyms")
    print(f"      • Q&A / Copilot enabled in model settings")
    print()
    print("   Next steps:")
    print("   1. Open the model in Fabric portal → Prep data for AI")
    print("   2. Verify synonyms appear in the linguistic schema")
    print("   3. Test with natural language queries (e.g., 'show me agents')")
    print(f"   4. Portal: https://app.fabric.microsoft.com/groups/{workspace_id}")
    print("═══════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
