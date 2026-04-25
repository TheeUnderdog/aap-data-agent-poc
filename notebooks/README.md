# AAP Loyalty Sample Data — Fabric Notebook

## Prerequisites

- Microsoft Fabric workspace with a **Lakehouse** attached
- Fabric capacity (F2 or higher recommended)
- Workspace contributor role or higher

## Setup Steps

### 1. Import the Notebook

1. Open your Fabric workspace
2. Click **+ New** → **Import notebook**
3. Upload `01-create-sample-data.py`
4. The notebook opens in the Fabric editor

### 2. Attach a Lakehouse

1. In the notebook's left panel, click **Add Lakehouse**
2. Select your existing Lakehouse or create a new one (e.g., `aap_loyalty_lakehouse`)
3. Confirm — the Lakehouse appears under **Explorer**

### 3. Run the Notebook

1. Click **Run all** in the toolbar
2. Execution takes ~3–5 minutes depending on capacity
3. Each cell prints a ✅ confirmation with row counts

### 4. Expected Output

| Table | Rows |
|---|---|
| `stores` | 500 |
| `sku_reference` | 2,000 |
| `loyalty_members` | 5,000 |
| `transactions` | 50,000 |
| `transaction_items` | ~150,000 |
| `member_points` | 100,000 |
| `coupon_rules` | 50 |
| `coupons` | 20,000 |
| `csr` | 200 |
| `csr_activities` | 10,000 |

### 5. Next Step — Create Semantic Views

1. Open the Lakehouse **SQL analytics endpoint**
2. Click **New SQL query**
3. Paste the contents of `scripts/create-semantic-views.sql`
4. Execute — this creates 9 views in the `semantic` schema
5. The Data Agent will query these views, not the raw tables

## Notes

- Data generation is deterministic (seed = 42) — re-running produces identical data
- Date range: 2023-01-01 to 2026-04-01
- All tables live in the default Lakehouse database (Fabric Spark doesn't support custom schemas)
- Seasonal patterns: spring/summer months have higher transaction volume
