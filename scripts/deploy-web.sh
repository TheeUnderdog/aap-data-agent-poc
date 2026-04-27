#!/usr/bin/env bash
#
# deploy-web.sh — Deploy Advance Insights to Azure Container Apps
# Bash equivalent of deploy-web.ps1 for macOS/Linux users.
#
# Usage:
#   ./scripts/deploy-web.sh
#
# Optional flags:
#   --resource-group RG          (default: aap-poc-rg)
#   --app-name NAME              (default: aap-loyalty-intelligence)
#   --env-name NAME              (default: aap-app-env)
#   --location LOCATION          (default: eastus2)
#   --subscription ID            (default: 629e646d-3923-4838-8f3e-cbee6c72734c)
#   --client-id ID               (Entra ID app client ID)
#   --client-secret SECRET       (Entra ID app client secret)
#   --dry-run                    (print commands without executing)
#

set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────

TENANT_ID="16b3c013-d300-468d-ac64-7eda0820b6d3"
FABRIC_WORKSPACE_ID="e7f4acfe-90d7-4685-864a-b5f1216fe614"
FABRIC_API_BASE="https://api.fabric.microsoft.com/v1"

# ── Defaults ─────────────────────────────────────────────────────────────

RESOURCE_GROUP="aap-poc-rg"
APP_NAME="aap-loyalty-intelligence"
ENV_NAME="aap-app-env"
LOCATION="eastus2"
SUBSCRIPTION="629e646d-3923-4838-8f3e-cbee6c72734c"
CLIENT_ID=""
CLIENT_SECRET=""
DRY_RUN=false

# ── Parse Arguments ──────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group)  RESOURCE_GROUP="$2"; shift 2 ;;
        --app-name)        APP_NAME="$2"; shift 2 ;;
        --env-name)        ENV_NAME="$2"; shift 2 ;;
        --location)        LOCATION="$2"; shift 2 ;;
        --subscription)    SUBSCRIPTION="$2"; shift 2 ;;
        --client-id)       CLIENT_ID="$2"; shift 2 ;;
        --client-secret)   CLIENT_SECRET="$2"; shift 2 ;;
        --dry-run)         DRY_RUN=true; shift ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --resource-group RG       Azure resource group (default: aap-poc-rg)"
            echo "  --app-name NAME           Container App name (default: aap-loyalty-intelligence)"
            echo "  --env-name NAME           Container App env (default: aap-app-env)"
            echo "  --location LOCATION       Azure region (default: eastus2)"
            echo "  --subscription ID         Azure subscription ID"
            echo "  --client-id ID            Entra ID app client ID"
            echo "  --client-secret SECRET    Entra ID app client secret"
            echo "  --dry-run                 Print commands without executing"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

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
echo "║       Advance Insights — Container Apps Deployment           ║"
echo "║       AAP Data Agent POC                                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Resource Group : $RESOURCE_GROUP"
echo "  App Name       : $APP_NAME"
echo "  Environment    : $ENV_NAME"
echo "  Location       : $LOCATION"
echo "  Subscription   : $SUBSCRIPTION"
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

az account set --subscription "$SUBSCRIPTION" 2>/dev/null || fail "Failed to set subscription $SUBSCRIPTION"
ok "Subscription set to $SUBSCRIPTION"
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

# ── Step 2: Container App Environment ────────────────────────────────────

info "Step 2: Container App Environment"

if az containerapp env show --name "$ENV_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    ok "Environment '$ENV_NAME' already exists"
else
    echo "  Creating Container App Environment '$ENV_NAME'..."
    run_cmd az containerapp env create \
        --name "$ENV_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output none
    ok "Environment created"
fi

# ── Step 3: Container App ───────────────────────────────────────────────

info "Step 3: Container App"

if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    ok "Container App '$APP_NAME' already exists"
    [[ -n "$FQDN" ]] && echo "    FQDN: $FQDN"
else
    echo "  Creating Container App '$APP_NAME'..."

    ENV_VARS="FABRIC_WORKSPACE_ID=$FABRIC_WORKSPACE_ID FABRIC_API_BASE=$FABRIC_API_BASE ENTRA_TENANT_ID=$TENANT_ID"
    [[ -n "$CLIENT_ID" ]] && ENV_VARS="$ENV_VARS ENTRA_CLIENT_ID=$CLIENT_ID"

    run_cmd az containerapp create \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --environment "$ENV_NAME" \
        --image "mcr.microsoft.com/azurelinux/base/python:3.11" \
        --target-port 8000 \
        --ingress external \
        --system-assigned \
        --cpu 0.5 \
        --memory 1Gi \
        --min-replicas 1 \
        --max-replicas 10 \
        --env-vars $ENV_VARS \
        --output none

    FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "$APP_NAME.azurecontainerapps.io")
    ok "Container App created"
    echo "    FQDN: $FQDN"
fi

# ── Step 4: Secrets ──────────────────────────────────────────────────────

info "Step 4: Secrets"

if [[ -n "$CLIENT_SECRET" ]]; then
    run_cmd az containerapp secret set \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --secrets "entra-client-secret=$CLIENT_SECRET" \
        --output none 2>/dev/null

    run_cmd az containerapp update \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --set-env-vars "ENTRA_CLIENT_SECRET=secretref:entra-client-secret" \
        --output none 2>/dev/null

    ok "ENTRA_CLIENT_SECRET configured"
else
    warn "No client secret provided — set it later with:"
    echo "    az containerapp secret set --name $APP_NAME --resource-group $RESOURCE_GROUP --secrets entra-client-secret=YOUR_SECRET"
fi

# ── Step 5: Managed Identity ────────────────────────────────────────────

info "Step 5: Managed Identity"

PRINCIPAL_ID=$(az containerapp identity show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "principalId" -o tsv 2>/dev/null || echo "")
if [[ -n "$PRINCIPAL_ID" ]]; then
    ok "System-assigned managed identity enabled"
    echo "    Principal ID: $PRINCIPAL_ID"
else
    warn "Could not retrieve managed identity"
fi

# ── Summary ──────────────────────────────────────────────────────────────

FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "$APP_NAME.azurecontainerapps.io")

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✅  Deployment Complete                                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  App URL: https://$FQDN"
echo ""
echo "  ── Manual Steps Required ──"
echo ""
echo "  1. Build & push the Docker image (or let GitHub Actions do it):"
echo "     docker build -t ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest ./web"
echo "     docker push ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest"
echo ""
echo "  2. Update Container App image:"
echo "     az containerapp update --name $APP_NAME --resource-group $RESOURCE_GROUP --image ghcr.io/YOUR_ORG/aap-loyalty-intelligence:latest"
echo ""
echo "  3. Grant managed identity Fabric workspace access:"
echo "     • https://msit.powerbi.com → Workspace → Manage access"
echo "     • Add the managed identity (by Principal ID) as Contributor"
echo ""
echo "  4. Create Entra ID app registration (if not already done):"
echo "     • Set redirect URI to: https://$FQDN/auth/callback"
echo "     • Set ENTRA_CLIENT_ID and ENTRA_CLIENT_SECRET env vars"
echo ""
echo "  5. Test: visit https://$FQDN"
echo ""
