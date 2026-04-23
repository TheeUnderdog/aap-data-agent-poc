<#
.SYNOPSIS
    Provisions a Microsoft Fabric workspace and Lakehouse for the AAP Data Agent POC.

.DESCRIPTION
    Creates (or reuses) a Fabric workspace and Lakehouse via the Fabric REST API.
    Outputs workspace ID, Lakehouse ID, and SQL endpoint to scripts/.env.fabric.

.PARAMETER WorkspaceName
    Display name for the Fabric workspace. Default: "AAP-RewardsLoyalty-POC"

.PARAMETER LakehouseName
    Display name for the Lakehouse. Default: "RewardsLoyaltyData"

.PARAMETER CapacityId
    The Fabric capacity GUID to assign the workspace to. Required.

.EXAMPLE
    ./setup-workspace.ps1 -CapacityId "00000000-0000-0000-0000-000000000000"

.EXAMPLE
    ./setup-workspace.ps1 -WorkspaceName "My-POC" -LakehouseName "MyData" -CapacityId "abc-123"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter()]
    [string]$WorkspaceName = "AAP-RewardsLoyalty-POC",

    [Parameter()]
    [string]$LakehouseName = "RewardsLoyaltyData",

    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
        ErrorMessage = "CapacityId must be a valid GUID (e.g., 00000000-0000-0000-0000-000000000000)")]
    [string]$CapacityId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$FabricBaseUrl = "https://api.fabric.microsoft.com/v1"
$ScriptDir = $PSScriptRoot
$EnvFile = Join-Path $ScriptDir ".env.fabric"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Write-Status  { param([string]$Msg) Write-Host "[✓] $Msg" -ForegroundColor Green }
function Write-Info    { param([string]$Msg) Write-Host "[·] $Msg" -ForegroundColor Cyan }
function Write-Warn    { param([string]$Msg) Write-Host "[!] $Msg" -ForegroundColor Yellow }
function Write-Err     { param([string]$Msg) Write-Host "[✗] $Msg" -ForegroundColor Red }

function Get-FabricToken {
    <# Returns a bearer token for the Fabric API via Azure CLI. #>
    try {
        $tokenJson = az account get-access-token --resource "https://api.fabric.microsoft.com" 2>&1
        if ($LASTEXITCODE -ne 0) { throw "az CLI returned exit code $LASTEXITCODE" }
        $token = ($tokenJson | ConvertFrom-Json).accessToken
        if (-not $token) { throw "Token was empty" }
        return $token
    }
    catch {
        Write-Err "Failed to get Fabric access token. Ensure you are logged in with 'az login'."
        throw
    }
}

function Invoke-FabricApi {
    <# Wrapper around Invoke-RestMethod with retry on 429 and better error reporting. #>
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body,
        [int]$MaxRetries = 5
    )

    $attempt = 0
    while ($true) {
        $attempt++
        try {
            $params = @{
                Method      = $Method
                Uri         = $Uri
                Headers     = $Headers
                ContentType = "application/json"
            }
            if ($Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10) }

            return Invoke-RestMethod @params
        }
        catch {
            $status = $null
            if ($_.Exception.Response) {
                $status = [int]$_.Exception.Response.StatusCode
            }

            # 429 — rate limited: retry with exponential backoff
            if ($status -eq 429 -and $attempt -le $MaxRetries) {
                $retryAfter = 2 * [math]::Pow(2, $attempt - 1)   # 2, 4, 8, 16, 32s
                if ($_.Exception.Response.Headers -and $_.Exception.Response.Headers["Retry-After"]) {
                    $retryAfter = [int]$_.Exception.Response.Headers["Retry-After"]
                }
                Write-Warn "Rate limited (429). Retrying in ${retryAfter}s (attempt $attempt/$MaxRetries)..."
                Start-Sleep -Seconds $retryAfter
                continue
            }

            # 409 — conflict (already exists): let caller handle
            if ($status -eq 409) {
                $err = [PSCustomObject]@{ StatusCode = 409; Message = $_.Exception.Message }
                return $err
            }

            # Everything else: surface the error
            $detail = $_.ErrorDetails.Message
            if (-not $detail) { $detail = $_.Exception.Message }
            Write-Err "Fabric API error ($Method $Uri): HTTP $status — $detail"
            throw
        }
    }
}

# ── Pre-flight checks ───────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║   AAP Data Agent POC — Fabric Workspace Provisioning   ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# Check Azure CLI
Write-Info "Checking Azure CLI availability..."
$azPath = Get-Command az -ErrorAction SilentlyContinue
if (-not $azPath) {
    Write-Err "Azure CLI (az) not found. Install from https://aka.ms/installazurecli"
    exit 1
}
Write-Status "Azure CLI found."

# Get token
Write-Info "Authenticating to Fabric API..."
$token = Get-FabricToken
$headers = @{ Authorization = "Bearer $token" }
Write-Status "Authenticated successfully."

# ── Step 1: Workspace ───────────────────────────────────────────────────────

Write-Info "Checking for existing workspace '$WorkspaceName'..."
$filter = [System.Uri]::EscapeDataString("displayName eq '$WorkspaceName'")
$workspaces = Invoke-FabricApi -Method GET -Uri "$FabricBaseUrl/workspaces?`$filter=$filter" -Headers $headers

