#!/usr/bin/env python3
"""
Deploy semantic contract views to the Fabric Lakehouse SQL endpoint.

Uses InteractiveBrowserCredential for auth (same as provision-lakehouse.py)
to avoid Azure CLI token visibility issues in Microsoft corporate tenants.

Usage:
    python scripts/deploy-views.py
    python scripts/deploy-views.py --auth device-code
    python scripts/deploy-views.py --sql-endpoint "xxx.datawarehouse.fabric.microsoft.com" --database "RewardsLoyaltyData"
"""

import argparse
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env.fabric"
SQL_FILE = SCRIPT_DIR / "create-semantic-views.sql"
DB_SCOPE = "https://database.windows.net/.default"


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


def get_db_token(credential) -> str:
    token = credential.get_token(DB_SCOPE)
    return token.token


def split_sql_on_go(sql_text: str) -> list:
    """Split SQL script on GO statements, extract view names."""
    blocks = re.split(r'(?mi)^\s*GO\s*$', sql_text)
    statements = []
    for block in blocks:
        trimmed = block.strip()
        if not trimmed or re.match(r'^\s*--', trimmed):
            continue

        # Extract view name (schema-qualified or plain)
        name = "unknown"
        m = re.search(
            r'CREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?VIEW\s+(?:\[?(\w+)\]?\.)?\[?(\w+)\]?',
            trimmed, re.IGNORECASE
        )
        if m:
            schema = m.group(1)
            vname = m.group(2)
            name = f"{schema}.{vname}" if schema else vname

        statements.append({"name": name, "sql": trimmed})
    return statements


