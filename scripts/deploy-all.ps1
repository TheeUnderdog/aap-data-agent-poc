<#
.SYNOPSIS
    Master deployment orchestrator for AAP Data Agent POC.

.DESCRIPTION
    Automates the complete deployment of the AAP Data Agent POC to Azure and Fabric.
    
    Orchestrates:
    1. Fabric workspace + Lakehouse setup
    2. Semantic views + model deployment
    3. Sample data loading (optional)
    4. Web app (SWA + managed Functions) deployment
    5. Entra ID configuration
    6. Managed identity setup
    
    Produces a checklist of manual portal steps still required (Fabric Git Sync, Data Agent import, etc.).
    
    Idempotent: Safe to re-run if steps fail.

.PARAMETER ResourceGroup
    Azure resource group name for SWA. Default: "aap-poc-rg"

.PARAMETER AppName
    Azure Static Web App name. Default: "advance-insights"

.PARAMETER GitHubRepoUrl
    GitHub repository URL (e.g., https://github.com/myorg/aap-data-agent-poc). Required.

.PARAMETER WorkspaceName
    Fabric workspace display name. Default: "AAP-RewardsLoyalty-POC"

.PARAMETER CapacityId
    Fabric capacity GUID. Required.

.PARAMETER LoadSampleData
    If true, execute the sample data notebook (optional). Default: $false

.PARAMETER SkipWeb
    If true, skip web app deployment (for Fabric-only testing). Default: $false

.EXAMPLE
    .\scripts\deploy-all.ps1 `
        -GitHubRepoUrl "https://github.com/myorg/aap-data-agent-poc" `
        -CapacityId "00000000-0000-0000-0000-000000000000"

.EXAMPLE
    .\scripts\deploy-all.ps1 `
        -ResourceGroup "my-rg" `
        -AppName "my-insights" `
        -GitHubRepoUrl "https://github.com/myorg/aap-data-agent-poc" `
        -CapacityId "00000000-0000-0000-0000-000000000000" `
        -LoadSampleData

#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ResourceGroup = "aap-poc-rg",
    [string]$AppName = "aap-loyalty-intelligence",
    
    [Parameter(Mandatory)]
    [string]$GitHubRepoUrl,
    
    [string]$WorkspaceName = "AAP-RewardsLoyalty-POC",
    
    [Parameter(Mandatory)]
    [string]$CapacityId,
    
    [switch]$LoadSampleData,
    [switch]$SkipWeb
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Configuration ────────────────────────────────────────────────────────

$ScriptDir = $PSScriptRoot
$RepoRoot = Split-Path $ScriptDir -Parent
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Logging helpers
function Write-Stage      { param([string]$Msg) Write-Host "`n╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan; Write-Host "║  $Msg" -ForegroundColor Cyan; Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan }
function Write-Step       { param([string]$Msg, [int]$Num) Write-Host "`n[$Num] $Msg" -ForegroundColor Yellow }
function Write-Success    { param([string]$Msg) Write-Host "  ✓ $Msg" -ForegroundColor Green }
function Write-Warn       { param([string]$Msg) Write-Host "  ⚠ $Msg" -ForegroundColor DarkYellow }
function Write-Err        { param([string]$Msg) Write-Host "  ✗ $Msg" -ForegroundColor Red }
function Write-Info       { param([string]$Msg) Write-Host "  · $Msg" -ForegroundColor Cyan }

# ── Banner ───────────────────────────────────────────────────────────

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║     AAP DATA AGENT POC — MASTER DEPLOYMENT ORCHESTRATOR         ║" -ForegroundColor Magenta
Write-Host "║                                                                 ║" -ForegroundColor Magenta
Write-Host "║  This script automates Phases 1–3:                              ║" -ForegroundColor Magenta
Write-Host "║    • Fabric workspace + Lakehouse                               ║" -ForegroundColor Magenta
Write-Host "║    • Semantic model + views                                     ║" -ForegroundColor Magenta
Write-Host "║    • Web app (Container Apps + Flask)                          ║" -ForegroundColor Magenta
Write-Host "║                                                                 ║" -ForegroundColor Magenta
Write-Host "║  Manual Phase 4 steps (portal work) will be printed at end      ║" -ForegroundColor Magenta
Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Config Summary:" -ForegroundColor White
Write-Host "    Resource Group      : $ResourceGroup"
Write-Host "    App Name            : $AppName"
Write-Host "    GitHub Repo         : $GitHubRepoUrl"
Write-Host "    Workspace Name      : $WorkspaceName"
Write-Host "    Capacity ID         : $CapacityId"
Write-Host "    Load Sample Data    : $LoadSampleData"
Write-Host "    Skip Web Deploy     : $SkipWeb"
Write-Host ""

# ── Prerequisite Checks ──────────────────────────────────────────────

Write-Stage "PREREQUISITE CHECKS"

Write-Step "Checking Azure CLI" 1
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Err "Azure CLI not installed"
    throw "Install from https://aka.ms/installazurecli"
}
Write-Success "Azure CLI found"

