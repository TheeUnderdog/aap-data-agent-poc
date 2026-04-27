#!/usr/bin/env python3
"""
Create a Fabric Semantic Model directly from Lakehouse Delta tables.

Sources the 10 Delta tables (loyalty_members, transactions, stores, products,
coupons, coupon_rules, points_ledger, csr, csr_activities, audit_log) with
relationships, DAX measures, and business-friendly descriptions. No SQL views
needed — the semantic model IS the abstraction layer.

Uses the Fabric REST API with TMDL (Tabular Model Definition Language).

Usage:
    python scripts/create-semantic-model.py
    python scripts/create-semantic-model.py --dry-run
    python scripts/create-semantic-model.py --force   # delete + recreate
    python scripts/create-semantic-model.py --auth device-code

References:
    - https://learn.microsoft.com/rest/api/fabric/semanticmodel/items/create-semantic-model
    - https://learn.microsoft.com/analysis-services/tmdl/tmdl-overview
"""

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"
FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"

DEFAULT_MODEL_NAME = "AAP Rewards Loyalty Model"

# ─── Lakehouse Delta tables ──────────────────────────────────────────────
# IMPORTANT: These MUST match the actual Delta tables created by the notebook
# (notebooks/01-create-sample-data.py). Column names and types are derived from
# the notebook's PySpark schemas. Column tuples: (name, type, label, description)
LAKEHOUSE_TABLES = {
    "loyalty_members": {
        "description": "Loyalty program members — profiles, tiers, contact info. Each row is one rewards program member.",
        "columns": [
            ("member_id", "int64", "Member ID", "Unique identifier for each loyalty program member"),
            ("first_name", "string", "First Name", "Member's first name"),
            ("last_name", "string", "Last Name", "Member's last name"),
            ("email", "string", "Email", "Member's email address for communications"),
            ("phone", "string", "Phone", "Member's phone number"),
            ("enrollment_date", "dateTime", "Enrollment Date", "Date when the member joined the loyalty program"),
            ("enrollment_source", "string", "Enrollment Source", "How the member joined: POS, Ecomm, or CustomerFirst"),
            ("member_status", "string", "Member Status", "Account status: active, inactive, or suspended"),
            ("tier", "string", "Tier", "Current loyalty tier: Bronze, Silver, Gold, or Platinum. Higher tiers earn more points per dollar."),
            ("opt_in_email", "boolean", "Opt-in Email", "Whether the member has opted in to receive email marketing communications"),
            ("opt_in_sms", "boolean", "Opt-in SMS", "Whether the member has opted in to receive SMS/text marketing messages"),
            ("diy_account_id", "string", "DIY Account ID", "Link to the member's DIY (Do-It-Yourself) commercial account, if any"),
            ("created_at", "dateTime", "Created At", "Timestamp when this member record was created"),
            ("updated_at", "dateTime", "Updated At", "Timestamp when this member record was last updated"),
        ],
    },
    "transactions": {
        "description": "Purchase and return transactions across all channels. Includes in-store, online, and mobile channels.",
        "columns": [
            ("transaction_id", "int64", "Transaction ID", "Unique identifier for each transaction"),
            ("member_id", "int64", "Member ID", "Links to loyalty_members table. Member who made this transaction."),
            ("store_id", "int64", "Store ID", "Links to stores table. Store where transaction occurred."),
            ("transaction_date", "dateTime", "Transaction Date", "Date when the transaction was completed"),
            ("transaction_type", "string", "Transaction Type", "Either 'purchase' (sale) or 'return' (refund). Revenue calculations should filter to purchases only."),
            ("subtotal", "double", "Subtotal", "Transaction amount before tax in USD"),
            ("tax", "double", "Tax", "Tax amount in USD"),
            ("total", "double", "Total", "Transaction total amount in USD including tax"),
            ("item_count", "int64", "Item Count", "Number of line items (products) in this transaction"),
            ("channel", "string", "Channel", "Sales channel: in-store, online, or mobile"),
            ("order_id", "string", "Order ID", "External order ID for online/mobile orders (NULL for in-store)"),
            ("created_at", "dateTime", "Created At", "Timestamp when this transaction record was created"),
        ],
    },
    "transaction_items": {
        "description": "Line items for each transaction — SKU, quantity, pricing. Approximately 3 items per transaction on average.",
        "columns": [
            ("item_id", "int64", "Item ID", "Unique identifier for each line item"),
            ("transaction_id", "int64", "Transaction ID", "Links to transactions table. Transaction this item belongs to."),
            ("sku", "string", "SKU", "Stock Keeping Unit - links to sku_reference table"),
            ("product_name", "string", "Product Name", "Display name of the product"),
            ("category", "string", "Category", "Primary product category (e.g., Batteries, Brakes, Engine Oil)"),
            ("quantity", "int64", "Quantity", "Number of units purchased"),
            ("unit_price", "double", "Unit Price", "Price per unit in USD"),
            ("line_total", "double", "Line Total", "Total for this line item (quantity × unit_price)"),
            ("is_return", "boolean", "Is Return", "Whether this line item is part of a return transaction"),
        ],
    },
    "stores": {
        "description": "Retail store locations — name, address, region, and type. store_type is either 'retail' (standard) or 'hub' (full-service).",
        "columns": [
            ("store_id", "int64", "Store ID", "Unique identifier for each store location"),
            ("store_name", "string", "Store Name", "Display name of the store"),
            ("city", "string", "City", "City where the store is located"),
            ("state", "string", "State", "Two-letter state code (e.g., 'TX', 'CA')"),
            ("zip_code", "string", "ZIP Code", "Postal code for the store address"),
            ("region", "string", "Region", "Geographic region: Northeast, Southeast, Midwest, Southwest, or West"),
            ("store_type", "string", "Store Type", "Store format: retail (standard) or hub (full-service)"),
            ("opened_date", "dateTime", "Opened Date", "Date when the store was opened"),
        ],
    },
    "sku_reference": {
        "description": "Auto parts product catalog. is_bonus_eligible means the product earns bonus loyalty points. is_skip_sku means the product is excluded from points earning.",
        "columns": [
            ("sku", "string", "SKU", "Stock Keeping Unit - unique product identifier"),
            ("product_name", "string", "Product Name", "Display name of the product"),
            ("category", "string", "Category", "Primary product category (e.g., Batteries, Brakes, Engine Oil)"),
            ("subcategory", "string", "Subcategory", "Product subcategory for finer classification"),
            ("brand", "string", "Brand", "Product brand or manufacturer name"),
            ("unit_price", "double", "Unit Price", "Standard retail price in USD"),
            ("is_bonus_eligible", "boolean", "Bonus Eligible", "Whether this product earns bonus loyalty points (TRUE) or standard points only (FALSE)"),
            ("is_skip_sku", "boolean", "Skip SKU", "Whether this product is excluded from earning loyalty points entirely"),
            ("created_at", "dateTime", "Created At", "Timestamp when this product record was created"),
        ],
    },
    "member_points": {
        "description": "Points earn/burn ledger — every points transaction with running balance. activity_type values: earn, redeem, adjust, expire, bonus.",
        "columns": [
            ("point_id", "int64", "Point ID", "Unique identifier for each points ledger entry"),
            ("member_id", "int64", "Member ID", "Links to loyalty_members. Member whose points were affected."),
            ("activity_date", "dateTime", "Activity Date", "Date when the points activity occurred"),
            ("activity_type", "string", "Activity Type", "Type of points activity: earn, redeem, adjust, expire, or bonus"),
            ("points_amount", "int64", "Points Amount", "Number of points affected. Positive for earn/adjust, negative for redeem/expire."),
            ("balance_after", "int64", "Balance After", "Member's points balance after this transaction"),
            ("source", "string", "Source", "System or process that created this points entry: purchase, campaign, bonus_activity, or manual_adjust"),
            ("reference_id", "string", "Reference ID", "Links to related transaction_id, coupon_id, or other source record"),
            ("description", "string", "Description", "Human-readable description of the points activity"),
            ("created_at", "dateTime", "Created At", "Timestamp when this ledger entry was created"),
        ],
    },
    "coupons": {
        "description": "Issued coupons — status, dates, and redemption tracking. Coupon lifecycle: issued → redeemed/expired/voided.",
        "columns": [
            ("coupon_id", "int64", "Coupon ID", "Unique identifier for each coupon instance"),
            ("coupon_code", "string", "Coupon Code", "Redemption code displayed to the customer"),
            ("coupon_rule_id", "int64", "Coupon Rule ID", "Links to coupon_rules. Campaign that generated this coupon."),
            ("member_id", "int64", "Member ID", "Links to loyalty_members. Member who owns this coupon."),
            ("issued_date", "dateTime", "Issued Date", "Date when the coupon was issued to the member"),
            ("expiry_date", "dateTime", "Expiry Date", "Date when the coupon expires"),
            ("status", "string", "Status", "Coupon lifecycle state: issued, redeemed, expired, or voided"),
            ("redeemed_date", "dateTime", "Redeemed Date", "Date when the coupon was redeemed (NULL if not yet redeemed)"),
            ("redeemed_transaction_id", "int64", "Redeemed Transaction ID", "Links to the transaction where this coupon was used. NULL if not yet redeemed."),
            ("discount_type", "string", "Discount Type", "Type of discount: percentage, fixed, or bogo"),
            ("discount_value", "double", "Discount Value", "Discount amount or percentage value"),
            ("source_system", "string", "Source System", "System that issued the coupon: GK, POS, or Ecomm"),
            ("created_at", "dateTime", "Created At", "Timestamp when this coupon record was created"),
        ],
    },
    "coupon_rules": {
        "description": "Coupon campaign rules — discount type, value, targeting, and validity. Each rule defines a campaign.",
        "columns": [
            ("rule_id", "int64", "Rule ID", "Unique identifier for each coupon campaign rule"),
            ("rule_name", "string", "Rule Name", "Display name of the campaign or promotion"),
            ("description", "string", "Description", "Business description of the campaign"),
            ("discount_type", "string", "Discount Type", "Type of discount: percentage, fixed, or bogo"),
            ("discount_value", "double", "Discount Value", "Discount amount. Interpreted as percentage if discount_type=percentage, or dollar amount if fixed."),
            ("min_purchase", "double", "Minimum Purchase", "Minimum purchase amount in USD required to use this coupon"),
            ("valid_days", "int64", "Valid Days", "Number of days from issuance that the coupon is valid"),
            ("is_active", "boolean", "Is Active", "Whether this campaign rule is currently active and can issue new coupons"),
            ("target_tier", "string", "Target Tier", "Restricts the coupon to members of this tier (Bronze/Silver/Gold/Platinum). NULL means all tiers are eligible."),
            ("created_at", "dateTime", "Created At", "Timestamp when this rule was created"),
        ],
    },
    "csr": {
        "description": "Customer Service Representatives — name, email, department, and active status. Each CSR agent who handles member interactions.",
        "columns": [
            ("csr_id", "int64", "CSR ID", "Unique identifier for each customer service representative"),
            ("csr_name", "string", "CSR Name", "Full name of the CSR agent"),
            ("csr_email", "string", "CSR Email", "Email address of the CSR agent"),
            ("department", "string", "Department", "CSR department (e.g., Customer Service, Loyalty Support, Fraud Prevention)"),
            ("is_active", "boolean", "Is Active", "Whether this CSR is currently active (TRUE) or inactive (FALSE)"),
            ("created_at", "dateTime", "Created At", "Timestamp when this CSR record was created"),
        ],
    },
    "csr_activities": {
        "description": "CSR interaction log — activity type, member context, and details. Every time a CSR agent interacts with a member's account.",
        "columns": [
            ("activity_id", "int64", "Activity ID", "Unique identifier for each CSR activity"),
            ("csr_id", "int64", "CSR ID", "Links to csr table. The CSR who performed this activity."),
            ("member_id", "int64", "Member ID", "Links to loyalty_members. The member whose account was affected."),
            ("activity_type", "string", "Activity Type", "Type of activity: enrollment, status_change, coupon_adjust, or tier_override"),
            ("activity_date", "dateTime", "Activity Date", "Date when the CSR activity occurred"),
            ("details", "string", "Details", "JSON or text description of what was done in this interaction"),
            ("created_at", "dateTime", "Created At", "Timestamp when this activity record was created"),
        ],
    },
}

