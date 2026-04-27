<#
.SYNOPSIS
    Deploy the Advance Insights web app to Azure Container Apps.

.DESCRIPTION
    Automates Azure Container App creation with managed identity, environment variables,
    and secrets for the AAP Data Agent POC.

    Idempotent: checks if resources exist before creating them.

.PARAMETER ResourceGroup
    Azure resource group name. Default: aap-poc-rg

.PARAMETER AppName
    Container App name (becomes part of the FQDN). Default: aap-loyalty-intelligence

.PARAMETER EnvName
    Container App Environment name. Default: aap-app-env

.PARAMETER Location
    Azure region. Default: eastus2

.PARAMETER ImageTag
    Container image tag to deploy. Default: latest

.PARAMETER EntraClientId
    Entra ID app registration client ID (for MSAL auth).

.PARAMETER EntraClientSecret
    Entra ID app registration client secret.

.PARAMETER SubscriptionId
    Azure subscription ID. Default: 629e646d-3923-4838-8f3e-cbee6c72734c

.EXAMPLE
    .\scripts\deploy-web.ps1

.EXAMPLE
    .\scripts\deploy-web.ps1 -EntraClientId "your-client-id" -EntraClientSecret "your-secret"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ResourceGroup = "aap-poc-rg",
    [string]$AppName = "aap-loyalty-intelligence",
    [string]$EnvName = "aap-app-env",
    [string]$Location = "eastus2",
    [string]$ImageTag = "latest",
    [string]$EntraClientId,
    [string]$EntraClientSecret,
    [string]$SubscriptionId = "629e646d-3923-4838-8f3e-cbee6c72734c"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Constants ────────────────────────────────────────────────────────────

$TENANT_ID           = "16b3c013-d300-468d-ac64-7eda0820b6d3"
$FABRIC_WORKSPACE_ID = "e7f4acfe-90d7-4685-864a-b5f1216fe614"
$FABRIC_API_BASE     = "https://api.fabric.microsoft.com/v1"

# ── Banner ───────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       Advance Insights — Container Apps Deployment           ║" -ForegroundColor Cyan
Write-Host "║       AAP Data Agent POC                                     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Resource Group : $ResourceGroup"
Write-Host "  App Name       : $AppName"
Write-Host "  Environment    : $EnvName"
Write-Host "  Location       : $Location"
Write-Host "  Subscription   : $SubscriptionId"
Write-Host ""

# ── Prerequisite Checks ─────────────────────────────────────────────────

function Test-Prerequisites {
    Write-Host "Checking prerequisites..." -ForegroundColor Yellow

    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI (az) is not installed. Install from https://aka.ms/installazurecli"
    }

    $account = az account show 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in to Azure CLI. Run 'az login' first."
    }
    $accountInfo = $account | ConvertFrom-Json
    Write-Host "  ✓ Azure CLI logged in as $($accountInfo.user.name)" -ForegroundColor Green

    # Set subscription
    az account set --subscription $SubscriptionId 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set subscription $SubscriptionId"
    }
    Write-Host "  ✓ Subscription set to $SubscriptionId" -ForegroundColor Green
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

# ── Step 2: Create Container App Environment ────────────────────────────

function New-ContainerAppEnvironment {
    Write-Host "Step 2: Container App Environment" -ForegroundColor Yellow

    $existing = az containerapp env show --name $EnvName --resource-group $ResourceGroup 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Environment '$EnvName' already exists" -ForegroundColor Green
        return
    }

    if ($PSCmdlet.ShouldProcess($EnvName, "Create Container App Environment")) {
        Write-Host "  Creating Container App Environment '$EnvName'..."
        az containerapp env create `
            --name $EnvName `
            --resource-group $ResourceGroup `
            --location $Location `
            --output none
        if ($LASTEXITCODE -ne 0) { throw "Failed to create Container App Environment" }
        Write-Host "  ✓ Container App Environment created" -ForegroundColor Green
    }
}

# ── Step 3: Create Container App ────────────────────────────────────────