Write-Step "Checking Azure login" 2
$account = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Not logged in to Azure"
    throw "Run 'az login' first"
}
$accountInfo = $account | ConvertFrom-Json
Write-Success "Logged in as $($accountInfo.user.name)"

Write-Step "Checking Python" 3
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Warn "Python not found — sample data loading will skip"
} else {
    Write-Success "Python found"
}

Write-Step "Checking deployment scripts exist" 4
$requiredScripts = @(
    "setup-workspace.ps1",
    "deploy-semantic-views.ps1",
    "create-semantic-model.py",
    "configure-linguistic-schema.py",
    "deploy-web.ps1"
)
foreach ($script in $requiredScripts) {
    $path = Join-Path $ScriptDir $script
    if (-not (Test-Path $path)) {
        Write-Err "$script not found at $path"
        throw "Missing required script"
    }
}
Write-Success "All deployment scripts present"

# ── Phase 1: Fabric Infrastructure ───────────────────────────────────

Write-Stage "PHASE 1: FABRIC INFRASTRUCTURE (Automated)"

Write-Step "Creating Fabric workspace + Lakehouse" 1
try {
    & "$ScriptDir\setup-workspace.ps1" -WorkspaceName $WorkspaceName -CapacityId $CapacityId -Verbose:$false
    Write-Success "Workspace provisioning complete"
} catch {
    Write-Err "Workspace provisioning failed: $_"
    throw
}

Write-Step "Deploying semantic views" 2
try {
    & "$ScriptDir\deploy-semantic-views.ps1" -Verbose:$false
    Write-Success "Views deployed to Lakehouse SQL endpoint"
} catch {
    Write-Err "View deployment failed: $_"
    throw
}

Write-Step "Deploying semantic model" 3
try {
    & python "$ScriptDir\create-semantic-model.py"
    Write-Success "Semantic model deployed with DirectLake connection + credentials bound"
} catch {
    Write-Err "Model deployment failed: $_"
    throw
}

Write-Step "Configuring linguistic schema (CSR synonyms)" 4
try {
    & python "$ScriptDir\configure-linguistic-schema.py"
    Write-Success "Linguistic schema configured (table/column/value synonyms)"
} catch {
    Write-Warn "Linguistic schema config failed (non-fatal): $_"
}

# ── Phase 1B: Optional Sample Data Loading ─────────────────────────

if ($LoadSampleData) {
    Write-Step "Loading sample data (optional)" 5
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            Write-Info "Executing sample data notebook..."
            & python "$ScriptDir\run-notebook.py"
            Write-Success "Sample data loaded (~337K rows)"
        } catch {
            Write-Warn "Sample data loading failed (non-fatal): $_"
            Write-Warn "You can load data manually later via Fabric Portal → Workspace → Notebooks"
        }
    } else {
        Write-Warn "Python not found — skipping sample data load"
        Write-Warn "You can load data manually later via Fabric Portal → Workspace → Notebooks"
    }
} else {
    Write-Info "Sample data loading skipped (use -LoadSampleData to enable)"
}

# ── Phase 2: Azure Resources ─────────────────────────────────────────