# ─── Relationships between tables ────────────────────────────────────────
# (from_table, from_column, to_table, to_column, is_active)
# "to" side is the "one" side (lookup); "from" side is the "many" side (fact).
# is_active defaults to True. Set to False to create an inactive relationship.
RELATIONSHIPS = [
    ("transactions", "member_id", "loyalty_members", "member_id", True),
    ("transactions", "store_id", "stores", "store_id", True),
    ("transaction_items", "transaction_id", "transactions", "transaction_id", True),
    ("transaction_items", "sku", "sku_reference", "sku", True),
    ("member_points", "member_id", "loyalty_members", "member_id", True),
    ("coupons", "member_id", "loyalty_members", "member_id", True),
    ("coupons", "coupon_rule_id", "coupon_rules", "rule_id", True),
    # Phase 1: coupon redemption → transaction (INACTIVE to avoid ambiguous path coupons → transactions → loyalty_members)
    # Use USERELATIONSHIP in DAX measures when you need to traverse this path
    ("coupons", "redeemed_transaction_id", "transactions", "transaction_id", False),
    ("csr_activities", "csr_id", "csr", "csr_id", True),
    ("csr_activities", "member_id", "loyalty_members", "member_id", True),
]

# ─── DAX measures ────────────────────────────────────────────────────────
# (table_name, measure_name, dax_expression, format_string, description, display_folder)
# Display folders organize measures for AI Data Agent and Power BI consumers.
DAX_MEASURES = [
    # 📊 Membership measures
    ("loyalty_members", "Total Members", "COUNTROWS(loyalty_members)", "#,##0",
     "Count of all loyalty members", "📊 Membership"),
    ("loyalty_members", "Active Members",
     'CALCULATE(COUNTROWS(loyalty_members), loyalty_members[member_status] = "active")',
     "#,##0", "Count of active members", "📊 Membership"),
    ("loyalty_members", "New Members This Month",
     'CALCULATE(COUNTROWS(loyalty_members), MONTH(loyalty_members[enrollment_date]) = MONTH(TODAY()) && YEAR(loyalty_members[enrollment_date]) = YEAR(TODAY()))',
     "#,##0", "Members enrolled in the current month", "📊 Membership"),
    ("loyalty_members", "Churn Risk Members",
     'CALCULATE(COUNTROWS(loyalty_members), FILTER(loyalty_members, DATEDIFF(CALCULATE(MAX(transactions[transaction_date]), FILTER(transactions, transactions[member_id] = loyalty_members[member_id])), TODAY(), DAY) > 180))',
     "#,##0", "Members with no transactions in 180+ days", "📊 Membership"),
    ("loyalty_members", "Email Opt-In Rate",
     'DIVIDE(CALCULATE(COUNTROWS(loyalty_members), loyalty_members[opt_in_email] = TRUE()), COUNTROWS(loyalty_members), 0)',
     "0.0%", "Percentage of members opted in to email marketing", "📊 Membership"),
    ("loyalty_members", "SMS Opt-In Rate",
     'DIVIDE(CALCULATE(COUNTROWS(loyalty_members), loyalty_members[opt_in_sms] = TRUE()), COUNTROWS(loyalty_members), 0)',
     "0.0%", "Percentage of members opted in to SMS marketing", "📊 Membership"),
    ("loyalty_members", "Avg Lifetime Spend",
     'AVERAGEX(loyalty_members, CALCULATE(SUM(transactions[total]), transactions[transaction_type] = "purchase"))',
     "$#,##0.00", "Average lifetime purchase amount per member", "📊 Membership"),
    
    # 💰 Revenue & Transactions measures
    ("transactions", "Total Revenue", 
     'CALCULATE(SUM(transactions[total]), transactions[transaction_type] = "purchase")',
     "$#,##0.00", "Sum of all purchase transaction totals (excludes returns)", "💰 Revenue & Transactions"),
    ("transactions", "Total Transactions", "COUNTROWS(transactions)", "#,##0",
     "Count of all transactions", "💰 Revenue & Transactions"),
    ("transactions", "Avg Transaction Value", "AVERAGE(transactions[total])", "$#,##0.00",
     "Average transaction total", "💰 Revenue & Transactions"),
    ("transactions", "Purchase Count",
     'CALCULATE(COUNTROWS(transactions), transactions[transaction_type] = "purchase")',
     "#,##0", "Count of purchase transactions", "💰 Revenue & Transactions"),
    ("transactions", "Return Count",
     'CALCULATE(COUNTROWS(transactions), transactions[transaction_type] = "return")',
     "#,##0", "Count of return transactions", "💰 Revenue & Transactions"),
    ("transactions", "Return Rate",
     'DIVIDE([Return Count], [Purchase Count], 0)',
     "0.0%", "Percentage of purchases that were returned", "💰 Revenue & Transactions"),
    ("transactions", "Avg Items Per Transaction",
     'AVERAGE(transactions[item_count])',
     "#,##0.0", "Average number of items per transaction", "💰 Revenue & Transactions"),
    ("transactions", "Unique Members (Transacting)",
     'DISTINCTCOUNT(transactions[member_id])',
     "#,##0", "Count of unique members who made transactions", "💰 Revenue & Transactions"),

    # 🛒 Transaction Items measures
    ("transaction_items", "Total Line Items", "COUNTROWS(transaction_items)", "#,##0",
     "Total number of line items across all transactions", "🛒 Transaction Items"),
    ("transaction_items", "Total Line Items Revenue",
     'CALCULATE(SUM(transaction_items[line_total]), transaction_items[is_return] = FALSE())',
     "$#,##0.00", "Sum of all line item totals (excludes returns)", "🛒 Transaction Items"),
    ("transaction_items", "Avg Line Item Value",
     'AVERAGE(transaction_items[line_total])',
     "$#,##0.00", "Average value per line item", "🛒 Transaction Items"),
    ("transaction_items", "Unique SKUs Sold",
     'DISTINCTCOUNT(transaction_items[sku])',
     "#,##0", "Count of unique SKUs sold", "🛒 Transaction Items"),

    # 🏪 Store Performance measures
    ("stores", "Total Stores", "COUNTROWS(stores)", "#,##0",
     "Count of all store locations", "🏪 Store Performance"),
    ("stores", "Revenue Per Store",
     'DIVIDE([Total Revenue], [Total Stores], 0)',
     "$#,##0.00", "Average revenue per store location", "🏪 Store Performance"),

    # 🎟️ Coupons & Campaigns measures
    ("coupons", "Coupons Issued", "COUNTROWS(coupons)", "#,##0",
     "Total coupons issued", "🎟️ Coupons & Campaigns"),
    ("coupons", "Coupons Redeemed",
     'CALCULATE(COUNTROWS(coupons), coupons[status] = "redeemed")',
     "#,##0", "Count of redeemed coupons", "🎟️ Coupons & Campaigns"),
    ("coupons", "Coupons Expired",
     'CALCULATE(COUNTROWS(coupons), coupons[status] = "expired")',
     "#,##0", "Count of expired coupons", "🎟️ Coupons & Campaigns"),
    ("coupons", "Coupons Voided",
     'CALCULATE(COUNTROWS(coupons), coupons[status] = "voided")',
     "#,##0", "Count of voided coupons", "🎟️ Coupons & Campaigns"),
    ("coupons", "Outstanding Coupons",
     'CALCULATE(COUNTROWS(coupons), coupons[status] = "issued")',
     "#,##0", "Count of active issued coupons not yet redeemed or expired", "🎟️ Coupons & Campaigns"),
    ("coupons", "Coupon Redemption Rate",
     'DIVIDE(CALCULATE(COUNTROWS(coupons), coupons[status] = "redeemed"), COUNTROWS(coupons), 0)',
     "0.0%", "Percentage of issued coupons that were redeemed", "🎟️ Coupons & Campaigns"),
    ("coupon_rules", "Avg Discount Value",
     'AVERAGE(coupon_rules[discount_value])',
     "#,##0.00", "Average discount value across all coupon campaigns", "🎟️ Coupons & Campaigns"),

    # ⭐ Points & Rewards measures
    ("member_points", "Total Current Points Balance",
     'CALCULATE(SUM(member_points[balance_after]), member_points[point_id] = CALCULATE(MAX(member_points[point_id]), ALLEXCEPT(member_points, member_points[member_id])))',
     "#,##0", "Sum of all members' current points balances (latest balance per member)", "⭐ Points & Rewards"),
    ("member_points", "Avg Points Balance",
     'AVERAGEX(VALUES(member_points[member_id]), CALCULATE(MAX(member_points[balance_after])))',
     "#,##0", "Average points balance per member (latest balance)", "⭐ Points & Rewards"),
    ("member_points", "Points Liability ($)",
     '[Total Current Points Balance] * 0.01',
     "$#,##0.00", "Dollar value of outstanding points liability (points * $0.01)", "⭐ Points & Rewards"),
    ("member_points", "Points Earned",
     'CALCULATE(SUM(member_points[points_amount]), member_points[activity_type] = "earn")',
     "#,##0", "Total points earned across all members", "⭐ Points & Rewards"),
    ("member_points", "Points Redeemed",
     'ABS(CALCULATE(SUM(member_points[points_amount]), member_points[activity_type] = "redeem"))',
     "#,##0", "Total points redeemed (spent) across all members", "⭐ Points & Rewards"),

    # 🛡️ Service & Audit measures
    ("csr_activities", "Total CSR Interactions", "COUNTROWS(csr_activities)", "#,##0",
     "Count of all CSR activities", "🛡️ Service & Audit"),
    ("csr", "Active CSR Agents",
     'CALCULATE(COUNTROWS(csr), csr[is_active] = TRUE())',
     "#,##0", "Count of active CSR agents", "🛡️ Service & Audit"),
    ("csr_activities", "Avg Activities Per CSR",
     'DIVIDE([Total CSR Interactions], [Active CSR Agents], 0)',
     "#,##0.0", "Average number of activities per active CSR agent", "🛡️ Service & Audit"),
    ("csr_activities", "CSR Activities This Month",
     'CALCULATE(COUNTROWS(csr_activities), MONTH(csr_activities[activity_date]) = MONTH(TODAY()) && YEAR(csr_activities[activity_date]) = YEAR(TODAY()))',
     "#,##0", "Count of CSR activities in the current month", "🛡️ Service & Audit"),

    # 📦 Product Performance measures
    ("sku_reference", "Unique Products in Catalog",
     'DISTINCTCOUNT(sku_reference[sku])',
     "#,##0", "Count of unique product SKUs in the catalog", "📦 Product Performance"),
    ("sku_reference", "Avg Product Price",
     'AVERAGE(sku_reference[unit_price])',
     "$#,##0.00", "Average unit price across all products", "📦 Product Performance"),
    ("sku_reference", "Bonus Eligible Products",
     'CALCULATE(COUNTROWS(sku_reference), sku_reference[is_bonus_eligible] = TRUE())',
     "#,##0", "Count of products that earn bonus loyalty points", "📦 Product Performance"),
]


