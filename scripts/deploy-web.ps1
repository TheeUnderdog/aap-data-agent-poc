<#
.SYNOPSIS
    Deploy the Advance Insights web app to Azure Static Web Apps.

.DESCRIPTION
    Automates Azure Static Web App creation, Entra ID app registration, managed identity
    setup, and application settings configuration for the AAP Data Agent POC.

    Idempotent: checks if resources exist before creating them.

.PARAMETER ResourceGroup
    Azure resource group name.

.PARAMETER AppName
    Azure Static Web App name (becomes part of the hostname).

.PARAMETER GitHubRepoUrl
    GitHub repository URL (e.g., https://github.com/org/repo).

.PARAMETER Branch
    Git branch to deploy from. Default: main.

.PARAMETER Location
    Azure region. Default: eastus2.

.PARAMETER AadClientId
    (Optional) Existing Entra ID app registration client ID. If omitted, a new one is created.

.PARAMETER AadClientSecret
    (Optional) Existing Entra ID app registration client secret. Required if AadClientId is provided.

.PARAMETER SkipAppRegistration
    Skip Entra ID app registration (use if already configured).

.EXAMPLE
    .\scripts\deploy-web.ps1 -ResourceGroup "aap-poc-rg" -AppName "advance-insights" `
        -GitHubRepoUrl "https://github.com/myorg/aap-data-agent-poc"

.EXAMPLE
    .\scripts\deploy-web.ps1 -ResourceGroup "aap-poc-rg" -AppName "advance-insights" `
        -GitHubRepoUrl "https://github.com/myorg/aap-data-agent-poc" `
        -AadClientId "existing-client-id" -AadClientSecret "existing-secret"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [string]$ResourceGroup,

    [Parameter(Mandatory)]
    [string]$AppName,

    [Parameter(Mandatory)]
    [string]$GitHubRepoUrl,

    [string]$Branch = "main",

    [string]$Location = "eastus2",

    [string]$AadClientId,

    [string]$AadClientSecret,

    [switch]$SkipAppRegistration
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Constants ────────────────────────────────────────────────────────────

$TENANT_ID       = "72f988bf-86f1-41af-91ab-2d7cd011db47"
$FABRIC_WORKSPACE_ID = "82f53636-206f-4825-821b-bdaa8e089893"
$FABRIC_API_BASE = "https://msitapi.fabric.microsoft.com/v1"

# ── Usage Banner ─────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       Advance Insights — SWA Deployment Script               ║" -ForegroundColor Cyan
Write-Host "║       AAP Data Agent POC                                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Resource Group : $ResourceGroup"
Write-Host "  App Name       : $AppName"
Write-Host "  GitHub Repo    : $GitHubRepoUrl"
Write-Host "  Branch         : $Branch"
Write-Host "  Location       : $Location"
Write-Host ""

# ── Prerequisite Checks ─────────────────────────────────────────────────

function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow

    # Azure CLI
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI (az) is not installed. Install from https://aka.ms/installazurecli"
    }

    # Verify logged in
    $account = az account show 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in to Azure CLI. Run 'az login' first."
    }
    $accountInfo = $account | ConvertFrom-Json
    Write-Host "  ✓ Azure CLI logged in as $($accountInfo.user.name)" -ForegroundColor Green

    # GitHub CLI (optional but recommended)
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        Write-Host "  ✓ GitHub CLI (gh) available" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ GitHub CLI (gh) not found — SWA will prompt for GitHub auth interactively" -ForegroundColor DarkYellow
    }

    Write-Host ""
}

# ── Step 1: Create Resource Group (if needed) ───────────────────────────

function New-ResourceGroupIfNeeded {
    Write-Host "Step 1: Resource Group" -ForegroundColor Yellow

    $existing = az group show --name $ResourceGroup 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Resource group '$ResourceGroup' already exists" -ForegroundColor Green
        return
    }

    if ($PSCmdlet.ShouldProcess($ResourceGroup, "Create resource group")) {
        Write-Host "  Creating resource group '$ResourceGroup' in $Location..."
        az group create --name $ResourceGroup --location $Location --output none
        if ($LASTEXITCODE -ne 0) { throw "Failed to create resource group" }
        Write-Host "  ✓ Resource group created" -ForegroundColor Green
    }
}

# ── Step 2: Create Static Web App ───────────────────────────────────────

function New-StaticWebApp {
    Write-Host "Step 2: Static Web App" -ForegroundColor Yellow

    # Check if SWA already exists
    $existing = az staticwebapp show --name $AppName --resource-group $ResourceGroup 2>&1
    if ($LASTEXITCODE -eq 0) {
        $swa = $existing | ConvertFrom-Json
        Write-Host "  ✓ Static Web App '$AppName' already exists" -ForegroundColor Green
        Write-Host "    Hostname: $($swa.defaultHostname)"
        return $swa
    }

    if ($PSCmdlet.ShouldProcess($AppName, "Create Azure Static Web App")) {
        Write-Host "  Creating Static Web App '$AppName'..."
        $result = az staticwebapp create `
            --name $AppName `
            --resource-group $ResourceGroup `
            --source $GitHubRepoUrl `
            --branch $Branch `
            --app-location "web" `
            --api-location "api" `
            --output-location "." `
            --login-with-github `
            --output json 2>&1

        if ($LASTEXITCODE -ne 0) { throw "Failed to create Static Web App: $result" }

        $swa = $result | ConvertFrom-Json
        Write-Host "  ✓ Static Web App created" -ForegroundColor Green
        Write-Host "    Hostname: $($swa.defaultHostname)"
        return $swa
    }
}

