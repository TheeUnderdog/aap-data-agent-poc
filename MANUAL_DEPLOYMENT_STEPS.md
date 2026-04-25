# Manual Deployment Steps — Quick Reference

**Status:** 8 of 11 deployment steps automated and complete. 3 manual tasks remaining.

---

## ✅ What's Already Done

1. ✅ Workspace provisioned (AAP-RewardsLoyalty-POC)
2. ✅ Lakehouse created (RewardsLoyaltyData) with SQL endpoint
3. ✅ 9 semantic views deployed to Lakehouse
4. ✅ Semantic model deployed (AAP Rewards Loyalty Model)
   - 10 tables, 8 relationships, 34 DAX measures
5. ✅ Credential binding executed (model can authenticate to SQL endpoint)
6. ✅ Linguistic schema configured
   - 50 table synonyms, 66 column synonyms, 53 value synonyms
   - AI instructions deployed (53 lines of business context)
7. ✅ 5 Fabric Data Agent configs ready in `agents/` folder

---

## 🔧 Manual Task 1: Debug & Run Sample Data Notebook

**Problem:** Notebook execution via REST API failed with "Spark session cancelled" error.

**Steps:**
1. Open notebook in portal:  
   https://app.fabric.microsoft.com/groups/82f53636-206f-4825-821b-bdaa8e089893/notebooks/f0af7753-cfef-47f5-8c0f-43ded9218b66

2. Verify Lakehouse is attached:
   - Click notebook settings → Lakehouse
   - Should show "RewardsLoyaltyData" attached
   - If not attached, add it via "Add lakehouse" button

3. Run cells one by one to identify error:
   - Click first cell, press Shift+Enter
   - Watch for error messages in cell output
   - Common issues:
     - PySpark syntax errors (check imports)
     - Schema conflicts (drop tables if they exist)
     - Memory/timeout issues (reduce row counts if needed)

4. Once all cells run successfully, verify tables exist:
   - In Lakehouse view, check "Tables" section
   - Should see 10 tables: `loyalty_members`, `transactions`, `stores`, `products`, `transaction_items`, `points_ledger`, `coupon_rules`, `coupons`, `csr`, `csr_activities`

**Expected output:** ~337K rows across 10 Delta tables in Lakehouse

---

## 🔄 Manual Task 2: Refresh Semantic Model

**Why needed:** Model is configured but has no data until Lakehouse tables exist.

**Steps:**
1. After notebook completes successfully, go to workspace:  
   https://app.fabric.microsoft.com/groups/82f53636-206f-4825-821b-bdaa8e089893

2. Find "AAP Rewards Loyalty Model" in workspace items list

3. Click "..." menu → "Refresh now"

4. Wait 1-2 minutes for refresh to complete

5. Verify success:
   - Click into the semantic model
   - Check "Data" tab → should show row counts for all 10 tables
   - If refresh fails, check notebook output — tables might not exist

**Expected result:** Model shows data loaded (e.g., loyalty_members: 5,000 rows, transactions: 50,000 rows)

---

## 🤖 Manual Task 3: Import Fabric Data Agent Configurations

**Why manual:** Fabric Data Agent has no REST API — portal-only configuration.

**Steps:**

### 3.1 Create a New Data Agent
1. Go to Fabric workspace:  
   https://app.fabric.microsoft.com/groups/82f53636-206f-4825-821b-bdaa8e089893

2. Click "New" → "Data Agent" (or find in item type list)

3. Give it a name: **"AAP Rewards Loyalty Agent"**

4. Connect to semantic model:
   - Select "AAP Rewards Loyalty Model" as data source

### 3.2 Import Agent Configurations (Repeat for Each Persona)

We have **5 agent personas** ready to import:
- `agents/customer-service/` — Customer Service & Support
- `agents/loyalty-program-manager/` — Loyalty Program Manager
- `agents/marketing-promotions/` — Marketing & Promotions
- `agents/merchandising/` — Merchandising & Category Manager
- `agents/store-operations/` — Store Operations

For each persona:

1. Open the agent config folder (e.g., `agents/customer-service/`)

2. Review files:
   - `config.json` — agent metadata
   - `{agent-name}-instructions.md` — full persona prompt (e.g., `customer-service-instructions.md`, `loyalty-program-manager-instructions.md`)
   - `examples.json` — 6-8 sample Q&A pairs

3. In Fabric portal, configure agent:
   - **System Instructions:** Copy content from the agent's `-instructions.md` file (e.g., `customer-service-instructions.md`)
   - **Examples/Training:** Add sample queries from `examples.json`
   - **Data Scope:** Should already be set (semantic model connection)

