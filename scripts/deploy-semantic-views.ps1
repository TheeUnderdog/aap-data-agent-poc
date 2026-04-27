<#
.SYNOPSIS
    Deploys semantic contract views to the Fabric Lakehouse SQL endpoint.

.DESCRIPTION
    Reads a SQL file containing CREATE VIEW statements and executes each one
    against the Lakehouse SQL endpoint using AAD token authentication.

.PARAMETER SqlEndpoint
    The Lakehouse SQL endpoint connection string. If omitted, reads from scripts/.env.fabric.

.PARAMETER SqlFile
    Path to the SQL file containing view definitions. Default: scripts/create-semantic-views.sql

.PARAMETER DatabaseName
    The Lakehouse database name. Defaults to the Lakehouse name from .env.fabric or "RewardsLoyaltyData".

.EXAMPLE
    ./deploy-semantic-views.ps1

.EXAMPLE
    ./deploy-semantic-views.ps1 -SqlEndpoint "xxx.datawarehouse.fabric.microsoft.com" -SqlFile "./my-views.sql"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter()]
    [string]$SqlEndpoint,

    [Parameter()]
    [string]$SqlFile,

    [Parameter()]
    [string]$DatabaseName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$EnvFile = Join-Path $ScriptDir ".env.fabric"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Write-Status  { param([string]$Msg) Write-Host "[✓] $Msg" -ForegroundColor Green }
function Write-Info    { param([string]$Msg) Write-Host "[·] $Msg" -ForegroundColor Cyan }
function Write-Warn    { param([string]$Msg) Write-Host "[!] $Msg" -ForegroundColor Yellow }
function Write-Err     { param([string]$Msg) Write-Host "[✗] $Msg" -ForegroundColor Red }

function Read-EnvFile {
    <# Parses a KEY=VALUE env file into a hashtable. #>
    param([string]$Path)
    $env = @{}
    if (Test-Path $Path) {
        Get-Content $Path | ForEach-Object {
            if ($_ -match '^\s*([A-Z_]+)\s*=\s*([^#]+?)(?:\s*#.*)?$') {
                $env[$Matches[1]] = $Matches[2].Trim()
            }
        }
    }
    return $env
}

function Get-FabricToken {
    try {
        $tokenJson = az account get-access-token --resource "https://database.windows.net" 2>&1
        if ($LASTEXITCODE -ne 0) { throw "az CLI returned exit code $LASTEXITCODE" }
        $token = ($tokenJson | ConvertFrom-Json).accessToken
        if (-not $token) { throw "Token was empty" }
        return $token
    }
    catch {
        Write-Err "Failed to get database access token. Ensure you are logged in with 'az login'."
        throw
    }
}

function Split-SqlStatements {
    <# Splits a SQL script into individual statements on GO or semicolons at statement boundaries.
       Returns an array of objects with Name and Sql properties. #>
    param([string]$SqlText)

    $statements = @()
    # Split on GO keyword (common in SQL scripts) or double-newline-separated statements
    $blocks = $SqlText -split '(?mi)^\s*GO\s*$'

    foreach ($block in $blocks) {
        $trimmed = $block.Trim()
        if (-not $trimmed) { continue }
        # Skip blocks that are ONLY comments (no actual SQL)
        $nonCommentLines = ($trimmed -split "`n") | Where-Object { $_ -notmatch '^\s*--' -and $_.Trim() -ne '' }
        if (-not $nonCommentLines) { continue }

        # Extract view name from CREATE VIEW statement
        $name = "unknown"
        if ($trimmed -match 'CREATE\s+(?:OR\s+(?:REPLACE|ALTER)\s+)?VIEW\s+(?:\[?(\w+)\]?\.)?\[?(\w+)\]?') {
            # Schema-qualified: semantic.v_member_summary or [semantic].[v_member_summary]
            if ($Matches[1]) {
                $name = "$($Matches[1]).$($Matches[2])"
            } else {
                $name = $Matches[2]
            }
        }

        $statements += [PSCustomObject]@{
            Name = $name
            Sql  = $trimmed
        }
    }
    return $statements
}

# ── Pre-flight ───────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   AAP Data Agent POC — Deploy Semantic Views           ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# Load .env.fabric defaults
$envConfig = Read-EnvFile -Path $EnvFile

# Resolve parameters
if (-not $SqlEndpoint) {
    $SqlEndpoint = $envConfig["FABRIC_SQL_ENDPOINT"]
    if (-not $SqlEndpoint -or $SqlEndpoint -like "*pending*") {
        Write-Err "No SQL endpoint provided and none found in $EnvFile."
        Write-Err "Run setup-workspace.ps1 first, or pass -SqlEndpoint explicitly."
        exit 1
    }
}

