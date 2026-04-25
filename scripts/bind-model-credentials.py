#!/usr/bin/env python3
"""
Bind OAuth2 credentials to the AAP Rewards Loyalty Model and trigger a refresh.

After deploying a semantic model via Fabric REST API (TMDL), the model's data
sources have no credentials. This script:
  1. Takes over the dataset (binds current user's OAuth2 creds)
  2. Discovers gateway/datasource IDs
  3. Patches each datasource with OAuth2 credentials
  4. Triggers a refresh

Usage:
    python scripts/bind-model-credentials.py
    python scripts/bind-model-credentials.py --auth device-code
    python scripts/bind-model-credentials.py --skip-refresh
    python scripts/bind-model-credentials.py --model-name "My Model"
"""

import argparse
import json
import re
import sys
import time
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
PBI_API = "https://api.powerbi.com/v1.0/myorg"
PBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"

DEFAULT_MODEL_NAME = "AAP Rewards Loyalty Model"


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


def get_token(credential, scope: str) -> str:
    return credential.get_token(scope).token


def find_semantic_model_id(workspace_id: str, model_name: str, fabric_headers: dict) -> str:
    """Find the semantic model ID by name using Fabric REST API."""
    r = requests.get(
        f"{FABRIC_API}/workspaces/{workspace_id}/semanticModels",
        headers=fabric_headers,
    )
    if r.status_code != 200:
        print(f"  ERROR: Failed to list semantic models ({r.status_code}): {r.text[:300]}")
        sys.exit(1)

    for sm in r.json().get("value", []):
        if sm["displayName"] == model_name:
            return sm["id"]

    print(f"  ERROR: Semantic model '{model_name}' not found in workspace.")
    print(f"  Available models:")
    for sm in r.json().get("value", []):
        print(f"    - {sm['displayName']} (ID: {sm['id']})")
    sys.exit(1)


def take_over_dataset(dataset_id: str, pbi_headers: dict) -> bool:
    """Take over the dataset — binds current user as data source owner."""
    print(f"  Taking over dataset {dataset_id}...")
    r = requests.post(
        f"{PBI_API}/datasets/{dataset_id}/Default.TakeOver",
        headers=pbi_headers,
    )
    if r.status_code in (200, 204):
        print("  OK: Dataset takeover succeeded.")
        return True
    elif r.status_code == 409:
        print("  OK: You already own this dataset (409 conflict — expected).")
        return True
    else:
        print(f"  ERROR: Takeover failed ({r.status_code}): {r.text[:500]}")
        return False


def get_datasources(dataset_id: str, pbi_headers: dict) -> list:
    """Get datasource info including gateway and datasource IDs."""
    print("  Discovering data sources...")
    r = requests.get(
        f"{PBI_API}/datasets/{dataset_id}/datasources",
        headers=pbi_headers,
    )
    if r.status_code != 200:
        print(f"  ERROR: Failed to get datasources ({r.status_code}): {r.text[:500]}")
        return []

    sources = r.json().get("value", [])
    print(f"  Found {len(sources)} data source(s).")
    for i, ds in enumerate(sources):
        gw_id = ds.get("gatewayId", "N/A")
        ds_id = ds.get("datasourceId", "N/A")
        ds_type = ds.get("datasourceType", "N/A")
        conn = ds.get("connectionDetails", {})
        server = conn.get("server", "N/A")
        db = conn.get("database", "N/A")
        print(f"    [{i+1}] Type: {ds_type} | Server: {server} | DB: {db}")
        print(f"         Gateway: {gw_id} | Datasource: {ds_id}")
    return sources


def update_datasource_credentials(gateway_id: str, datasource_id: str, pbi_headers: dict) -> bool:
    """Patch datasource credentials to OAuth2."""
    print(f"  Updating credentials for datasource {datasource_id}...")
    body = {
        "credentialDetails": {
            "credentialType": "OAuth2",
            "credentials": json.dumps({"credentialData": ""}),
            "encryptedConnection": "Encrypted",
            "encryptionAlgorithm": "None",
            "privacyLevel": "Organizational",
        }
    }
    r = requests.patch(
        f"{PBI_API}/gateways/{gateway_id}/datasources/{datasource_id}",
        headers=pbi_headers,
        json=body,
    )
    if r.status_code in (200, 204):
        print(f"  OK: Credentials updated (OAuth2).")
        return True
    else:
        print(f"  WARNING: Credential update returned {r.status_code}: {r.text[:500]}")
        print(f"  (This may be OK — takeover alone often suffices for Fabric lakehouses.)")
        return False


def trigger_refresh(dataset_id: str, pbi_headers: dict) -> bool:
    """Trigger a dataset refresh."""
    print("  Triggering dataset refresh...")
    r = requests.post(
        f"{PBI_API}/datasets/{dataset_id}/refreshes",
        headers=pbi_headers,
        json={"notifyOption": "NoNotification"},
    )
    if r.status_code == 202:
        print("  OK: Refresh triggered (202 Accepted).")
        return True
    elif r.status_code == 200:
        print("  OK: Refresh triggered.")
        return True
    else:
        print(f"  WARNING: Refresh request returned {r.status_code}: {r.text[:500]}")
        return False


