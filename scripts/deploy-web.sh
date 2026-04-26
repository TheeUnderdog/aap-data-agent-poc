#!/usr/bin/env bash
#
# deploy-web.sh — Deploy Advance Insights to Azure Static Web Apps
# Bash equivalent of deploy-web.ps1 for macOS/Linux users.
#
# Usage:
#   ./scripts/deploy-web.sh \
#     --resource-group aap-poc-rg \
#     --app-name advance-insights \
#     --repo https://github.com/myorg/aap-data-agent-poc
#
# Optional flags:
#   --branch main               (default: main)
#   --location eastus2          (default: eastus2)
#   --client-id <id>            (skip app registration creation)
#   --client-secret <secret>    (required if --client-id provided)
#   --skip-app-registration     (skip Entra ID app registration entirely)
#   --dry-run                   (print commands without executing)
#

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────

TENANT_ID="72f988bf-86f1-41af-91ab-2d7cd011db47"
FABRIC_WORKSPACE_ID="82f53636-206f-4825-821b-bdaa8e089893"
FABRIC_API_BASE="https://msitapi.fabric.microsoft.com/v1"

# ── Defaults ─────────────────────────────────────────────────────────────

BRANCH="main"
LOCATION="eastus2"
CLIENT_ID=""
CLIENT_SECRET=""
SKIP_APP_REG=false
DRY_RUN=false
RESOURCE_GROUP=""
APP_NAME=""
REPO_URL=""

# ── Parse Arguments ──────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group)  RESOURCE_GROUP="$2"; shift 2 ;;
        --app-name)        APP_NAME="$2"; shift 2 ;;
        --repo)            REPO_URL="$2"; shift 2 ;;
        --branch)          BRANCH="$2"; shift 2 ;;
        --location)        LOCATION="$2"; shift 2 ;;
        --client-id)       CLIENT_ID="$2"; shift 2 ;;
        --client-secret)   CLIENT_SECRET="$2"; shift 2 ;;
        --skip-app-registration) SKIP_APP_REG=true; shift ;;
        --dry-run)         DRY_RUN=true; shift ;;
        -h|--help)
            echo "Usage: $0 --resource-group RG --app-name NAME --repo GITHUB_URL [options]"
            echo ""
            echo "Options:"
            echo "  --branch BRANCH            Git branch (default: main)"
            echo "  --location LOCATION        Azure region (default: eastus2)"
            echo "  --client-id ID             Existing Entra ID client ID"
            echo "  --client-secret SECRET     Existing Entra ID client secret"
            echo "  --skip-app-registration    Skip Entra ID app registration"
            echo "  --dry-run                  Print commands without executing"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Validation ───────────────────────────────────────────────────────────

if [[ -z "$RESOURCE_GROUP" || -z "$APP_NAME" || -z "$REPO_URL" ]]; then
    echo "❌ Required: --resource-group, --app-name, --repo"
    echo "Run $0 --help for usage."
    exit 1
fi

# ── Helpers ──────────────────────────────────────────────────────────────

info()  { echo -e "\033[33m$1\033[0m"; }
ok()    { echo -e "\033[32m  ✓ $1\033[0m"; }
warn()  { echo -e "\033[33m  ⚠ $1\033[0m"; }
fail()  { echo -e "\033[31m  ❌ $1\033[0m"; exit 1; }

run_cmd() {
    if $DRY_RUN; then
        echo "  [dry-run] $*"
    else
        "$@"
    fi
}

# ── Banner ───────────────────────────────────────────────────────────────

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║       Advance Insights — SWA Deployment Script               ║"
echo "║       AAP Data Agent POC                                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Resource Group : $RESOURCE_GROUP"
echo "  App Name       : $APP_NAME"
echo "  GitHub Repo    : $REPO_URL"
echo "  Branch         : $BRANCH"
echo "  Location       : $LOCATION"
echo ""

# ── Prerequisites ────────────────────────────────────────────────────────

info "Checking prerequisites..."

command -v az >/dev/null 2>&1 || fail "Azure CLI (az) not installed. See https://aka.ms/installazurecli"

if az account show >/dev/null 2>&1; then
    ACCOUNT_NAME=$(az account show --query "user.name" -o tsv)
    ok "Azure CLI logged in as $ACCOUNT_NAME"
else
    fail "Not logged in to Azure CLI. Run 'az login' first."
fi

if command -v gh >/dev/null 2>&1; then
    ok "GitHub CLI (gh) available"
else
    warn "GitHub CLI (gh) not found — SWA will prompt for GitHub auth interactively"
fi
echo ""

# ── Step 1: Resource Group ───────────────────────────────────────────────

info "Step 1: Resource Group"

if az group show --name "$RESOURCE_GROUP" >/dev/null 2>&1; then
    ok "Resource group '$RESOURCE_GROUP' already exists"
else
    echo "  Creating resource group '$RESOURCE_GROUP' in $LOCATION..."
    run_cmd az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
    ok "Resource group created"
fi

# ── Step 2: Static Web App ──────────────────────────────────────────────

info "Step 2: Static Web App"

if az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    SWA_HOSTNAME=$(az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "defaultHostname" -o tsv)
    ok "Static Web App '$APP_NAME' already exists"
    echo "    Hostname: $SWA_HOSTNAME"
