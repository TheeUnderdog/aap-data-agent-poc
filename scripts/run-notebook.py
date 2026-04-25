#!/usr/bin/env python3
"""
Upload, configure, and run a Fabric notebook via the REST API.

Converts the local .py notebook (Jupytext-style # %% cells) into Fabric's
fabricGitSource format, uploads it with the default lakehouse attached,
triggers an on-demand run, and polls until completion.

Uses InteractiveBrowserCredential (opens browser) — same auth pattern as
provision-lakehouse.py.

Usage:
    python scripts/run-notebook.py
    python scripts/run-notebook.py --auth device-code
    python scripts/run-notebook.py --dry-run
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

FABRIC_API = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"
NOTEBOOK_SOURCE = PROJECT_DIR / "notebooks" / "01-create-sample-data.py"
NOTEBOOK_DISPLAY_NAME = "01-create-sample-data"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def read_env_file() -> dict:
    """Read key=value pairs from .env.fabric, stripping inline comments."""
    env = {}
    if not ENV_FILE.exists():
        print(f"❌ Config file not found: {ENV_FILE}")
        print("   Run provision-lakehouse.py first.")
        sys.exit(1)
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Z_]+)\s*=\s*(.+?)(?:\s*#.*)?$", line)
        if m:
            env[m.group(1)] = m.group(2).strip()
    return env


# ---------------------------------------------------------------------------
# Auth (mirrors provision-lakehouse.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Fabric API helpers
# ---------------------------------------------------------------------------

def fabric_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def fabric_get(token: str, path: str) -> requests.Response:
    r = requests.get(f"{FABRIC_API}{path}", headers=fabric_headers(token))
    return r


def fabric_post(token: str, path: str, body: dict = None) -> requests.Response:
    r = requests.post(
        f"{FABRIC_API}{path}",
        headers=fabric_headers(token),
        json=body,
    )
    return r


def fabric_delete(token: str, path: str) -> requests.Response:
    r = requests.delete(f"{FABRIC_API}{path}", headers=fabric_headers(token))
    return r


def fabric_patch(token: str, path: str, body: dict) -> requests.Response:
    r = requests.patch(
        f"{FABRIC_API}{path}",
        headers=fabric_headers(token),
        json=body,
    )
    return r


def wait_for_lro(token: str, response: requests.Response, label: str, max_wait: int = 120) -> bool:
    """Poll a long-running operation (LRO) returned in the Location header."""
    location = response.headers.get("Location")
    if not location:
        return True

    retry_after = int(response.headers.get("Retry-After", 5))
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(retry_after)
        r = requests.get(location, headers=fabric_headers(token))
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "")
            if status in ("Succeeded", "Completed"):
                print(f"   ✅ {label} succeeded.")
                return True
            elif status == "Failed":
                print(f"   ❌ {label} failed: {data}")
                return False
            else:
                elapsed = int(time.time() - start)
                print(f"   ⏳ {label} — {status} ({elapsed}s)...")
        elif r.status_code == 202:
            location = r.headers.get("Location", location)
            retry_after = int(r.headers.get("Retry-After", 5))
            elapsed = int(time.time() - start)
            print(f"   ⏳ {label} — provisioning ({elapsed}s)...")
        else:
            print(f"   ⚠️  LRO poll returned {r.status_code}: {r.text[:300]}")
            return False

    print(f"   ⚠️  {label} timed out after {max_wait}s.")
    return False


# ---------------------------------------------------------------------------
# Notebook format conversion
# ---------------------------------------------------------------------------

def convert_jupytext_to_fabric(source: str, workspace_id: str, lakehouse_id: str, lakehouse_name: str) -> str:
    """
    Convert a Jupytext-style .py notebook (# %% markers) into Fabric's
    fabricGitSource format (# CELL / # MARKDOWN / # METADATA blocks).
    """
    lines = source.splitlines()

    # Build the Fabric notebook header with lakehouse metadata
    header = [
        "# Fabric notebook source",
        "",
        "# METADATA ********************",
        "# META {",
        '# META   "kernel_info": {',
        '# META     "name": "synapse_pyspark"',
        "# META   },",
        '# META   "dependencies": {',
        '# META     "lakehouse": {',
        f'# META       "default_lakehouse": "{lakehouse_id}",',
        f'# META       "default_lakehouse_name": "{lakehouse_name}",',
        f'# META       "default_lakehouse_workspace_id": "{workspace_id}",',
        '# META       "known_lakehouses": [',
        "# META         {",
        f'# META           "id": "{lakehouse_id}"',
        "# META         }",
        "# META       ]",
        "# META     }",
        "# META   }",
        "# META }",
    ]

    # Parse cells from Jupytext format
    cells = []
    current_cell = None

    for line in lines:
        if line.strip() == "# %% [markdown]":
            if current_cell is not None:
                cells.append(current_cell)
            current_cell = {"type": "markdown", "lines": []}
        elif line.strip() == "# %%":
            if current_cell is not None:
                cells.append(current_cell)
            current_cell = {"type": "code", "lines": []}
        elif current_cell is not None:
            if current_cell["type"] == "markdown":
                # Markdown lines are prefixed with "# "
                if line.startswith("# "):
                    current_cell["lines"].append(line[2:])
                elif line.strip() == "#":
                    current_cell["lines"].append("")
                else:
                    current_cell["lines"].append(line)
            else:
                current_cell["lines"].append(line)

    if current_cell is not None:
        cells.append(current_cell)

    # Build Fabric notebook content
    output_lines = list(header)

    for cell in cells:
        # Strip trailing blank lines from cell content
        cell_lines = cell["lines"]
        while cell_lines and cell_lines[-1].strip() == "":
            cell_lines = cell_lines[:-1]
        if not cell_lines:
            continue

        output_lines.append("")

        if cell["type"] == "markdown":
            output_lines.append("# MARKDOWN ********************")
            output_lines.append("")
            for cl in cell_lines:
                if cl:
                    output_lines.append(f"# {cl}")
                else:
                    output_lines.append("#")
        else:
            output_lines.append("# CELL ********************")
            output_lines.append("")
            output_lines.extend(cell_lines)

        # Add cell metadata
        output_lines.append("")
        output_lines.append("# METADATA ********************")
        output_lines.append("")
        output_lines.append("# META {")
        output_lines.append('# META   "language": "python",')
        output_lines.append('# META   "language_group": "synapse_pyspark"')
        output_lines.append("# META }")

    output_lines.append("")
    return "\n".join(output_lines)


# ---------------------------------------------------------------------------
# Notebook CRUD
# ---------------------------------------------------------------------------

def find_existing_notebook(token: str, workspace_id: str, name: str) -> str | None:
    """Return notebook item ID if one with this name already exists, else None."""
    print(f"📓 Checking for existing notebook '{name}'...")
    r = fabric_get(token, f"/workspaces/{workspace_id}/notebooks")
    if r.status_code != 200:
        print(f"   ⚠️  Could not list notebooks ({r.status_code}): {r.text[:200]}")
        return None
    for nb in r.json().get("value", []):
        if nb["displayName"] == name:
            print(f"   ✅ Found existing: {nb['id']}")
            return nb["id"]
    print("   (not found — will create)")
    return None


def build_definition_payload(fabric_content: str) -> dict:
    """Build the definition object with base64-encoded parts."""
    content_b64 = base64.b64encode(fabric_content.encode("utf-8")).decode("ascii")

    platform_json = json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {
            "type": "Notebook",
            "displayName": NOTEBOOK_DISPLAY_NAME,
            "description": "AAP Loyalty Program — Sample Data Generator"
        },
        "config": {
            "version": "2.0",
            "logicalId": "00000000-0000-0000-0000-000000000000"
        }
    }, indent=2)
    platform_b64 = base64.b64encode(platform_json.encode("utf-8")).decode("ascii")

    return {
        "format": "fabricGitSource",
        "parts": [
            {
                "path": "notebook-content.py",
                "payload": content_b64,
                "payloadType": "InlineBase64",
            },
            {
                "path": ".platform",
                "payload": platform_b64,
                "payloadType": "InlineBase64",
            },
        ],
    }


def create_notebook(token: str, workspace_id: str, fabric_content: str) -> str | None:
    """Create a new notebook and return its item ID."""
    print(f"   Creating notebook '{NOTEBOOK_DISPLAY_NAME}'...")
    body = {
        "displayName": NOTEBOOK_DISPLAY_NAME,
        "description": "AAP Loyalty Program — Sample Data Generator",
        "definition": build_definition_payload(fabric_content),
    }
    r = fabric_post(token, f"/workspaces/{workspace_id}/notebooks", body)

    if r.status_code == 201:
        nb = r.json()
        print(f"   ✅ Created: {nb['id']}")
        return nb["id"]
    elif r.status_code == 202:
        # LRO — wait for provisioning
        if wait_for_lro(token, r, "Notebook creation"):
            # Fetch the notebook ID
            return find_existing_notebook(token, workspace_id, NOTEBOOK_DISPLAY_NAME)
        return None
    elif r.status_code == 409:
        print("   ⚠️  409 conflict — already exists. Fetching...")
        return find_existing_notebook(token, workspace_id, NOTEBOOK_DISPLAY_NAME)
    else:
        print(f"   ❌ Create failed ({r.status_code}): {r.text[:500]}")
        return None


def update_notebook_definition(token: str, workspace_id: str, notebook_id: str, fabric_content: str) -> bool:
    """Update an existing notebook's definition."""
    print(f"   Updating notebook definition...")
    definition = build_definition_payload(fabric_content)
    url = f"{FABRIC_API}/workspaces/{workspace_id}/notebooks/{notebook_id}/updateDefinition?updateMetadata=true"
    r = requests.post(url, headers=fabric_headers(token), json={"definition": definition})

    if r.status_code == 200:
        print("   ✅ Definition updated.")
        return True
    elif r.status_code == 202:
        return wait_for_lro(token, r, "Definition update")
    else:
        print(f"   ❌ Update failed ({r.status_code}): {r.text[:500]}")
        return False


# ---------------------------------------------------------------------------
# Notebook execution
# ---------------------------------------------------------------------------

def run_notebook(token: str, workspace_id: str, notebook_id: str) -> str | None:
    """Trigger on-demand notebook run. Returns job instance URL or None."""
    print("🚀 Triggering notebook run...")
    r = fabric_post(
        token,
        f"/workspaces/{workspace_id}/items/{notebook_id}/jobs/RunNotebook/instances",
    )

    if r.status_code == 202:
        location = r.headers.get("Location", "")
        retry_after = int(r.headers.get("Retry-After", 30))
        print(f"   ✅ Run started. Polling every {retry_after}s...")
        return location
    else:
        print(f"   ❌ Run failed ({r.status_code}): {r.text[:500]}")
        return None


def poll_job(token: str, job_url: str, max_wait: int = 1200) -> bool:
    """Poll job instance until terminal state. Default max 20 min."""
    start = time.time()
    poll_interval = 30

    while time.time() - start < max_wait:
        time.sleep(poll_interval)
        r = requests.get(job_url, headers=fabric_headers(token))

        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "Unknown")
            elapsed = int(time.time() - start)

            if status == "Completed":
                end_time = data.get("endTimeUtc", "")
                print(f"\n   ✅ Notebook completed successfully! ({elapsed}s)")
                if end_time:
                    print(f"      Finished at: {end_time}")
                return True
            elif status in ("Failed", "Cancelled", "Deduped"):
                reason = data.get("failureReason", {})
                msg = reason.get("message", "No details") if isinstance(reason, dict) else str(reason)
                print(f"\n   ❌ Notebook {status.lower()}: {msg}")
                # Dump full response for debugging
                import json as _json
                for key in ("executionData", "error", "errorMessage", "properties"):
                    if key in data:
                        print(f"\n   📋 {key}:")
                        val = data[key]
                        if isinstance(val, (dict, list)):
                            print(f"      {_json.dumps(val, indent=2)[:2000]}")
                        else:
                            print(f"      {str(val)[:2000]}")
                # Show any keys we might be missing
                extra_keys = [k for k in data.keys() if k not in ("id", "status", "startTimeUtc", "endTimeUtc", "failureReason")]
                if extra_keys:
                    print(f"\n   🔑 Additional response keys: {extra_keys}")
                    for ek in extra_keys[:5]:
                        print(f"      {ek}: {str(data[ek])[:500]}")
                return False
            else:
                print(f"   ⏳ {status}... ({elapsed}s)")
        elif r.status_code == 202:
            elapsed = int(time.time() - start)
            print(f"   ⏳ Running... ({elapsed}s)")
        else:
            elapsed = int(time.time() - start)
            print(f"   ⚠️  Poll returned {r.status_code} ({elapsed}s)")

    print(f"\n   ⚠️  Timed out after {max_wait}s. Check the Fabric portal for status.")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Upload and run a Fabric notebook")
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser", help="Auth method")
    parser.add_argument("--dry-run", action="store_true", help="Convert and show payload but don't upload")
    parser.add_argument("--skip-run", action="store_true", help="Upload only, don't execute the notebook")
    parser.add_argument("--force", action="store_true", help="Delete and recreate notebook (bypasses update cache)")
    parser.add_argument("--notebook", type=str, help="Path to notebook .py file (default: notebooks/01-create-sample-data.py)")
    args = parser.parse_args()

    # Allow overriding notebook source via CLI
    global NOTEBOOK_SOURCE, NOTEBOOK_DISPLAY_NAME
    if args.notebook:
        NOTEBOOK_SOURCE = Path(args.notebook)
        NOTEBOOK_DISPLAY_NAME = NOTEBOOK_SOURCE.stem

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   AAP Data Agent POC — Notebook Upload & Run           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Load config
    env = read_env_file()
    workspace_id = env.get("FABRIC_WORKSPACE_ID")
    lakehouse_id = env.get("FABRIC_LAKEHOUSE_ID")
    lakehouse_name = env.get("FABRIC_LAKEHOUSE_NAME", "RewardsLoyaltyData")

    if not workspace_id or not lakehouse_id:
        print("❌ Missing FABRIC_WORKSPACE_ID or FABRIC_LAKEHOUSE_ID in .env.fabric")
        sys.exit(1)

    print(f"  Workspace:  {workspace_id}")
    print(f"  Lakehouse:  {lakehouse_name} ({lakehouse_id})")
    print(f"  Notebook:   {NOTEBOOK_SOURCE.name}")
    print()

    # Read and convert notebook
    if not NOTEBOOK_SOURCE.exists():
        print(f"❌ Notebook source not found: {NOTEBOOK_SOURCE}")
        sys.exit(1)

    source = NOTEBOOK_SOURCE.read_text(encoding="utf-8")
    fabric_content = convert_jupytext_to_fabric(source, workspace_id, lakehouse_id, lakehouse_name)

    if args.dry_run:
        print("--- Fabric notebook content (first 120 lines) ---")
        for i, line in enumerate(fabric_content.splitlines()[:120]):
            print(f"  {i+1:4d} | {line}")
        print("--- end ---")
        print(f"\nTotal lines: {len(fabric_content.splitlines())}")
        return

    # Authenticate
    credential = get_credential(args.auth)
    token = get_token(credential)
    print("   ✅ Authenticated successfully.\n")

    # Upload or update notebook
    existing_id = find_existing_notebook(token, workspace_id, NOTEBOOK_DISPLAY_NAME)

    if existing_id and args.force:
        print(f"   🗑️  --force: Deleting existing notebook {existing_id}...")
        dr = fabric_delete(token, f"/workspaces/{workspace_id}/notebooks/{existing_id}")
        if dr.status_code in (200, 202, 204):
            print("   ✅ Deleted. Waiting 5s for propagation...")
            time.sleep(5)
            existing_id = None
        else:
            print(f"   ⚠️  Delete returned {dr.status_code}: {dr.text[:300]}")
            print("   Falling back to update...")

    if existing_id:
        ok = update_notebook_definition(token, workspace_id, existing_id, fabric_content)
        if not ok:
            print("❌ Failed to update notebook definition.")
            sys.exit(1)
        notebook_id = existing_id
    else:
        notebook_id = create_notebook(token, workspace_id, fabric_content)
        if not notebook_id:
            print("❌ Failed to create notebook.")
            sys.exit(1)

    print()

    if args.skip_run:
        print("⏭️  --skip-run specified. Notebook uploaded but not executed.")
        print(f"   Open in Fabric: https://app.fabric.microsoft.com/groups/{workspace_id}/notebooks/{notebook_id}")
        return

    # Run the notebook
    job_url = run_notebook(token, workspace_id, notebook_id)
    if not job_url:
        print("❌ Could not trigger notebook run.")
        sys.exit(1)

    # If the location is relative, make it absolute
    if job_url.startswith("/"):
        job_url = f"{FABRIC_API}{job_url}"
    elif not job_url.startswith("http"):
        job_url = f"{FABRIC_API}/{job_url}"

    # Poll for completion
    success = poll_job(token, job_url)

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    if success:
        print("║              Notebook Run Complete ✅                   ║")
    else:
        print("║              Notebook Run Failed ❌                     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Notebook:    {NOTEBOOK_DISPLAY_NAME}")
    print(f"  Notebook ID: {notebook_id}")
    print(f"  Workspace:   {workspace_id}")
    print(f"  Lakehouse:   {lakehouse_name}")
    print(f"  Portal:      https://app.fabric.microsoft.com/groups/{workspace_id}/notebooks/{notebook_id}")
    print()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