def read_env_file(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r'^\s*([A-Z_]+)\s*=\s*([^#]+?)(?:\s*#.*)?$', line)
            if m:
                env[m.group(1)] = m.group(2).strip()
    return env


def get_credential(auth_method: str, tenant_id: str = ""):
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


def build_tmdl_definition(sql_endpoint: str, database_name: str) -> dict:
    """
    Build TMDL definition for Fabric REST API semanticModels/create.

    Sources data directly from Lakehouse Delta tables (dbo schema) —
    no SQL views needed. The semantic model provides the abstraction
    layer via relationships, measures, and descriptions.
    """
    parts = []

    # definition.pbism — required Fabric semantic model metadata
    pbism_content = json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "5.0",
        "settings": {},
    })
    parts.append({
        "path": "definition.pbism",
        "payload": base64.b64encode(pbism_content.encode()).decode(),
        "payloadType": "InlineBase64",
    })

    # definition/database.tmdl — database-level properties
    db_tmdl_lines = [
        f"database '{database_name}'",
        "\tcompatibilityLevel: 1604",
        "",
    ]
    parts.append({
        "path": "definition/database.tmdl",
        "payload": base64.b64encode("\n".join(db_tmdl_lines).encode()).decode(),
        "payloadType": "InlineBase64",
    })

    # definition/model.tmdl — root model definition
    model_tmdl_lines = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "",
    ]
    parts.append({
        "path": "definition/model.tmdl",
        "payload": base64.b64encode("\n".join(model_tmdl_lines).encode()).decode(),
        "payloadType": "InlineBase64",
    })

    # definition/expressions.tmdl — shared DatabaseQuery expression for DirectLake
    # All table partitions reference this expression to discover Lakehouse tables.
    # DirectLake reads Delta files directly from OneLake — no SQL credentials needed.
    expr_lines = [
        "expression DatabaseQuery =",
        "\t\tlet",
        f'\t\t\tdatabase = Sql.Database("{sql_endpoint}", "{database_name}")',
        "\t\tin",
        "\t\t\tdatabase",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    parts.append({
        "path": "definition/expressions.tmdl",
        "payload": base64.b64encode("\n".join(expr_lines).encode()).decode(),
        "payloadType": "InlineBase64",
    })

    # One .tmdl file per table
    for table_name, table_def in LAKEHOUSE_TABLES.items():
        lines = [
            f'table {table_name}',
            '',
        ]

        # Columns — now with descriptions (4th tuple element)
        # Note: TMDL column-level descriptions are not supported (causes parse errors).
        # Descriptions are added as annotations instead for AI Data Agent compatibility.
        for col_tuple in table_def["columns"]:
            col_name = col_tuple[0]
            col_type = col_tuple[1]
            col_label = col_tuple[2]
            col_desc = col_tuple[3] if len(col_tuple) > 3 else ""
            
            lines.append(f'\tcolumn {col_name}')
            lines.append(f'\t\tdataType: {col_type}')
            lines.append(f'\t\tsourceColumn: {col_name}')
            lines.append(f'\t\tsummarizeBy: none')
            # Add description as annotation if present (TMDL doesn't support native description on columns)
            if col_desc:
                lines.append(f'\t\tannotation Description = "{col_desc}"')
            lines.append('')

        # DAX measures for this table — now with display folders (6th tuple element)
        table_measures = [m for m in DAX_MEASURES if m[0] == table_name]
        for measure_tuple in table_measures:
            _, measure_name, dax_expr, fmt, desc, display_folder = measure_tuple[:6]
            lines.append(f'\tmeasure \'{measure_name}\' = {dax_expr}')
            lines.append(f'\t\tformatString: {fmt}')
            # Display folder helps organize measures for AI and Power BI users
            if display_folder:
                lines.append(f'\t\tdisplayFolder: "{display_folder}"')
            lines.append('')

        # Partition — DirectLake entity reference (reads Delta files directly from OneLake)
        lines.append(f'\tpartition {table_name} = entity')
        lines.append(f'\t\tmode: directLake')
        lines.append(f'\t\tentityName: {table_name}')
        lines.append(f'\t\tschemaName: dbo')
        lines.append(f'\t\texpressionSource: DatabaseQuery')
        lines.append('')

        tmdl_content = "\n".join(lines)
        parts.append({
            "path": f"definition/tables/{table_name}.tmdl",
            "payload": base64.b64encode(tmdl_content.encode()).decode(),
            "payloadType": "InlineBase64",
        })

    # relationships.tmdl — all relationships in one file
    if RELATIONSHIPS:
        rel_lines = []
        for rel_tuple in RELATIONSHIPS:
            from_tbl = rel_tuple[0]
            from_col = rel_tuple[1]
            to_tbl = rel_tuple[2]
            to_col = rel_tuple[3]
            is_active = rel_tuple[4] if len(rel_tuple) > 4 else True
            
            rel_name = f"rel_{from_tbl}_{from_col}_{to_col}"
            rel_lines.append(f"relationship {rel_name}")
            rel_lines.append(f"\tfromColumn: {from_tbl}.{from_col}")
            rel_lines.append(f"\ttoColumn: {to_tbl}.{to_col}")
            if not is_active:
                rel_lines.append(f"\tisActive: false")
            rel_lines.append("")

        parts.append({
            "path": "definition/relationships.tmdl",
            "payload": base64.b64encode("\n".join(rel_lines).encode()).decode(),
            "payloadType": "InlineBase64",
        })

    return {"parts": parts}


def _post_deploy_bind_and_refresh(credential, workspace_id: str, model_name: str):
    """Post-deploy: take over dataset, bind OAuth2 credentials, and trigger refresh."""
    print("   ── Post-deploy: binding credentials & refreshing ──")
    print()
    try:
        from bind_model_credentials import bind_and_refresh
        # Wait a moment for Fabric to finalize the model
        time.sleep(5)
        bind_and_refresh(credential, workspace_id, model_name, skip_refresh=False)
    except ImportError:
        # Inline fallback if bind_model_credentials is not importable
        print("   (bind_model_credentials module not found — using inline fallback)")
        _inline_bind_and_refresh(credential, workspace_id, model_name)
    except Exception as e:
        print(f"   ⚠️  Post-deploy bind/refresh failed: {e}")
        print("   Run separately: python scripts/bind-model-credentials.py")


def _inline_bind_and_refresh(credential, workspace_id: str, model_name: str):
    """Inline fallback for takeover + refresh when bind_model_credentials can't be imported."""
    pbi_api = "https://api.powerbi.com/v1.0/myorg"
    fabric_token = credential.get_token(FABRIC_SCOPE).token
    pbi_token = credential.get_token(PBI_SCOPE).token

    fabric_headers = {"Authorization": f"Bearer {fabric_token}", "Content-Type": "application/json"}
    pbi_headers = {"Authorization": f"Bearer {pbi_token}", "Content-Type": "application/json"}

    # Find model ID
    r = requests.get(f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels", headers=fabric_headers)
    dataset_id = None
    if r.status_code == 200:
        for sm in r.json().get("value", []):
            if sm["displayName"] == model_name:
                dataset_id = sm["id"]
                break
    if not dataset_id:
        print("   ⚠️  Could not find model for post-deploy bind. Run bind-model-credentials.py manually.")
        return

    # Take over
    r = requests.post(f"{pbi_api}/datasets/{dataset_id}/Default.TakeOver", headers=pbi_headers)
    if r.status_code in (200, 204, 409):
        print(f"   ✅ Dataset takeover succeeded.")
    else:
        print(f"   ⚠️  Takeover returned {r.status_code}: {r.text[:300]}")

    time.sleep(3)

    # Get datasources and update credentials
    r = requests.get(f"{pbi_api}/datasets/{dataset_id}/datasources", headers=pbi_headers)
    if r.status_code == 200:
        import json as _json
        for ds in r.json().get("value", []):
            gw_id = ds.get("gatewayId")
            ds_id = ds.get("datasourceId")
            if gw_id and ds_id:
                body = {
                    "credentialDetails": {
                        "credentialType": "OAuth2",
                        "credentials": _json.dumps({"credentialData": ""}),
                        "encryptedConnection": "Encrypted",
                        "encryptionAlgorithm": "None",
                        "privacyLevel": "Organizational",
                    }
                }
                requests.patch(f"{pbi_api}/gateways/{gw_id}/datasources/{ds_id}", headers=pbi_headers, json=body)

    # Trigger refresh
    r = requests.post(f"{pbi_api}/datasets/{dataset_id}/refreshes", headers=pbi_headers, json={"notifyOption": "NoNotification"})
    if r.status_code in (200, 202):
        print(f"   ✅ Refresh triggered. Check Fabric portal for status.")
    else:
        print(f"   ⚠️  Refresh returned {r.status_code}. Refresh manually in the portal.")


def main():
    parser = argparse.ArgumentParser(
        description="Create Fabric Semantic Model from Lakehouse Delta tables"
    )
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser")
    parser.add_argument("--name", default=DEFAULT_MODEL_NAME, help="Semantic model display name")
    parser.add_argument("--dry-run", action="store_true", help="Preview without calling API")
    parser.add_argument("--force", action="store_true", help="Delete existing model and recreate")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   AAP Data Agent POC — Create Semantic Model           ║")
    print("║   Sources: 10 Lakehouse Delta tables (no SQL views)    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    env = read_env_file(ENV_FILE)
    workspace_id = env.get("FABRIC_WORKSPACE_ID", "")
    sql_endpoint = env.get("FABRIC_SQL_ENDPOINT", "")
    database_name = env.get("FABRIC_LAKEHOUSE_NAME", "RewardsLoyaltyData")

    if not workspace_id or not sql_endpoint:
        print("❌ Missing FABRIC_WORKSPACE_ID or FABRIC_SQL_ENDPOINT in .env.fabric")
        sys.exit(1)

    print(f"   Workspace:    {workspace_id}")
    print(f"   SQL Endpoint: {sql_endpoint}")
    print(f"   Database:     {database_name}")
    print(f"   Model Name:   {args.name}")
    print(f"   Tables:       {len(LAKEHOUSE_TABLES)} Delta tables")
    print(f"   Relationships:{len(RELATIONSHIPS)}")
    print(f"   DAX Measures: {len(DAX_MEASURES)}")
    print()

    # Build TMDL definition
    definition = build_tmdl_definition(sql_endpoint, database_name)

    if args.dry_run:
        print("🔍 DRY RUN — would create semantic model with:")
        print()
        print("   Tables:")
        for tbl_name, tbl_def in LAKEHOUSE_TABLES.items():
            n_cols = len(tbl_def["columns"])
            n_measures = len([m for m in DAX_MEASURES if m[0] == tbl_name])
            extra = f" + {n_measures} measures" if n_measures else ""
            print(f"      • {tbl_name} ({n_cols} columns{extra})")
        print()
        print("   Relationships:")
        for rel_tuple in RELATIONSHIPS:
            from_tbl, from_col, to_tbl, to_col = rel_tuple[0], rel_tuple[1], rel_tuple[2], rel_tuple[3]
            is_active = rel_tuple[4] if len(rel_tuple) > 4 else True
            status = "" if is_active else " (inactive)"
            print(f"      • {from_tbl}.{from_col} → {to_tbl}.{to_col}{status}")
        print()
        print(f"   Definition parts: {len(definition['parts'])}")
        for part in definition["parts"]:
            payload_size = len(base64.b64decode(part["payload"]))
            print(f"      {part['path']} ({payload_size} bytes)")
        print()

        # Save definition for inspection
        debug_path = SCRIPT_DIR / "semantic-model-definition.json"
        debug_path.write_text(json.dumps(definition, indent=2))
        print(f"   📄 Definition saved to: {debug_path}")
        return

    # Authenticate
    tenant_id = env.get("ENTRA_TENANT_ID", "")
    credential = get_credential(args.auth, tenant_id=tenant_id)
    token = credential.get_token(FABRIC_SCOPE).token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Check if model already exists
    print("   Checking for existing semantic model...")
    r = requests.get(
        f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels",
        headers=headers,
    )
    existing_id = None
    if r.status_code == 200:
        for sm in r.json().get("value", []):
            if sm["displayName"] == args.name:
                existing_id = sm["id"]
                break

    if existing_id:
        if args.force:
            print(f"   🗑️  Deleting existing model '{args.name}' (ID: {existing_id})...")
            dr = requests.delete(
                f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels/{existing_id}",
                headers=headers,
            )
            if dr.status_code in (200, 204):
                print(f"   ✅ Deleted. Waiting 5s before recreating...")
                time.sleep(5)
            else:
                print(f"   ❌ Delete failed ({dr.status_code}): {dr.text[:300]}")
                sys.exit(1)
        else:
            print(f"   ⚠️  '{args.name}' already exists (ID: {existing_id})")
            print(f"   Use --force to delete and recreate.")
            return
    else:
        print(f"   No existing model named '{args.name}' — proceeding.")
    print()

    # Create the semantic model
    print(f"   Creating semantic model '{args.name}'...")
    body = {
        "displayName": args.name,
        "description": (
            "AAP Rewards & Loyalty Program semantic model. "
            "10 tables from Lakehouse Delta tables with relationships and DAX measures. "
            "Covers: members, transactions, stores, products, coupons, coupon rules, "
            "points ledger, CSRs, CSR activities, and audit log."
        ),
        "definition": definition,
    }

    r = requests.post(
        f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels",
        headers=headers,
        json=body,
    )

    if r.status_code in (200, 201):
        result = r.json()
        model_id = result.get("id", "unknown")
        print(f"   ✅ Semantic model created!")
        print(f"      ID:   {model_id}")
        print(f"      Name: {args.name}")
        print()

        # Post-deploy: bind credentials and trigger refresh
        _post_deploy_bind_and_refresh(credential, workspace_id, args.name)

        print(f"   Portal: https://app.fabric.microsoft.com/groups/{workspace_id}")

    elif r.status_code == 202:
        operation_id = r.headers.get("x-ms-operation-id", "")
        location = r.headers.get("Location", "")
        retry_after = int(r.headers.get("Retry-After", "5"))
        print(f"   ⏳ Creation in progress (operation: {operation_id})...")

        for attempt in range(30):
            time.sleep(max(retry_after, 3))
            if location:
                poll_r = requests.get(location, headers=headers)
            elif operation_id:
                poll_r = requests.get(
                    f"{FABRIC_API}/operations/{operation_id}",
                    headers=headers,
                )
            else:
                print("   ⚠️  No operation ID or location header — cannot poll.")
                break

            if poll_r.status_code == 200:
                poll_data = poll_r.json()
                status = poll_data.get("status", "")
                if status.lower() == "succeeded":
                    print(f"   ✅ Semantic model created successfully!")
                    print()
                    # Post-deploy: bind credentials and trigger refresh
                    _post_deploy_bind_and_refresh(credential, workspace_id, args.name)
                    print(f"      Check workspace: https://app.fabric.microsoft.com/groups/{workspace_id}")
                    break
                elif status.lower() == "failed":
                    error = poll_data.get("error", {})
                    print(f"   ❌ Creation failed: {json.dumps(error, indent=2)}")
                    break
                else:
                    print(f"      Status: {status}... ({attempt + 1}/30)")
        else:
            print("   ⚠️  Timed out. Check Fabric portal.")

    elif r.status_code == 409:
        print(f"   ⚠️  Conflict (409) — model may already exist.")
        print(f"      Response: {r.text[:500]}")

    else:
        print(f"   ❌ Failed to create semantic model.")
        print(f"      Status: {r.status_code}")
        print(f"      Response: {r.text[:1000]}")
        print()
        print("   Saving definition for manual import...")
        debug_path = SCRIPT_DIR / "semantic-model-definition.json"
        debug_path.write_text(json.dumps(
            {"displayName": args.name, "definition": definition}, indent=2
        ))
        print(f"   📄 Saved to: {debug_path}")
        print("   Use Tabular Editor or Fabric portal to create the model manually.")


if __name__ == "__main__":
    main()