function New-ContainerApp {
    Write-Host "Step 3: Container App" -ForegroundColor Yellow

    $existing = az containerapp show --name $AppName --resource-group $ResourceGroup 2>&1
    if ($LASTEXITCODE -eq 0) {
        $app = $existing | ConvertFrom-Json
        Write-Host "  ✓ Container App '$AppName' already exists" -ForegroundColor Green
        $fqdn = $app.properties.configuration.ingress.fqdn
        if ($fqdn) { Write-Host "    FQDN: $fqdn" }
        return
    }

    if ($PSCmdlet.ShouldProcess($AppName, "Create Container App")) {
        Write-Host "  Creating Container App '$AppName'..."

        # Build env vars list
        $envVars = @(
            "FABRIC_WORKSPACE_ID=$FABRIC_WORKSPACE_ID",
            "FABRIC_API_BASE=$FABRIC_API_BASE",
            "ENTRA_TENANT_ID=$TENANT_ID"
        )
        if ($EntraClientId) {
            $envVars += "ENTRA_CLIENT_ID=$EntraClientId"
        }

        az containerapp create `
            --name $AppName `
            --resource-group $ResourceGroup `
            --environment $EnvName `
            --image "mcr.microsoft.com/azurelinux/base/python:3.11" `
            --target-port 8000 `
            --ingress external `
            --system-assigned `
            --cpu 0.5 `
            --memory 1Gi `
            --min-replicas 1 `
            --max-replicas 10 `
            --env-vars @envVars `
            --output none

        if ($LASTEXITCODE -ne 0) { throw "Failed to create Container App" }

        $fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" --output tsv
        Write-Host "  ✓ Container App created" -ForegroundColor Green
        if ($fqdn) { Write-Host "    FQDN: $fqdn" }
    }
}

# ── Step 4: Configure Secrets ───────────────────────────────────────────

function Set-ContainerAppSecrets {
    Write-Host "Step 4: Secrets" -ForegroundColor Yellow

    if ($EntraClientSecret) {
        if ($PSCmdlet.ShouldProcess($AppName, "Set ENTRA_CLIENT_SECRET")) {
            az containerapp secret set `
                --name $AppName `
                --resource-group $ResourceGroup `
                --secrets "entra-client-secret=$EntraClientSecret" `
                --output none 2>&1

            if ($LASTEXITCODE -eq 0) {
                # Link secret to env var
                az containerapp update `
                    --name $AppName `
                    --resource-group $ResourceGroup `
                    --set-env-vars "ENTRA_CLIENT_SECRET=secretref:entra-client-secret" `
                    --output none 2>&1

                Write-Host "  ✓ ENTRA_CLIENT_SECRET configured" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Failed to set secret (non-fatal)" -ForegroundColor DarkYellow
            }
        }
    } else {
        Write-Host "  ⏭ No client secret provided — set it later with:" -ForegroundColor DarkYellow
        Write-Host "    az containerapp secret set --name $AppName --resource-group $ResourceGroup --secrets entra-client-secret=YOUR_SECRET"
    }
}

# ── Step 5: Display Managed Identity Info ───────────────────────────────

function Show-ManagedIdentity {
    Write-Host "Step 5: Managed Identity" -ForegroundColor Yellow

    $principalId = az containerapp identity show `
        --name $AppName `
        --resource-group $ResourceGroup `
        --query "principalId" `
        --output tsv 2>&1

    if ($LASTEXITCODE -eq 0 -and $principalId) {
        Write-Host "  ✓ System-assigned managed identity enabled" -ForegroundColor Green
        Write-Host "    Principal ID: $principalId"
    } else {
        Write-Host "  ⚠ Could not retrieve managed identity" -ForegroundColor DarkYellow
    }
}

# ── Main ─────────────────────────────────────────────────────────────────

try {
    Test-Prerequisites
    New-ResourceGroupIfNeeded
    New-ContainerAppEnvironment
    New-ContainerApp
    Set-ContainerAppSecrets
    Show-ManagedIdentity

    # ── Summary ──────────────────────────────────────────────────────────
    $fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" --output tsv 2>&1
    if ($LASTEXITCODE -ne 0) { $fqdn = "$AppName.azurecontainerapps.io" }

    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅  Deployment Complete                                      ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "  App URL: https://$fqdn" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ── Manual Steps Required ──" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Build & push the Docker image (or let GitHub Actions do it):"
    Write-Host "     docker build -t ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest ./web"
    Write-Host "     docker push ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest"
    Write-Host ""
    Write-Host "  2. Update the Container App image:"
    Write-Host "     az containerapp update --name $AppName --resource-group $ResourceGroup --image ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest"
    Write-Host ""
    Write-Host "  3. Grant the managed identity Fabric workspace access:"
    Write-Host "     • Go to https://msit.powerbi.com → Workspace → Manage access"
    Write-Host "     • Add the managed identity (by Principal ID) as Contributor"
    Write-Host ""
    Write-Host "  4. Create Entra ID app registration (if not already done):"
    Write-Host "     • Set redirect URI to: https://$fqdn/auth/callback"
    Write-Host "     • Set ENTRA_CLIENT_ID and ENTRA_CLIENT_SECRET env vars"
    Write-Host ""
    Write-Host "  5. Test the app: visit https://$fqdn"
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "  ❌ Error: $_" -ForegroundColor Red
    Write-Host "  $($_.ScriptStackTrace)" -ForegroundColor DarkRed
    Write-Host ""
    exit 1
}
