#!/usr/bin/env python3
"""
Provision Lakehouse in an existing Fabric workspace using browser-based auth.

Uses InteractiveBrowserCredential (opens browser) instead of Azure CLI tokens,
which resolves visibility issues with portal-created workspaces in Microsoft
corporate tenants.

Usage:
    python scripts/provision-lakehouse.py
    python scripts/provision-lakehouse.py --workspace-id e7f4acfe-90d7-4685-864a-b5f1216fe614
    python scripts/provision-lakehouse.py --workspace-name "AAP-RewardsLoyalty-POC"
    python scripts/provision-lakehouse.py --auth device-code
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"

# Defaults matching setup-workspace.ps1
DEFAULT_WORKSPACE_NAME = "AAP-RewardsLoyalty-POC"
DEFAULT_LAKEHOUSE_NAME = "RewardsLoyaltyData"


def get_credential(auth_method: str):
    try:
        from azure.identity import (
            DeviceCodeCredential,
            InteractiveBrowserCredential,
        )
    except ImportError:
        print("❌ azure-identity not found. Install: pip install azure-identity")
        sys.exit(1)

    if auth_method == "device-code":
        print("🔑 Device code auth — check terminal for instructions...")
        return DeviceCodeCredential()
    else:
        print("🔑 Browser auth — a login window will open...")
        return InteractiveBrowserCredential()


def get_token(credential) -> str:
    token = credential.get_token(FABRIC_SCOPE)
    return token.token


def fabric_get(token: str, path: str) -> dict:
    r = requests.get(
        f"{FABRIC_API}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


def fabric_post(token: str, path: str, body: dict) -> requests.Response:
    r = requests.post(
        f"{FABRIC_API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    return r


def find_workspace(token: str, name: str = None, ws_id: str = None) -> dict:
    """Find workspace by ID or name."""
    if ws_id:
        print(f"📂 Looking up workspace {ws_id}...")
        try:
            ws = fabric_get(token, f"/workspaces/{ws_id}")
            print(f"   ✅ Found: {ws['displayName']} ({ws['id']})")
            return ws
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print(f"   ❌ Workspace {ws_id} not found via direct lookup.")
            else:
                raise

    # Fall back to listing all workspaces
    print(f"📂 Searching for workspace '{name or DEFAULT_WORKSPACE_NAME}'...")
    target = name or DEFAULT_WORKSPACE_NAME
    data = fabric_get(token, "/workspaces")
    for ws in data.get("value", []):
        if ws["displayName"] == target and ws.get("type") != "Personal":
            print(f"   ✅ Found: {ws['displayName']} ({ws['id']})")
            return ws

    # Show what we can see
    print(f"\n   ❌ Workspace '{target}' not found. Visible workspaces:")
    for ws in data.get("value", []):
        print(f"      • {ws['displayName']} ({ws['id']}) [{ws.get('type', '?')}]")
    return None


def find_or_create_lakehouse(token: str, workspace_id: str, name: str) -> dict:
    """Find existing lakehouse or create a new one."""
    print(f"🏠 Checking for lakehouse '{name}'...")
    try:
        data = fabric_get(token, f"/workspaces/{workspace_id}/lakehouses")
        for lh in data.get("value", []):
            if lh["displayName"] == name:
                print(f"   ✅ Already exists: {lh['id']}")
                return lh
    except requests.HTTPError:
        pass

    print(f"   Creating lakehouse '{name}'...")
    r = fabric_post(token, f"/workspaces/{workspace_id}/lakehouses", {"displayName": name})
    if r.status_code == 201:
        lh = r.json()
        print(f"   ✅ Created: {lh['id']}")
        return lh
    elif r.status_code == 409:
        print("   ⚠️ 409 conflict — already exists. Fetching...")
        data = fabric_get(token, f"/workspaces/{workspace_id}/lakehouses")
        for lh in data.get("value", []):
            if lh["displayName"] == name:
                return lh
    else:
        print(f"   ❌ Failed ({r.status_code}): {r.text}")
        sys.exit(1)


def get_sql_endpoint(token: str, workspace_id: str, lakehouse_id: str, max_wait: int = 120) -> str:
    """Poll for SQL endpoint (may take 1-3 min after lakehouse creation)."""
    print("🔌 Retrieving SQL endpoint...")
    start = time.time()
    while time.time() - start < max_wait:
        try:
            data = fabric_get(token, f"/workspaces/{workspace_id}/lakehouses/{lakehouse_id}")
            props = data.get("properties", {})
            sql_ep = props.get("sqlEndpointProperties", {})
            conn_str = sql_ep.get("connectionString", "")
            status = sql_ep.get("provisioningStatus", "")

            if conn_str and status != "InProgress":
                print(f"   ✅ {conn_str}")
                return conn_str
            else:
                elapsed = int(time.time() - start)
                print(f"   ⏳ SQL endpoint provisioning... ({elapsed}s)")
                time.sleep(10)
        except requests.HTTPError:
            time.sleep(10)

    print(f"   ⚠️ SQL endpoint not ready after {max_wait}s. You can re-run later.")
    return "<pending>"


def write_env_file(workspace: dict, lakehouse: dict, sql_endpoint: str, capacity_id: str):
    """Write .env.fabric config file."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""# Generated by provision-lakehouse.py on {ts}