else
    echo "  Creating Static Web App '$APP_NAME'..."
    run_cmd az staticwebapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --source "$REPO_URL" \
        --branch "$BRANCH" \
        --app-location "web" \
        --api-location "api" \
        --output-location "" \
        --login-with-github \
        --output none

    SWA_HOSTNAME=$(az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "defaultHostname" -o tsv 2>/dev/null || echo "$APP_NAME.azurestaticapps.net")
    ok "Static Web App created"
    echo "    Hostname: $SWA_HOSTNAME"
fi

# ── Step 3: Entra ID App Registration ───────────────────────────────────

info "Step 3: Entra ID App Registration"

if $SKIP_APP_REG; then
    warn "Skipped (--skip-app-registration)"
elif [[ -n "$CLIENT_ID" && -n "$CLIENT_SECRET" ]]; then
    ok "Using provided client ID: $CLIENT_ID"
else
    REDIRECT_URI="https://$SWA_HOSTNAME/.auth/login/aad/callback"
    DISPLAY_NAME="Advance Insights"

    EXISTING=$(az ad app list --display-name "$DISPLAY_NAME" --query "[0].appId" -o tsv 2>/dev/null || echo "")
    if [[ -n "$EXISTING" ]]; then
        CLIENT_ID="$EXISTING"
        ok "App registration '$DISPLAY_NAME' already exists (Client ID: $CLIENT_ID)"
        warn "Provide client secret manually with --client-secret"
    else
        echo "  Creating app registration '$DISPLAY_NAME'..."
        echo "    Redirect URI: $REDIRECT_URI"

        APP_JSON=$(run_cmd az ad app create \
            --display-name "$DISPLAY_NAME" \
            --sign-in-audience "AzureADMyOrg" \
            --web-redirect-uris "$REDIRECT_URI" \
            --output json)

        CLIENT_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['appId'])" 2>/dev/null || echo "")
        APP_OBJECT_ID=$(echo "$APP_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
        ok "App registration created (Client ID: $CLIENT_ID)"

        echo "  Creating client secret..."
        SECRET_JSON=$(run_cmd az ad app credential reset \
            --id "$APP_OBJECT_ID" \
            --display-name "SWA Auth Secret" \
            --years 2 \
            --output json)
        CLIENT_SECRET=$(echo "$SECRET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])" 2>/dev/null || echo "")
        ok "Client secret created"

        run_cmd az ad sp create --id "$CLIENT_ID" --output none 2>/dev/null || true
        ok "Service principal created"
    fi
fi

# ── Step 4: Application Settings ────────────────────────────────────────

info "Step 4: Application Settings"

if [[ -n "$CLIENT_ID" ]]; then
    SETTINGS=("FABRIC_WORKSPACE_ID=$FABRIC_WORKSPACE_ID" "FABRIC_API_BASE=$FABRIC_API_BASE" "AAD_CLIENT_ID=$CLIENT_ID")
    [[ -n "$CLIENT_SECRET" ]] && SETTINGS+=("AAD_CLIENT_SECRET=$CLIENT_SECRET")

    echo "  Setting application configuration..."
    run_cmd az staticwebapp appsettings set \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --setting-names "${SETTINGS[@]}" \
        --output none

    ok "Application settings configured"
    echo "    AAD_CLIENT_ID       = $CLIENT_ID"
    echo "    AAD_CLIENT_SECRET   = $(if [[ -n "$CLIENT_SECRET" ]]; then echo '(set)'; else echo '(not set)'; fi)"
    echo "    FABRIC_WORKSPACE_ID = $FABRIC_WORKSPACE_ID"
    echo "    FABRIC_API_BASE     = $FABRIC_API_BASE"
else
    warn "No client ID available — configure settings manually in Azure Portal"
fi

# ── Step 5: Managed Identity ────────────────────────────────────────────

info "Step 5: Managed Identity"

SWA_RESOURCE_ID=$(az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "id" -o tsv 2>/dev/null || echo "")

if [[ -n "$SWA_RESOURCE_ID" ]]; then
    run_cmd az resource update --ids "$SWA_RESOURCE_ID" --set "identity.type=SystemAssigned" --output none 2>/dev/null

    PRINCIPAL_ID=$(az staticwebapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "identity.principalId" -o tsv 2>/dev/null || echo "")
    ok "System-assigned managed identity enabled"
    [[ -n "$PRINCIPAL_ID" ]] && echo "    Principal ID: $PRINCIPAL_ID"
else
    warn "Could not enable managed identity — do it manually in Azure Portal"
fi

# ── Summary ──────────────────────────────────────────────────────────────

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅  Deployment Complete                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  App URL: https://$SWA_HOSTNAME"
echo ""
echo "  ── Manual Steps Required ──"
echo ""
echo "  1. Grant managed identity Fabric workspace access:"
echo "     • https://msit.powerbi.com → Workspace → Manage access"
echo "     • Add the managed identity (by Principal ID) as Contributor"
echo ""
echo "  2. Verify GitHub Actions deployment: $REPO_URL/actions"
echo ""
if [[ -z "$CLIENT_SECRET" ]]; then
    echo "  3. Add AAD_CLIENT_SECRET in Azure Portal:"
    echo "     • Portal → Static Web App → Configuration → Application settings"
    echo ""
fi
echo "  4. Test: visit https://$SWA_HOSTNAME"
echo ""