def deploy_views(token: str, endpoint: str, database: str, sql_file: Path, dry_run: bool = False):
    """Deploy each SQL statement using pyodbc or pymssql."""

    # Try pyodbc first, then pymssql
    conn = None
    driver_name = None

    try:
        import pyodbc
        # Find ODBC driver
        drivers = [d for d in pyodbc.drivers() if 'ODBC Driver' in d and 'SQL Server' in d]
        if drivers:
            driver = sorted(drivers)[-1]  # Use latest version
            conn_str = (
                f"Driver={{{driver}}};"
                f"Server={endpoint};"
                f"Database={database};"
                f"Encrypt=yes;"
                f"TrustServerCertificate=no;"
            )
            # pyodbc with AAD token needs special struct
            import struct
            token_bytes = token.encode("UTF-16-LE")
            token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)

            conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
            driver_name = f"pyodbc ({driver})"
    except (ImportError, Exception) as e:
        print(f"   ⚠️ pyodbc not available: {e}")

    if not conn:
        # Fallback: try Invoke-Sqlcmd via PowerShell subprocess
        try:
            import subprocess
            result = subprocess.run(
                ["pwsh", "-Command", "Get-Command Invoke-Sqlcmd -ErrorAction SilentlyContinue"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                driver_name = "Invoke-Sqlcmd (PowerShell)"
                return deploy_via_sqlcmd(token, endpoint, database, sql_file, dry_run)
        except Exception:
            pass

    if not conn:
        print("❌ No SQL driver available. Install one of:")
        print("   pip install pyodbc    (requires ODBC Driver for SQL Server)")
        print("   Install-Module SqlServer -Scope CurrentUser  (PowerShell)")
        print("")
        print("   ODBC Driver download: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server")
        sys.exit(1)

    print(f"   Using: {driver_name}")
    print()

    # Read and split SQL
    sql_text = sql_file.read_text(encoding="utf-8")
    statements = split_sql_on_go(sql_text)

    if not statements:
        print("⚠️ No SQL statements found.")
        return

    print(f"   Found {len(statements)} statement(s) to execute.")
    print()

    success = 0
    failed = 0
    cursor = conn.cursor()

    for stmt in statements:
        name = stmt["name"]
        if dry_run:
            print(f"   [DRY-RUN] Would deploy: {name}")
            success += 1
            continue

        print(f"   [·] Deploying: {name}...", end=" ", flush=True)
        try:
            cursor.execute(stmt["sql"])
            conn.commit()
            print("✅")
            success += 1
        except Exception as e:
            print(f"❌\n       Error: {e}")
            failed += 1

    cursor.close()
    conn.close()
    return success, failed


def deploy_via_sqlcmd(token: str, endpoint: str, database: str, sql_file: Path, dry_run: bool = False):
    """Fallback: deploy using PowerShell Invoke-Sqlcmd."""
    import subprocess

    sql_text = sql_file.read_text(encoding="utf-8")
    statements = split_sql_on_go(sql_text)

    if not statements:
        print("⚠️ No SQL statements found.")
        return 0, 0

    print(f"   Using: Invoke-Sqlcmd (PowerShell)")
    print(f"   Found {len(statements)} statement(s) to execute.")
    print()

    success = 0
    failed = 0

    for stmt in statements:
        name = stmt["name"]
        if dry_run:
            print(f"   [DRY-RUN] Would deploy: {name}")
            success += 1
            continue

        print(f"   [·] Deploying: {name}...", end=" ", flush=True)

        # Write SQL to temp file to avoid quoting issues
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
            f.write(stmt["sql"])
            tmp_path = f.name

        try:
            ps_cmd = (
                f'Invoke-Sqlcmd -ServerInstance "{endpoint}" -Database "{database}" '
                f'-AccessToken "{token}" -InputFile "{tmp_path}" -QueryTimeout 120 -ErrorAction Stop'
            )
            result = subprocess.run(
                ["pwsh", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode == 0:
                print("✅")
                success += 1
            else:
                print(f"❌\n       Error: {result.stderr.strip()}")
                failed += 1
        except Exception as e:
            print(f"❌\n       Error: {e}")
            failed += 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    return success, failed


def main():
    parser = argparse.ArgumentParser(description="Deploy semantic views to Fabric SQL endpoint")
    parser.add_argument("--sql-endpoint", help="SQL endpoint (default: from .env.fabric)")
    parser.add_argument("--database", help="Database name (default: from .env.fabric)")
    parser.add_argument("--sql-file", help="SQL file path (default: scripts/create-semantic-views.sql)")
    parser.add_argument("--auth", choices=["browser", "device-code"], default="browser")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════╗")
    print("║   AAP Data Agent POC — Deploy Semantic Views           ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Load config
    env = read_env_file(ENV_FILE)

    endpoint = args.sql_endpoint or env.get("FABRIC_SQL_ENDPOINT", "")
    database = args.database or env.get("FABRIC_LAKEHOUSE_NAME", "RewardsLoyaltyData")
    sql_path = Path(args.sql_file) if args.sql_file else SQL_FILE

    if not endpoint or "pending" in endpoint:
        print("❌ No SQL endpoint found. Run provision-lakehouse.py first.")
        sys.exit(1)

    if not sql_path.exists():
        print(f"❌ SQL file not found: {sql_path}")
        sys.exit(1)

    print(f"   SQL Endpoint:  {endpoint}")
    print(f"   Database:      {database}")
    print(f"   SQL File:      {sql_path}")
    print()

    # Authenticate
    credential = get_credential(args.auth)
    token = get_db_token(credential)
    print("   ✅ Database token acquired.")
    print()

    if args.dry_run:
        print("   🔍 DRY RUN — no changes will be made.")
        print()

    # Deploy
    result = deploy_views(token, endpoint, database, sql_path, args.dry_run)

    if result is None:
        return

    success, failed = result

    print()
    if failed == 0:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║              All views deployed successfully            ║")
        print("╚══════════════════════════════════════════════════════════╝")
    else:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║              Deployment completed with errors           ║")
        print("╚══════════════════════════════════════════════════════════╝")

    print(f"  ✅ Succeeded: {success}")
    print(f"  {'❌' if failed else '  '} Failed:    {failed}")
    print()

    if failed > 0:
        print("Troubleshooting:")
        print("  - Ensure the data generation notebook has been run first")
        print("  - Check that your account has write access to the Lakehouse")
        print("  - Verify the SQL endpoint is fully provisioned")
        sys.exit(1)
    else:
        print("Next steps:")
        print("  1. Open the Lakehouse SQL endpoint in the Fabric portal")
        print("  2. Verify: SELECT * FROM semantic.v_member_summary LIMIT 10")
        print("  3. Configure the Fabric Data Agent on the semantic views")
        print("  4. Use config/sample-queries.json for Data Agent examples")


if __name__ == "__main__":
    main()
