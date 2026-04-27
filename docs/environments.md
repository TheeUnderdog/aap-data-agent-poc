# AAP Data Agent POC — Environment Reference

Three Azure/Fabric environments have been used during development. The **active** environment is Microsoft Corp (Fabric) with local Flask dev (no app registration).

---

## Tenants

| Environment | Tenant Name | Tenant ID | Domain | Dave's Role |
|-------------|-------------|-----------|--------|-------------|
| **Microsoft Corp** | Microsoft | `72f988bf-86f1-41af-91ab-2d7cd011db47` | `microsoft.onmicrosoft.com` | Employee |
| **FDPO** | Microsoft Non-Production | `16b3c013-d300-468d-ac64-7eda0820b6d3` | `fdpo.onmicrosoft.com` | User |
| **Contoso (MCAP)** | MngEnvMCAP757180 | `39f0ed6b-05f4-4e0e-b167-9d9779789c88` | `MngEnvMCAP757180.onmicrosoft.com` | Tenant Admin |

---

## Azure Subscriptions

| Environment | Subscription Name | Subscription ID | Usage |
|-------------|-------------------|-----------------|-------|
| **Microsoft Corp** | MSFT-Provisioning-01[Prod] | `0832b3b6-22b3-4c47-8d8b-572054b97257` | Current `az login` default |
| **FDPO** | (FDPO sub) | `629e646d-3923-4838-8f3e-cbee6c72734c` | Container App deployment target |

---

## Fabric Workspaces

### Microsoft Corp (ACTIVE)

| Resource | Value |
|----------|-------|
| Workspace Name | AAP-RewardsLoyalty-POC |
| Workspace ID | `82f53636-206f-4825-821b-bdaa8e089893` |
| Capacity ID | `8b61d9ff-78d3-465e-a647-a0c84c3416b4` |
| Capacity Region | West Central US |
| Capacity SKU | F64+ (supports Data Agents) |
| OneLake Blob | `https://msit-westcentralus-onelake.blob.fabric.microsoft.com` |
| OneLake DFS | `https://msit-westcentralus-onelake.dfs.fabric.microsoft.com` |

**Workspace Items:**

| Type | Name | ID |
|------|------|----|
| Lakehouse | RewardsLoyaltyData | `0b895197-a0b2-40b4-9ab3-2daeb0e778c0` |
| SQL Endpoint | RewardsLoyaltyData | `d924938e-809d-495e-843b-946ddc5d19a1` |
| Semantic Model | AAP Rewards Loyalty Model | `ffc1ba28-0ba1-4d5c-a0e1-3392878e4cdb` |
| Notebook | 01-create-sample-data | `f0af7753-cfef-47f5-8c0f-43ded9218b66` |
| Notebook | 02-data-sanity-check | `641d6c7f-182d-4651-b110-3e6d69b533b6` |
| Data Agent | AAP Customer Service & Support Analyst | `e2cf8db6-2e51-45b6-bb2d-edfeeeb8b38a` |
| Data Agent | Loyalty Program Manager | `b03579f9-1074-4578-8165-6954a83b31c5` |
| Data Agent | Marketing & Promotions Analyst | `f0272a61-7e54-408f-bf70-28495982567b` |
| Data Agent | Merchandising & Category Manager | `1062ac57-5132-4cf1-afbd-71e1e973fbc8` |
| Data Agent | Store Operations Analyst | `e8fc166b-360e-4b0a-922b-05ca8bba3ff4` |

### FDPO (INACTIVE — no Data Agents, PPU capacity too low)

| Resource | Value |
|----------|-------|
| Workspace Name | AAP-RewardsLoyalty-POC |
| Workspace ID | `e7f4acfe-90d7-4685-864a-b5f1216fe614` |
| Capacity ID | `cc5bfcb0-13fc-47b7-88c0-9f4c07a4af33` |
| Capacity SKU | PP3 (PPU — does NOT support Data Agents) |
| Capacity Region | West US 3 |
| Lakehouse ID | `899c38e8-3705-4e8f-9c90-583ee13f3c04` |
| SQL Endpoint | `cpalgfqa2ogunldep3naqifw2m-...datawarehouse.fabric.microsoft.com` |