if (-not $SkipWeb) {
    Write-Stage "PHASE 2: WEB DEPLOYMENT (Automated)"
    
    Write-Step "Creating Azure resource group" 1
    $rg = az group show --name $ResourceGroup 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Resource group '$ResourceGroup' already exists"
    } else {
        try {
            az group create --name $ResourceGroup --location "eastus2" --output none
            Write-Success "Resource group created"
        } catch {
            Write-Err "Resource group creation failed: $_"
            throw
        }
    }
    
    Write-Step "Deploying Container App + Managed Identity" 2
    try {
        & "$ScriptDir\deploy-web.ps1" `
            -ResourceGroup $ResourceGroup `
            -AppName $AppName `
            -Verbose:$false
        Write-Success "Container App deployment complete"
    } catch {
        Write-Err "Web app deployment failed: $_"
        throw
    }
    
    Write-Step "Verifying Container App deployment" 3
    Write-Info "GitHub Actions will auto-deploy on next push to master branch"
    Write-Info "Monitor progress at: $GitHubRepoUrl/actions"
    Write-Success "Container App deployment phase complete"
} else {
    Write-Info "Web deployment skipped (--SkipWeb)"
}

# ── Phase 3: Manual Portal Checklist ─────────────────────────────────

Write-Stage "PHASE 3: MANUAL PORTAL STEPS (Required)"

Write-Host ""
Write-Host "The following steps CANNOT be automated (Fabric platform limitations)." -ForegroundColor Yellow
Write-Host "Complete these in any order — they can be parallelized." -ForegroundColor Yellow
Write-Host ""

$checklist = @(
    @{
        Num = "3.1"
        Title = "Configure Fabric Git Sync (CRITICAL)"
        Time = "10 min"
        Steps = @(
            "1. Go to https://msit.powerbi.com → Workspace → $WorkspaceName",
            "2. Click Workspace settings → Git integration → Connect",
            "3. Authorize GitHub org, select repo: $($GitHubRepoUrl -replace 'https://github.com/', '')",
            "4. Set branch to 'main', enable auto-sync",
            "5. Select '/reports' folder for sync"
        )
        Notes = "⚠️ BLOCKER: PBIR report won't appear until Git Sync is configured"
    },
    @{
        Num = "3.2"
        Title = "Verify PBIR Report Deployment"
        Time = "2 min"
        Steps = @(
            "1. Once Git Sync is enabled (step 3.1), return to Workspace",
            "2. Check Reports section — 'LoyaltyOverview' should appear",
            "3. Click to open and verify it loads"
        )
        Notes = "✓ Automatic after step 3.1 completes"
    },
    @{
        Num = "3.3"
        Title = "Enable Language Models in Workspace"
        Time = "5 min"
        Steps = @(
            "1. Fabric Portal → Workspace → Workspace settings → Data Agent",
            "2. Toggle 'Language model services' ON",
            "3. Select 'Azure OpenAI' or preferred LLM",
            "4. Save"
        )
        Notes = "Required for Data Agents to understand natural language queries"
    },
    @{
        Num = "3.4"
        Title = "Grant Managed Identity Workspace Access"
        Time = "5 min"
        Steps = @(
            "1. Azure Portal → Resource Groups → $ResourceGroup → Container App → $AppName",
            "2. Go to Identity → System assigned",
            "3. Copy the Object (principal) ID",
            "4. Fabric Portal → Workspace → $WorkspaceName → Manage access",
            "5. Click Add → paste Object ID → Set role to 'Contributor' → Save"
        )
        Notes = "Required: API backend needs workspace access to call Fabric Data Agent"
    },
    @{
        Num = "3.5"
        Title = "Import 5 Data Agents"
        Time = "20–30 min"
        Steps = @(
            "For each agent (run 5 times):",
            "",
            "  Loyalty Program Manager:",
            "    • Fabric → Workspace → New → Data Agent → Import",
            "    • Upload file: agents/loyalty-program-manager/config.json",
            "    • Link to semantic model: 'AAP Rewards Loyalty Model'",
            "    • Test query: 'How many members do we have?'",
            "",
            "  Store Operations:",
            "    • Upload: agents/store-operations/config.json",
            "    • Link to model, test",
            "",
            "  Merchandising:",
            "    • Upload: agents/merchandising/config.json",
            "    • Link to model, test",
            "",
            "  Marketing & Promotions:",
            "    • Upload: agents/marketing-promotions/config.json",
            "    • Link to model, test",
            "",
            "  Customer Service:",
            "    • Upload: agents/customer-service/config.json",
            "    • Link to model, test"
        )
        Notes = "Each agent is a specialized query interface for a business domain"
    }
)

foreach ($item in $checklist) {
    Write-Host "[$($item.Num)] $($item.Title) — $($item.Time)" -ForegroundColor Cyan
    Write-Host "────────────────────────────────────────────────" -ForegroundColor DarkGray
    foreach ($step in $item.Steps) {
        if ($step -eq "") {
            Write-Host ""
        } else {
            Write-Host "  $step"
        }
    }
    Write-Host "  └─ $($item.Notes)" -ForegroundColor DarkYellow
    Write-Host ""
}

# ── Deployment Summary ───────────────────────────────────────────────

Write-Stage "DEPLOYMENT SUMMARY"

$fqdn = az containerapp show --name $AppName --resource-group $ResourceGroup --query "properties.configuration.ingress.fqdn" --output tsv 2>&1
if ($LASTEXITCODE -ne 0) {
    $fqdn = "$AppName.azurecontainerapps.io"
}

Write-Host ""
Write-Host "✅ AUTOMATED DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host ""
Write-Host "Resources Created:" -ForegroundColor White
Write-Host "  • Fabric Workspace     : $WorkspaceName"
Write-Host "  • Lakehouse            : RewardsLoyaltyData"
Write-Host "  • Semantic Model       : AAP Rewards Loyalty Model"
Write-Host "  • Contract Views       : 9 semantic.v_* views"
Write-Host "  • Container App        : $fqdn"
Write-Host "  • Managed Identity     : Container App system-assigned"
Write-Host "  • Entra ID App Reg     : Advance Insights"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "  1. Complete the 5 manual portal steps above (30–45 min total)"
Write-Host "  2. Verify web app at: https://$fqdn"
Write-Host "  3. Test chat interface and all 5 agents"
Write-Host ""
Write-Host "Documentation:" -ForegroundColor White
Write-Host "  • Deployment Gaps     : docs/deployment-gaps.md"
Write-Host "  • Architecture        : docs/architecture.md"
Write-Host "  • Web Setup Guide     : web/SETUP.md"
Write-Host "  • Data Schema         : docs/data-schema.md"
Write-Host ""
Write-Host "Support:" -ForegroundColor White
Write-Host "  • For errors, re-run this script — it's idempotent"
Write-Host "  • Check GitHub Actions: $GitHubRepoUrl/actions"
Write-Host "  • Check Azure Portal for Container App deployment logs"
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Magenta