# ── Step 3: Entra ID App Registration ───────────────────────────────────

function New-EntraIdAppRegistration {
    param([string]$SwaHostname)

    Write-Host "Step 3: Entra ID App Registration" -ForegroundColor Yellow

    if ($SkipAppRegistration) {
        Write-Host "  ⏭ Skipped (--SkipAppRegistration)" -ForegroundColor DarkYellow
        return @{ ClientId = $AadClientId; ClientSecret = $AadClientSecret }
    }

    if ($AadClientId -and $AadClientSecret) {
        Write-Host "  ✓ Using provided client ID: $AadClientId" -ForegroundColor Green
        return @{ ClientId = $AadClientId; ClientSecret = $AadClientSecret }
    }

    $redirectUri = "https://$SwaHostname/.auth/login/aad/callback"
    $displayName = "Advance Insights"

    # Check if app registration already exists by display name
    $existingApps = az ad app list --display-name $displayName --query "[].{appId:appId, displayName:displayName}" --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        $apps = $existingApps | ConvertFrom-Json
        if ($apps.Count -gt 0) {
            $appId = $apps[0].appId
            Write-Host "  ✓ App registration '$displayName' already exists (Client ID: $appId)" -ForegroundColor Green
            Write-Host "  ⚠ You must provide the client secret manually (cannot retrieve existing secrets)" -ForegroundColor DarkYellow
            Write-Host "    Pass -AadClientId '$appId' -AadClientSecret '<secret>' on next run" -ForegroundColor DarkYellow
            return @{ ClientId = $appId; ClientSecret = $null }
        }
    }

    if ($PSCmdlet.ShouldProcess($displayName, "Create Entra ID app registration")) {
        Write-Host "  Creating app registration '$displayName'..."
        Write-Host "    Redirect URI: $redirectUri"

        # Create the app registration (single tenant)
        $appResult = az ad app create `
            --display-name $displayName `
            --sign-in-audience "AzureADMyOrg" `
            --web-redirect-uris $redirectUri `
            --output json 2>&1

        if ($LASTEXITCODE -ne 0) { throw "Failed to create app registration: $appResult" }

        $app = $appResult | ConvertFrom-Json
        $clientId = $app.appId
        Write-Host "  ✓ App registration created (Client ID: $clientId)" -ForegroundColor Green

        # Create a client secret (valid 2 years)
        Write-Host "  Creating client secret..."
        $secretResult = az ad app credential reset `
            --id $app.id `
            --display-name "SWA Auth Secret" `
            --years 2 `
            --output json 2>&1

        if ($LASTEXITCODE -ne 0) { throw "Failed to create client secret: $secretResult" }

        $secret = ($secretResult | ConvertFrom-Json).password
        Write-Host "  ✓ Client secret created" -ForegroundColor Green

        # Create service principal for the app
        $spResult = az ad sp create --id $clientId 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Service principal created" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Service principal may already exist (non-fatal)" -ForegroundColor DarkYellow
        }

        return @{ ClientId = $clientId; ClientSecret = $secret }
    }
}

# ── Step 4: Configure SWA Application Settings ──────────────────────────