---

## App Registrations

### Contoso — AAP Loyalty Intelligence (for future production auth)

| Field | Value |
|-------|-------|
| Tenant | Contoso (MCAP) `39f0ed6b-05f4-4e0e-b167-9d9779789c88` |
| App Name | AAP Loyalty Intelligence |
| Client ID | `360a35c3-fdbb-4840-b348-6340faf6937b` |
| Multi-tenant | Yes |
| Redirect URI | `http://localhost:8000/auth/callback` |
| API Permission | Power BI Service > Delegated > `Item.Execute.All` |

### FDPO — AAP Loyalty Intelligence (legacy, single-tenant)

| Field | Value |
|-------|-------|
| Tenant | FDPO `16b3c013-d300-468d-ac64-7eda0820b6d3` |
| App Name | AAP Loyalty Intelligence |
| Client ID | `176f52b8-fc6e-42d4-9f61-c1bceb21d5b4` |
| Multi-tenant | No (FDPO policy restricts to single-tenant) |

---

## Data Agent GUID Mapping

These GUIDs are the same in both `config.js` and the Fabric workspace (corp tenant).

| App Tab | Fabric Data Agent Name | Agent GUID |
|---------|----------------------|------------|
| Crew Chief | (client-side orchestrator, no Fabric agent) | n/a |
| Pit Crew | AAP Customer Service & Support Analyst | `e2cf8db6-2e51-45b6-bb2d-edfeeeb8b38a` |
| GearUp | Loyalty Program Manager | `b03579f9-1074-4578-8165-6954a83b31c5` |
| Ignition | Marketing & Promotions Analyst | `f0272a61-7e54-408f-bf70-28495982567b` |
| PartsPro | Merchandising & Category Manager | `1062ac57-5132-4cf1-afbd-71e1e973fbc8` |
| DieHard | Store Operations Analyst | `e8fc166b-360e-4b0a-922b-05ca8bba3ff4` |

---

## Auth — Current State

**Local dev (active):** No app registration. Flask server uses `ChainedTokenCredential`:
1. `ManagedIdentityCredential` — for Azure Container Apps (future)
2. `AzureCliCredential` — local dev after `az login` to corp tenant
3. `DeviceCodeCredential` — Docker/headless fallback

Scope: `https://api.fabric.microsoft.com/.default`

**Production (future):** Delegated user auth through Contoso multi-tenant app registration. User signs in, server forwards their token to Fabric API.

---

## API Endpoint Pattern

```
POST https://api.fabric.microsoft.com/v1/workspaces/82f53636-206f-4825-821b-bdaa8e089893/dataagents/{AGENT_GUID}/aiassistant/openai
Authorization: Bearer {token}
Content-Type: application/json

{ "messages": [{ "role": "user", "content": "..." }] }
```

---

## Portal URLs

- **Fabric workspace:** `https://msit.powerbi.com/groups/82f53636-206f-4825-821b-bdaa8e089893`
- **Data Agent config:** `https://app.fabric.microsoft.com/groups/82f53636-206f-4825-821b-bdaa8e089893/aiskills/{AGENT_GUID}`

---

## Why Three Tenants?

| Constraint | Impact |
|------------|--------|
| Microsoft Corp requires Service Tree ID for app registrations | Cannot create app reg in corp tenant |
| FDPO restricts app registrations to single-tenant | Cannot make FDPO app reg multi-tenant |
| Fabric Data Agents require F64+ capacity | FDPO's PPU capacity cannot host Data Agents |
| Dave is tenant admin in Contoso | Can create multi-tenant app reg there |

The result: Fabric workspace and Data Agents live in corp tenant (F64+ capacity), the multi-tenant app registration lives in Contoso (admin access), and FDPO is inactive for this project.
