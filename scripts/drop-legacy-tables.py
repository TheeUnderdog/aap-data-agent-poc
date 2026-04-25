#!/usr/bin/env python3
"""
Drop stale legacy tables from the Fabric Lakehouse.

After the CSR rename (agents → csr, agent_activities → csr_activities), the old
Delta tables were left behind. This script removes them using the Fabric REST API
(Lakehouse Tables endpoint). The SQL Analytics Endpoint does not support DROP TABLE.

Tables dropped:
  - agents
  - agent_activities

Usage:
    python scripts/drop-legacy-tables.py
    python scripts/drop-legacy-tables.py --auth device-code
    python scripts/drop-legacy-tables.py --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

import requests

# Ensure UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"
FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
ONELAKE_DFS = "https://onelake.dfs.fabric.microsoft.com"
STORAGE_SCOPE = "https://storage.azure.com/.default"

TABLES_TO_DROP = ["agents", "agent_activities"]


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
        print("ERROR: azure-identity not found. Install: pip install azure-identity")
        sys.exit(1)

    if auth_method == "device-code":
        print("  Auth: Device code flow -- check terminal for instructions...")
        return DeviceCodeCredential()
    else:
        print("  Auth: Browser flow -- a login window will open...")
        return InteractiveBrowserCredential()


def list_lakehouse_tables(workspace_id: str, lakehouse_id: str, headers: dict) -> list:
    """List all tables in the Lakehouse via Fabric REST API."""
    url = f"{FABRIC_API}/workspaces/{workspace_id}/lakehouses/{lakehouse_id}/tables"
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"  ERROR listing tables ({r.status_code}): {r.text[:300]}")
        return []
    return r.json().get("data", [])


def delete_table_via_onelake(workspace_id: str, lakehouse_id: str, table_name: str, dfs_headers: dict) -> bool:
    """Delete a Delta table by removing its folder from OneLake via ADLS Gen2 DFS API."""
    # OneLake DFS path: /{workspaceId}/{lakehouseId}/Tables/{tableName}?recursive=true
    url = f"{ONELAKE_DFS}/{workspace_id}/{lakehouse_id}/Tables/{table_name}?recursive=true"
    r = requests.delete(url, headers=dfs_headers)
    if r.status_code in (200, 202):
        return True
    elif r.status_code == 404:
        print(f"NOT FOUND (already gone)", end=" ")
        return True
    else:
        print(f"FAILED ({r.status_code}): {r.text[:300]}", end=" ")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Drop stale legacy tables (agents, agent_activities) from Fabric Lakehouse"
    )
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()

    print("=" * 60)
    print("  AAP Data Agent POC -- Drop Legacy Tables")
    print("=" * 60)

    env = read_env_file(ENV_FILE)
    workspace_id = env.get("FABRIC_WORKSPACE_ID", "")
    lakehouse_id = env.get("FABRIC_LAKEHOUSE_ID", "")

    if not workspace_id or not lakehouse_id:
        print("  ERROR: Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID in .env.fabric")
        sys.exit(1)

    print(f"  Workspace:  {workspace_id}")
    print(f"  Lakehouse:  {lakehouse_id}")
    print(f"  Tables:     {', '.join(TABLES_TO_DROP)}")
    print()

    if args.dry_run:
        print("  DRY RUN -- no changes will be made.")
        print()

    credential = get_credential(args.auth)

    # Two tokens: Fabric API for listing tables, Storage for OneLake DFS deletion
    fabric_token = credential.get_token(FABRIC_SCOPE).token
    storage_token = credential.get_token(STORAGE_SCOPE).token

    fabric_headers = {
        "Authorization": f"Bearer {fabric_token}",
        "Content-Type": "application/json",
    }
    dfs_headers = {
        "Authorization": f"Bearer {storage_token}",
    }
    print("  Tokens acquired (Fabric API + OneLake Storage).")
    print()

    # List existing tables to confirm targets exist
    print("  Checking existing tables...")
    tables = list_lakehouse_tables(workspace_id, lakehouse_id, fabric_headers)
    table_names = [t.get("name", "") for t in tables]
    print(f"  Found {len(tables)} table(s): {', '.join(sorted(table_names))}")
    print()

    dropped = 0
    for table in TABLES_TO_DROP:
        if table not in table_names:
            print(f"  {table}: NOT FOUND (already removed or never existed)")
            dropped += 1
            continue

        if args.dry_run:
            print(f"  [DRY-RUN] Would delete: {table}")
            dropped += 1
            continue

        print(f"  Deleting {table}...", end=" ", flush=True)
        if delete_table_via_onelake(workspace_id, lakehouse_id, table, dfs_headers):
            print("DONE")
            dropped += 1

    print()
    if dropped == len(TABLES_TO_DROP):
        print(f"  SUCCESS: All {dropped} legacy tables handled.")
    else:
        print(f"  PARTIAL: {dropped}/{len(TABLES_TO_DROP)} tables handled. Check errors above.")

    print(f"  Portal: https://app.fabric.microsoft.com/groups/{workspace_id}")


if __name__ == "__main__":
    main()