$workspace = $null
if ($workspaces.value -and $workspaces.value.Count -gt 0) {
    $workspace = $workspaces.value[0]
    Write-Status "Workspace already exists: $($workspace.id)"
}
else {
    if ($PSCmdlet.ShouldProcess($WorkspaceName, "Create Fabric workspace")) {
        Write-Info "Creating workspace '$WorkspaceName' on capacity $CapacityId..."
        $body = @{
            displayName = $WorkspaceName
            capacityId  = $CapacityId
        }
        $workspace = Invoke-FabricApi -Method POST -Uri "$FabricBaseUrl/workspaces" -Headers $headers -Body $body

        if ($workspace.StatusCode -eq 409) {
            Write-Warn "Workspace creation returned 409 (conflict). Fetching existing workspace..."
            $workspaces = Invoke-FabricApi -Method GET -Uri "$FabricBaseUrl/workspaces?`$filter=$filter" -Headers $headers
            $workspace = $workspaces.value[0]
        }
        Write-Status "Workspace ready: $($workspace.id)"
    }
    else {
        Write-Warn "WhatIf: Would create workspace '$WorkspaceName'"
        return
    }
}

$workspaceId = $workspace.id

# ── Step 2: Lakehouse ───────────────────────────────────────────────────────

Write-Info "Checking for existing Lakehouse '$LakehouseName' in workspace..."
$lakehouses = Invoke-FabricApi -Method GET -Uri "$FabricBaseUrl/workspaces/$workspaceId/lakehouses" -Headers $headers

$lakehouse = $null
if ($lakehouses.value) {
    $lakehouse = $lakehouses.value | Where-Object { $_.displayName -eq $LakehouseName } | Select-Object -First 1
}

if ($lakehouse) {
    Write-Status "Lakehouse already exists: $($lakehouse.id)"
}
else {
    if ($PSCmdlet.ShouldProcess($LakehouseName, "Create Lakehouse in workspace $workspaceId")) {
        Write-Info "Creating Lakehouse '$LakehouseName'..."
        $body = @{
            displayName = $LakehouseName
        }
        $lakehouse = Invoke-FabricApi -Method POST -Uri "$FabricBaseUrl/workspaces/$workspaceId/lakehouses" -Headers $headers -Body $body

        if ($lakehouse.StatusCode -eq 409) {
            Write-Warn "Lakehouse creation returned 409 (conflict). Fetching existing..."
            $lakehouses = Invoke-FabricApi -Method GET -Uri "$FabricBaseUrl/workspaces/$workspaceId/lakehouses" -Headers $headers
            $lakehouse = $lakehouses.value | Where-Object { $_.displayName -eq $LakehouseName } | Select-Object -First 1
        }
        Write-Status "Lakehouse ready: $($lakehouse.id)"
    }
    else {
        Write-Warn "WhatIf: Would create Lakehouse '$LakehouseName'"
        return
    }
}

$lakehouseId = $lakehouse.id

# ── Step 3: Get SQL endpoint ────────────────────────────────────────────────

Write-Info "Retrieving Lakehouse SQL endpoint..."
$lhDetail = Invoke-FabricApi -Method GET -Uri "$FabricBaseUrl/workspaces/$workspaceId/lakehouses/$lakehouseId" -Headers $headers

$sqlEndpoint = $null
if ($lhDetail.properties -and $lhDetail.properties.sqlEndpointProperties) {
    $sqlEndpoint = $lhDetail.properties.sqlEndpointProperties.connectionString
}

if (-not $sqlEndpoint) {
    Write-Warn "SQL endpoint not yet available. The Lakehouse may still be provisioning."
    Write-Warn "Re-run this script in a few minutes, or retrieve the endpoint from the Fabric portal."
    $sqlEndpoint = "<pending — check Fabric portal>"
}
else {
    Write-Status "SQL endpoint: $sqlEndpoint"
}

# ── Step 4: Write .env.fabric ───────────────────────────────────────────────

Write-Info "Writing configuration to $EnvFile..."
@"
# Generated by setup-workspace.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Do not commit this file to source control.
FABRIC_WORKSPACE_ID=$workspaceId
FABRIC_WORKSPACE_NAME=$WorkspaceName
FABRIC_LAKEHOUSE_ID=$lakehouseId
FABRIC_LAKEHOUSE_NAME=$LakehouseName
FABRIC_SQL_ENDPOINT=$sqlEndpoint
FABRIC_CAPACITY_ID=$CapacityId
"@ | Set-Content -Path $EnvFile -Encoding UTF8

Write-Status "Configuration saved to $EnvFile"

# ── Summary ─────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                  Provisioning Complete                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Workspace:     $WorkspaceName" -ForegroundColor White
Write-Host "  Workspace ID:  $workspaceId" -ForegroundColor Gray
Write-Host "  Lakehouse:     $LakehouseName" -ForegroundColor White
Write-Host "  Lakehouse ID:  $lakehouseId" -ForegroundColor Gray
Write-Host "  SQL Endpoint:  $sqlEndpoint" -ForegroundColor White
Write-Host "  Config File:   $EnvFile" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Import and run the data generation notebook in the workspace" -ForegroundColor White
Write-Host "  2. Run ./deploy-semantic-views.ps1 to create contract views" -ForegroundColor White
Write-Host ""