# Do not commit this file to source control.
FABRIC_WORKSPACE_ID={workspace['id']}
FABRIC_WORKSPACE_NAME={workspace['displayName']}
FABRIC_LAKEHOUSE_ID={lakehouse['id']}
FABRIC_LAKEHOUSE_NAME={lakehouse['displayName']}
FABRIC_SQL_ENDPOINT={sql_endpoint}
FABRIC_CAPACITY_ID={capacity_id}
"""
    ENV_FILE.write_text(content)
    print(f"💾 Config saved to {ENV_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Provision Lakehouse in Fabric workspace")
    parser.add_argument("--workspace-id", help="Workspace GUID (direct lookup)")
    parser.add_argument("--workspace-name", default=DEFAULT_WORKSPACE_NAME, help="Workspace display name")
    parser.add_argument("--lakehouse-name", default=DEFAULT_LAKEHOUSE_NAME, help="Lakehouse display name")
    parser.add_argument("--capacity-id", default="2f4f34b6-27ae-4873-b49d-7f854dc158ee", help="Fabric capacity GUID")
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser", help="Auth method")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   AAP Data Agent POC — Lakehouse Provisioning          ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Authenticate via browser
    credential = get_credential(args.auth)
    token = get_token(credential)
    print("   ✅ Authenticated successfully.\n")

    # Find workspace
    ws = find_workspace(token, name=args.workspace_name, ws_id=args.workspace_id)
    if not ws:
        print("\n💡 Try passing --workspace-id with the GUID from your portal URL.")
        sys.exit(1)

    # Create or find lakehouse
    lh = find_or_create_lakehouse(token, ws["id"], args.lakehouse_name)
    if not lh:
        print("❌ Could not create or find lakehouse.")
        sys.exit(1)

    # Get SQL endpoint
    sql_ep = get_sql_endpoint(token, ws["id"], lh["id"])

    # Write config
    capacity_id = ws.get("capacityId", args.capacity_id)
    write_env_file(ws, lh, sql_ep, capacity_id)

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                  Provisioning Complete                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Workspace:     {ws['displayName']}")
    print(f"  Workspace ID:  {ws['id']}")
    print(f"  Lakehouse:     {lh['displayName']}")
    print(f"  Lakehouse ID:  {lh['id']}")
    print(f"  SQL Endpoint:  {sql_ep}")
    print(f"  Config File:   {ENV_FILE}")
    print()
    print("Next steps:")
    print("  1. Import and run notebooks/01-create-sample-data.py in the workspace")
    print("  2. Run: python scripts/deploy-semantic-views.ps1")
    print("     (or: ./scripts/deploy-semantic-views.ps1)")


if __name__ == "__main__":
    main()
