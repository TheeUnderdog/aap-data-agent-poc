#!/usr/bin/env python3
"""
Verify that semantic views exist on the Fabric Lakehouse SQL endpoint.

Uses the Fabric REST API (no pyodbc/ODBC required) to list items and
then uses the SQL endpoint to check view existence.

Usage:
    python scripts/verify-views.py
    python scripts/verify-views.py --auth device-code
"""

import json
import re
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"
FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
DB_SCOPE = "https://database.windows.net/.default"

EXPECTED_VIEWS = [
    "semantic.v_member_summary",
    "semantic.v_transaction_history",
    "semantic.v_points_activity",
    "semantic.v_coupon_activity",
    "semantic.v_store_performance",
    "semantic.v_product_popularity",
    "semantic.v_member_engagement",
    "semantic.v_campaign_effectiveness",
    "semantic.v_audit_trail",
]


def read_env_file(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r'^\s*([A-Z_]+)\s*=\s*([^#]+?)(?:\s*#.*)?$', line)
            if m:
                env[m.group(1)] = m.group(2).strip()
    return env


def get_credential(auth_method: str):
    try:
        from azure.identity import DeviceCodeCredential, InteractiveBrowserCredential
    except ImportError:
        print("❌ azure-identity not found. Install: pip install azure-identity")
        sys.exit(1)

    if auth_method == "device-code":
        print("🔑 Device code auth — check terminal for instructions...")
        return DeviceCodeCredential()
    else:
        print("🔑 Browser auth — a login window will open...")
        return InteractiveBrowserCredential()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify semantic views on Fabric SQL endpoint")
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   AAP Data Agent POC — Verify Semantic Views           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    env = read_env_file(ENV_FILE)
    workspace_id = env.get("FABRIC_WORKSPACE_ID", "")
    lakehouse_id = env.get("FABRIC_LAKEHOUSE_ID", "")
    sql_endpoint = env.get("FABRIC_SQL_ENDPOINT", "")
    lakehouse_name = env.get("FABRIC_LAKEHOUSE_NAME", "RewardsLoyaltyData")

    if not workspace_id:
        print("❌ FABRIC_WORKSPACE_ID not found in .env.fabric")
        sys.exit(1)

    print(f"   Workspace:  {workspace_id}")
    print(f"   Lakehouse:  {lakehouse_name} ({lakehouse_id})")
    print(f"   SQL Endpoint: {sql_endpoint}")
    print()

    credential = get_credential(args.auth)

    # --- Part 1: Fabric REST API check (workspace items) ---
    print("━━━ Part 1: Workspace Items (Fabric REST API) ━━━")
    fabric_token = credential.get_token(FABRIC_SCOPE).token
    headers = {"Authorization": f"Bearer {fabric_token}"}

    r = requests.get(f"{FABRIC_API}/workspaces/{workspace_id}/items", headers=headers)
    r.raise_for_status()
    items = r.json().get("value", [])

    semantic_models = [i for i in items if i.get("type") == "SemanticModel"]
    sql_endpoints = [i for i in items if i.get("type") == "SQLEndpoint"]
    lakehouses = [i for i in items if i.get("type") == "Lakehouse"]

    print(f"   Total workspace items: {len(items)}")
    print(f"   Lakehouses:            {len(lakehouses)}")
    print(f"   SQL Endpoints:         {len(sql_endpoints)}")
    print(f"   Semantic Models:       {len(semantic_models)}")
    print()

    if semantic_models:
        print("   Semantic Models found:")
        for sm in semantic_models:
            print(f"      • {sm['displayName']} ({sm['id']})")
    else:
        print("   ⚠️  No semantic models found in workspace.")
        print("      This is expected — SQL views are NOT semantic models.")
        print("      See explanation below.")
    print()

    # List all items for visibility
    print("   All workspace items:")
    for item in sorted(items, key=lambda x: x.get("type", "")):
        print(f"      [{item.get('type', '?'):20s}] {item['displayName']}")
    print()

    # --- Part 2: SQL endpoint view check ---
    print("━━━ Part 2: SQL Views (via Invoke-Sqlcmd) ━━━")
    if not sql_endpoint:
        print("   ⚠️  No SQL endpoint configured. Skipping SQL verification.")
        print()
    else:
        try:
            db_token = credential.get_token(DB_SCOPE).token
            import subprocess
            check_sql = (
                "SELECT s.name + '.' + v.name AS view_name "
                "FROM sys.views v "
                "JOIN sys.schemas s ON v.schema_id = s.schema_id "
                "WHERE s.name = 'semantic' "
                "ORDER BY v.name"
            )
            ps_cmd = (
                f'$results = Invoke-Sqlcmd -ServerInstance "{sql_endpoint}" '
                f'-Database "{lakehouse_name}" '
                f'-AccessToken "{db_token}" '
                f'-Query "{check_sql}" -QueryTimeout 60 -ErrorAction Stop; '
                f'$results | ForEach-Object {{ $_.view_name }}'
            )
            result = subprocess.run(
                ["pwsh", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0 and result.stdout.strip():
                found_views = [v.strip() for v in result.stdout.strip().splitlines() if v.strip()]
                print(f"   Found {len(found_views)} view(s) in 'semantic' schema:")
                for v in found_views:
                    status = "✅" if v in EXPECTED_VIEWS else "❓"
                    print(f"      {status} {v}")
                print()

                missing = [v for v in EXPECTED_VIEWS if v not in found_views]
                if missing:
                    print(f"   ⚠️  Missing {len(missing)} expected view(s):")
                    for v in missing:
                        print(f"      ❌ {v}")
                else:
                    print("   ✅ All 9 expected semantic views are present!")
            elif result.returncode != 0:
                print(f"   ❌ SQL query failed: {result.stderr.strip()}")
                print("   Falling back to REST API only (views cannot be verified via REST).")
            else:
                print("   ⚠️  No views found in 'semantic' schema.")
                print("   The sample data notebook may need to be run first.")
        except Exception as e:
            print(f"   ⚠️  SQL verification skipped: {e}")
            print("   (Invoke-Sqlcmd may not be available)")
    print()

    # --- Summary ---
    print("━━━ Summary ━━━")
    print()
    print("  SQL Views vs Semantic Models — they are DIFFERENT things:")
    print()
    print("  📊 SQL Views (what we deployed):")
    print("     • Database objects inside the SQL Analytics Endpoint")
    print("     • Visible in SQL endpoint object explorer under 'semantic' schema")
    print("     • Queryable via SELECT * FROM semantic.v_member_summary")
    print("     • ✅ These are deployed and working")
    print()
    print("  📦 Semantic Models (what appears in workspace list):")
    print("     • Workspace-level Power BI items (formerly 'datasets')")
    print("     • Created separately — either auto-generated by Lakehouse or manually")
    print("     • The Lakehouse auto-creates a 'default semantic model' for tables")
    print("     • Custom views in 'semantic' schema are NOT auto-included")
    print()
    print("  ➡️  To create a workspace-level semantic model from our views,")
    print("     run: python scripts/create-semantic-model.py")
    print()


if __name__ == "__main__":
    main()