if (-not $SqlFile) {
    $SqlFile = Join-Path $ScriptDir "create-semantic-views.sql"
}

if (-not $DatabaseName) {
    $DatabaseName = $envConfig["FABRIC_LAKEHOUSE_NAME"]
    if (-not $DatabaseName) { $DatabaseName = "RewardsLoyaltyData" }
}

if (-not (Test-Path $SqlFile)) {
    Write-Err "SQL file not found: $SqlFile"
    Write-Err "Ensure the semantic views SQL file exists. Livingston should provide this."
    exit 1
}

# Check Azure CLI
$azPath = Get-Command az -ErrorAction SilentlyContinue
if (-not $azPath) {
    Write-Err "Azure CLI (az) not found. Install from https://aka.ms/installazurecli"
    exit 1
}

Write-Info "SQL Endpoint:  $SqlEndpoint"
Write-Info "Database:      $DatabaseName"
Write-Info "SQL File:      $SqlFile"
Write-Host ""

# ── Get token ────────────────────────────────────────────────────────────────

Write-Info "Authenticating to database endpoint..."
$accessToken = Get-FabricToken
Write-Status "Authenticated successfully."

# ── Read and parse SQL ───────────────────────────────────────────────────────

Write-Info "Reading SQL file..."
$sqlContent = Get-Content -Path $SqlFile -Raw -Encoding UTF8
$statements = @(Split-SqlStatements -SqlText $sqlContent)

if ($statements.Count -eq 0) {
    Write-Warn "No SQL statements found in $SqlFile."
    exit 0
}

Write-Status "Found $($statements.Count) statement(s) to execute."

# ── Execute views ────────────────────────────────────────────────────────────

# Try Invoke-Sqlcmd first (from SqlServer module), fall back to SqlClient
$useSqlCmd = $false
if (Get-Command Invoke-Sqlcmd -ErrorAction SilentlyContinue) {
    $useSqlCmd = $true
    Write-Info "Using Invoke-Sqlcmd for execution."
}
else {
    Write-Info "Invoke-Sqlcmd not available. Using System.Data.SqlClient."
}

$successCount = 0
$failCount = 0

foreach ($stmt in $statements) {
    $viewName = $stmt.Name

    if ($PSCmdlet.ShouldProcess($viewName, "Create/replace view")) {
        Write-Info "Deploying: $viewName..."

        try {
            if ($useSqlCmd) {
                Invoke-Sqlcmd `
                    -ServerInstance $SqlEndpoint `
                    -Database $DatabaseName `
                    -AccessToken $accessToken `
                    -Query $stmt.Sql `
                    -QueryTimeout 120 `
                    -ErrorAction Stop
            }
            else {
                # SqlClient fallback
                $connStr = "Server=$SqlEndpoint;Database=$DatabaseName;Encrypt=True;TrustServerCertificate=False;"
                $conn = [System.Data.SqlClient.SqlConnection]::new($connStr)
                $conn.AccessToken = $accessToken
                $conn.Open()

                try {
                    $cmd = $conn.CreateCommand()
                    $cmd.CommandText = $stmt.Sql
                    $cmd.CommandTimeout = 120
                    $cmd.ExecuteNonQuery() | Out-Null
                }
                finally {
                    $conn.Close()
                    $conn.Dispose()
                }
            }

            Write-Status "  $viewName — deployed successfully."
            $successCount++
        }
        catch {
            Write-Err "  $viewName — FAILED: $($_.Exception.Message)"
            $failCount++
        }
    }
}

# ── Summary ─────────────────────────────────────────────────────────────────

Write-Host ""
if ($failCount -eq 0) {
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              All views deployed successfully            ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
}
else {
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║              Deployment completed with errors           ║" -ForegroundColor Yellow
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  Succeeded: $successCount" -ForegroundColor Green
Write-Host "  Failed:    $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Gray" })
Write-Host ""

if ($failCount -gt 0) {
    Write-Host "Troubleshooting tips:" -ForegroundColor Cyan
    Write-Host "  - Ensure the underlying tables exist (run data generation notebook first)" -ForegroundColor White
    Write-Host "  - Check that your account has write access to the Lakehouse" -ForegroundColor White
    Write-Host "  - Verify the SQL endpoint is fully provisioned (may take a few minutes)" -ForegroundColor White
    Write-Host ""
    exit 1
}