def poll_refresh_status(dataset_id: str, pbi_headers: dict, max_wait: int = 300):
    """Poll refresh status until completion or timeout."""
    print(f"  Polling refresh status (max {max_wait}s)...")
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(10)
        r = requests.get(
            f"{PBI_API}/datasets/{dataset_id}/refreshes?$top=1",
            headers=pbi_headers,
        )
        if r.status_code != 200:
            print(f"  Could not check refresh status ({r.status_code}).")
            break

        refreshes = r.json().get("value", [])
        if not refreshes:
            print("  No refresh history found.")
            break

        latest = refreshes[0]
        status = latest.get("status", "Unknown")
        elapsed = int(time.time() - start)

        if status == "Completed":
            print(f"  OK: Refresh completed successfully ({elapsed}s).")
            return True
        elif status == "Failed":
            error = latest.get("serviceExceptionJson", "")
            print(f"  ERROR: Refresh failed ({elapsed}s).")
            if error:
                print(f"  Detail: {error[:500]}")
            return False
        elif status == "Disabled":
            print(f"  ERROR: Refresh is disabled on this dataset.")
            return False
        else:
            print(f"    Status: {status} ({elapsed}s elapsed)...")

    print("  Timed out waiting for refresh. Check Fabric portal.")
    return False


def bind_and_refresh(credential, workspace_id: str, model_name: str, skip_refresh: bool = False):
    """
    Full bind-and-refresh flow. Can be called standalone or from create-semantic-model.py.
    Returns True if all steps succeeded.
    """
    # Get tokens for both APIs
    fabric_token = get_token(credential, FABRIC_SCOPE)
    pbi_token = get_token(credential, PBI_SCOPE)

    fabric_headers = {
        "Authorization": f"Bearer {fabric_token}",
        "Content-Type": "application/json",
    }
    pbi_headers = {
        "Authorization": f"Bearer {pbi_token}",
        "Content-Type": "application/json",
    }

    # Step 1: Find the semantic model
    print(f"\n  [1/4] Finding semantic model '{model_name}'...")
    dataset_id = find_semantic_model_id(workspace_id, model_name, fabric_headers)
    print(f"  Found: {dataset_id}")

    # Step 2: Take over the dataset
    print(f"\n  [2/4] Taking over dataset...")
    if not take_over_dataset(dataset_id, pbi_headers):
        print("\n  FAILED: Could not take over dataset. Are you an admin/owner?")
        return False

    # Brief pause for takeover to propagate
    time.sleep(3)

    # Step 3: Get and update datasource credentials
    print(f"\n  [3/4] Updating data source credentials...")
    datasources = get_datasources(dataset_id, pbi_headers)
    if datasources:
        for ds in datasources:
            gw_id = ds.get("gatewayId")
            ds_id = ds.get("datasourceId")
            if gw_id and ds_id:
                update_datasource_credentials(gw_id, ds_id, pbi_headers)
    else:
        print("  No datasources found — takeover may be sufficient for Fabric lakehouse sources.")

    # Step 4: Trigger refresh
    if skip_refresh:
        print(f"\n  [4/4] Skipping refresh (--skip-refresh).")
        print("\n  Done! Credentials are bound. Refresh manually when ready.")
        return True

    print(f"\n  [4/4] Triggering refresh...")
    if trigger_refresh(dataset_id, pbi_headers):
        return poll_refresh_status(dataset_id, pbi_headers)
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Bind OAuth2 credentials to semantic model and trigger refresh"
    )
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="Semantic model name")
    parser.add_argument("--skip-refresh", action="store_true", help="Bind credentials but don't refresh")
    args = parser.parse_args()

    print("=" * 60)
    print("  AAP Data Agent POC -- Bind Model Credentials & Refresh")
    print("=" * 60)

    env = read_env_file(ENV_FILE)
    workspace_id = env.get("FABRIC_WORKSPACE_ID", "")
    if not workspace_id:
        print("  ERROR: Missing FABRIC_WORKSPACE_ID in .env.fabric")
        sys.exit(1)

    print(f"  Workspace: {workspace_id}")
    print(f"  Model:     {args.model_name}")

    credential = get_credential(args.auth)
    success = bind_and_refresh(credential, workspace_id, args.model_name, args.skip_refresh)

    print()
    if success:
        print("  SUCCESS: Model credentials bound and refresh complete.")
    else:
        print("  COMPLETED WITH WARNINGS: Check output above for details.")
        print("  You can also refresh manually in the Fabric portal.")

    print(f"  Portal: https://app.fabric.microsoft.com/groups/{workspace_id}")


if __name__ == "__main__":
    main()