function Set-SwaAppSettings {
    param(
        [string]$ClientId,
        [string]$ClientSecret
    )

    Write-Host "Step 4: Application Settings" -ForegroundColor Yellow

    if (-not $ClientId) {
        Write-Host "  ⚠ No client ID available — skipping settings configuration" -ForegroundColor DarkYellow
        Write-Host "    Configure manually in Azure Portal → Static Web App → Configuration" -ForegroundColor DarkYellow
        return
    }

    $settings = @(
        "FABRIC_WORKSPACE_ID=$FABRIC_WORKSPACE_ID",
        "FABRIC_API_BASE=$FABRIC_API_BASE"
    )

    # Always set the client ID
    $settings += "AAD_CLIENT_ID=$ClientId"

    # Only set secret if we have one
    if ($ClientSecret) {
        $settings += "AAD_CLIENT_SECRET=$ClientSecret"
    }

    if ($PSCmdlet.ShouldProcess($AppName, "Configure application settings")) {
        Write-Host "  Setting application configuration..."

        $settingsArgs = $settings -join " "
        az staticwebapp appsettings set `
            --name $AppName `
            --resource-group $ResourceGroup `
            --setting-names @settings `
            --output none 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠ az staticwebapp appsettings failed — trying individual settings" -ForegroundColor DarkYellow
            foreach ($s in $settings) {
                az staticwebapp appsettings set --name $AppName --resource-group $ResourceGroup --setting-names $s --output none 2>&1
            }
        }

        Write-Host "  ✓ Application settings configured:" -ForegroundColor Green
        Write-Host "    AAD_CLIENT_ID       = $ClientId"
        Write-Host "    AAD_CLIENT_SECRET   = $(if ($ClientSecret) { '(set)' } else { '(not set — add manually)' })"
        Write-Host "    FABRIC_WORKSPACE_ID = $FABRIC_WORKSPACE_ID"
        Write-Host "    FABRIC_API_BASE     = $FABRIC_API_BASE"
    }
}

# ── Step 5: Enable Managed Identity ─────────────────────────────────────

function Enable-ManagedIdentity {
    Write-Host "Step 5: Managed Identity" -ForegroundColor Yellow

    if ($PSCmdlet.ShouldProcess($AppName, "Enable system-assigned managed identity")) {
        # SWA doesn't have a direct CLI command for managed identity; use generic resource update
        $swaResourceId = az staticwebapp show `
            --name $AppName `
            --resource-group $ResourceGroup `
            --query "id" `
            --output tsv 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠ Could not retrieve SWA resource ID" -ForegroundColor DarkYellow
            Write-Host "    Enable managed identity manually: Portal → Static Web App → Identity → System assigned → On" -ForegroundColor DarkYellow
            return
        }

        az resource update `
            --ids $swaResourceId `
            --set "identity.type=SystemAssigned" `
            --output none 2>&1

        if ($LASTEXITCODE -eq 0) {
            # Retrieve the principal ID
            $identity = az staticwebapp show `
                --name $AppName `
                --resource-group $ResourceGroup `
                --query "identity.principalId" `
                --output tsv 2>&1

            Write-Host "  ✓ System-assigned managed identity enabled" -ForegroundColor Green
            if ($identity -and $LASTEXITCODE -eq 0) {
                Write-Host "    Principal ID: $identity"
            }
        } else {
            Write-Host "  ⚠ Could not enable managed identity via CLI" -ForegroundColor DarkYellow
            Write-Host "    Enable manually: Portal → Static Web App → Identity → System assigned → On" -ForegroundColor DarkYellow
        }
    }
}

# ── Main ─────────────────────────────────────────────────────────────────

try {
    Test-Prerequisites
    New-ResourceGroupIfNeeded

    $swa = New-StaticWebApp
    $hostname = if ($swa) { $swa.defaultHostname } else { "$AppName.azurestaticapps.net" }

    $registration = New-EntraIdAppRegistration -SwaHostname $hostname
    Set-SwaAppSettings -ClientId $registration.ClientId -ClientSecret $registration.ClientSecret
    Enable-ManagedIdentity

    # ── Summary & Next Steps ─────────────────────────────────────────────
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅  Deployment Complete                                      ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  App URL: https://$hostname" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ── Manual Steps Required ──" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Grant the managed identity Fabric workspace access:"
    Write-Host "     • Go to https://msit.powerbi.com → Workspace → Manage access"
    Write-Host "     • Add the managed identity (by Object/Principal ID) as Contributor"
    Write-Host ""
    Write-Host "  2. Verify the GitHub Actions deployment workflow ran successfully:"
    Write-Host "     • Check $GitHubRepoUrl/actions"
    Write-Host ""
    if (-not $registration.ClientSecret) {
        Write-Host "  3. Add the AAD_CLIENT_SECRET in Azure Portal:"
        Write-Host "     • Portal → Static Web App → Configuration → Application settings"
        Write-Host ""
    }
    Write-Host "  4. Test the app:"
    Write-Host "     • Visit https://$hostname"
    Write-Host "     • Should redirect to Entra ID login"
    Write-Host "     • After login, the chat interface should load"
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "  ❌ Error: $_" -ForegroundColor Red
    Write-Host "  $($_.ScriptStackTrace)" -ForegroundColor DarkRed
    Write-Host ""
    exit 1
}