4. Save and test with a sample query:
   - Example: "How many gold tier members do we have?"
   - Verify agent returns a valid SQL query and result

5. Repeat for remaining 4 personas

**Time estimate:** 5-7 minutes per agent × 5 agents = 25-35 minutes

---

## ✅ Manual Task 4: Test End-to-End

Once all 3 manual tasks complete:

1. **Test a natural language query** via Fabric Data Agent:
   - "Show me top 10 stores by revenue"
   - "How many platinum members joined last month?"
   - "What's the most popular product category?"

2. **Verify the agent**:
   - Generates valid SQL (check query log)
   - Returns accurate results (compare to manual SQL query)
   - Respects synonyms (e.g., "agents" → queries `csr` table)

3. **Check linguistic schema**:
   - Open semantic model → "Prep for AI" or Q&A settings
   - Verify synonyms appear (e.g., "members" → loyalty_members)
   - Test with synonym: "show me customers by tier" (should understand "customers" = loyalty_members)

---

## 🆘 Troubleshooting

### Notebook fails to run
- Check Spark logs in notebook output
- Verify Lakehouse is attached
- Check Python syntax (PySpark DataFrames)
- If tables already exist, drop them first: `spark.sql("DROP TABLE IF EXISTS loyalty_members")`

### Semantic model refresh fails
- Ensure notebook ran successfully (check Lakehouse for tables)
- Verify credentials are bound (should be — we ran `bind-model-credentials.py`)
- Check semantic model definition sources `dbo.tablename` not `semantic.v_*`

### Data Agent doesn't understand synonyms
- Check that linguistic schema was deployed (we ran `configure-linguistic-schema.py`)
- Open model → Prep for AI → verify synonyms appear
- May need to refresh agent cache (portal bug)

### Data Agent returns no results
- Check that semantic model has data (Task 2 refresh)
- Verify agent is connected to correct semantic model
- Check query log for generated SQL — might be valid SQL but no matching rows

---

## 📁 Reference Artifacts

- **Deployment scripts:** `scripts/` folder
- **Agent configs:** `agents/` folder (5 personas × 3 files = 15 files)
- **Sample queries:** `config/sample-queries.json` (25 NL→SQL pairs)
- **Notebook:** `notebooks/01-create-sample-data.py`
- **Deployment status:** `.squad/decisions/inbox/livingston-deployment-completion.md`

---

## 📞 Need Help?

Reference:
- `docs/data-schema.md` — schema documentation
- `docs/architecture.md` — system architecture
- `docs/capability-overview.md` — what's deployed and how it works

**Workspace ID:** `82f53636-206f-4825-821b-bdaa8e089893`  
**Lakehouse ID:** `0b895197-a0b2-40b4-9ab3-2daeb0e778c0`  
**Semantic Model ID:** `f5483f6a-e81a-4cd8-ac42-88af4b972347`

### Fabric Data Agent GUIDs

| Chatbot Tab | Fabric Data Agent | GUID | Instructions File |
|-------------|-------------------|------|-------------------|
| Pit Crew | Customer Service & Support | `e2cf8db6-2e51-45b6-bb2d-edfeeeb8b38a` | `agents/customer-service/customer-service-instructions.md` |
| GearUp | Loyalty Program Manager | `b03579f9-1074-4578-8165-6954a83b31c5` | `agents/loyalty-program-manager/loyalty-program-manager-instructions.md` |
| Ignition | Marketing & Promotions | `f0272a61-7e54-408f-bf70-28495982567b` | `agents/marketing-promotions/marketing-promotions-instructions.md` |
| PartsPro | Merchandising & Categories | `1062ac57-5132-4cf1-afbd-71e1e973fbc8` | `agents/merchandising/merchandising-instructions.md` |
| DieHard | Store Operations | `e8fc166b-360e-4b0a-922b-05ca8bba3ff4` | `agents/store-operations/store-operations-instructions.md` |

**API endpoint (OpenAI-compatible):**
```
POST https://msitapi.fabric.microsoft.com/v1/workspaces/82f53636-206f-4825-821b-bdaa8e089893/dataagents/{GUID}/aiassistant/openai
Authorization: Bearer <token>
Content-Type: application/json

{ "messages": [{ "role": "user", "content": "..." }] }
```

**Auth scope:** `https://api.fabric.microsoft.com/.default`  
**Portal base URL:** `https://msit.powerbi.com/groups/82f53636-206f-4825-821b-bdaa8e089893/aiskills/{GUID}`
