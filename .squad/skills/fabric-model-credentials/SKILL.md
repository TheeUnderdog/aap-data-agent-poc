# Skill: Fabric Semantic Model Credential Binding

## When to Use
After deploying a Fabric semantic model via REST API (TMDL), the model's data sources have no credentials. Refresh will fail until credentials are bound.

## Pattern
1. **TakeOver** — `POST /v1.0/myorg/datasets/{id}/Default.TakeOver` binds the calling user's OAuth2 token to all data sources
2. **Get datasources** — `GET /v1.0/myorg/datasets/{id}/datasources` returns `gatewayId` and `datasourceId` for each source
3. **Patch credentials** — `PATCH /v1.0/myorg/gateways/{gw}/datasources/{ds}` with `credentialType: "OAuth2"` and `privacyLevel: "Organizational"`
4. **Refresh** — `POST /v1.0/myorg/datasets/{id}/refreshes` triggers data load

## Key Details
- Requires **two** token scopes: `https://api.fabric.microsoft.com/.default` (model lookup) and `https://analysis.windows.net/powerbi/api/.default` (dataset operations)
- TakeOver returns 409 if you already own it — treat as success
- Credential patch may return 400 for Fabric-native sources — TakeOver alone is often sufficient
- Always add a 3-5s delay between TakeOver and subsequent API calls for propagation

## Reference Script
`scripts/bind-model-credentials.py`
