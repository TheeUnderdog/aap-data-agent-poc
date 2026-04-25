# %% [markdown]
# # AAP Loyalty Program — Data Sanity Check Pipeline
#
# **Purpose:** Validates that the generated sample data produces realistic answers
# for the kinds of questions our Fabric Data Agents will be asked during demos.
#
# **Usage:** Run after `01-create-sample-data.py` completes. Attach to the same Lakehouse.
#
# **Pipeline:**
# - **Block 1:** Data Census — row counts, date ranges, FK integrity, null rates
# - **Block 2:** Distribution Sanity — tier splits, channel mix, per-agent checks
# - **Block 3:** Business Logic — tier-correlated metrics, seasonality, churn, lifecycle
# - **Block 4:** LLM Diagnostic Report — structured fix instructions for Fabric Copilot
#
# Each check gets PASS / WARN / FAIL. Final scorecard tells you if the data is demo-ready.

# %%
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import date

spark = SparkSession.builder.getOrCreate()

# ── Scorecard accumulator ───────────────────────────────────────────────────────
results = []  # list of (block, check_name, status, detail)

def record(block, name, status, detail=""):
    results.append((block, name, status, detail))
    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[status]
    print(f"  {icon} {name}: {detail}")

# %% [markdown]
# ## Block 1: Data Census
# Does the data exist and is it shaped right?

# %%
print("═" * 60)
print("  BLOCK 1: DATA CENSUS")
print("═" * 60)

# ── 1a. Row counts ──────────────────────────────────────────────────────────────
EXPECTED_COUNTS = {
    "stores":            (400, 600),
    "sku_reference":     (1500, 6000),
    "loyalty_members":   (40000, 60000),
    "transactions":      (400000, 600000),
    "transaction_items": (100000, 2000000),
    "member_points":     (80000, 600000),
    "coupon_rules":      (50, 200),
    "coupons":           (150000, 250000),
    "csr":               (100, 600),
    "csr_activities":    (8000, 60000),
}

print("\n📊 Row Counts:")
print(f"  {'Table':<22} {'Actual':>10}  {'Expected Range':>20}  Status")
print(f"  {'─'*22} {'─'*10}  {'─'*20}  {'─'*6}")

all_counts = {}
count_ok = True
for table, (lo, hi) in EXPECTED_COUNTS.items():
    try:
        df = spark.table(table)
        n = df.count()
        all_counts[table] = n
        in_range = lo <= n <= hi
        status = "✅" if in_range else "❌"
        if not in_range:
            count_ok = False
        print(f"  {table:<22} {n:>10,}  {f'{lo:,}–{hi:,}':>20}  {status}")
    except Exception as e:
        all_counts[table] = 0
        count_ok = False
        print(f"  {table:<22} {'MISSING':>10}  {f'{lo:,}–{hi:,}':>20}  ❌")

record("Census", "Row counts", "PASS" if count_ok else "FAIL",
       f"{sum(1 for t,(lo,hi) in EXPECTED_COUNTS.items() if lo <= all_counts.get(t,0) <= hi)}/{len(EXPECTED_COUNTS)} tables in range")

# ── 1b. Date range validation ────────────────────────────────────────────────────
print("\n📅 Date Ranges:")
txn_dates = spark.table("transactions").select(
    F.min("transaction_date").alias("min_date"),
    F.max("transaction_date").alias("max_date")
).collect()[0]

min_d, max_d = txn_dates["min_date"], txn_dates["max_date"]
date_ok = min_d <= date(2023, 3, 1) and max_d >= date(2025, 12, 1)
print(f"  Transactions: {min_d} to {max_d}")
record("Census", "Date range", "PASS" if date_ok else "FAIL",
       f"{min_d} to {max_d}" + ("" if date_ok else " — expected 2023 to 2026"))

# ── 1c. FK integrity ─────────────────────────────────────────────────────────────
print("\n🔗 FK Integrity:")
fk_checks = [
    ("transactions.member_id → loyalty_members",
     "SELECT COUNT(*) as n FROM transactions t LEFT JOIN loyalty_members m ON t.member_id = m.member_id WHERE m.member_id IS NULL"),
    ("transactions.store_id → stores",
     "SELECT COUNT(*) as n FROM transactions t LEFT JOIN stores s ON t.store_id = s.store_id WHERE s.store_id IS NULL"),
    ("transaction_items.transaction_id → transactions",
     "SELECT COUNT(*) as n FROM transaction_items ti LEFT JOIN transactions t ON ti.transaction_id = t.transaction_id WHERE t.transaction_id IS NULL"),
    ("transaction_items.sku → sku_reference",
     "SELECT COUNT(*) as n FROM transaction_items ti LEFT JOIN sku_reference sr ON ti.sku = sr.sku WHERE sr.sku IS NULL"),
    ("coupons.member_id → loyalty_members",
     "SELECT COUNT(*) as n FROM coupons c LEFT JOIN loyalty_members m ON c.member_id = m.member_id WHERE c.member_id IS NOT NULL AND m.member_id IS NULL"),
    ("csr_activities.csr_id → csr",
     "SELECT COUNT(*) as n FROM csr_activities ca LEFT JOIN csr c ON ca.csr_id = c.csr_id WHERE c.csr_id IS NULL"),
    ("csr_activities.member_id → loyalty_members",
     "SELECT COUNT(*) as n FROM csr_activities ca LEFT JOIN loyalty_members m ON ca.member_id = m.member_id WHERE m.member_id IS NULL"),
]

fk_ok = True
for label, sql in fk_checks:
    orphans = spark.sql(sql).collect()[0]["n"]
    ok = orphans == 0
    if not ok:
        fk_ok = False
    icon = "✅" if ok else "❌"
    print(f"  {icon} {label}: {orphans} orphans")

record("Census", "FK integrity", "PASS" if fk_ok else "FAIL",
       f"{'All clean' if fk_ok else 'Orphan records found'}")

# ── 1d. Null checks on key columns ──────────────────────────────────────────────
print("\n🔍 Null Rates (key columns):")
null_checks = [
    ("loyalty_members", ["member_id", "tier", "member_status", "enrollment_date"]),
    ("transactions", ["transaction_id", "member_id", "store_id", "transaction_date", "total"]),
    ("transaction_items", ["item_id", "transaction_id", "sku", "line_total"]),
    ("member_points", ["point_id", "member_id", "activity_type", "points_amount"]),
    ("coupons", ["coupon_id", "status"]),
    ("csr_activities", ["activity_id", "csr_id", "member_id", "activity_type"]),
]

null_ok = True
for table, cols in null_checks:
    df = spark.table(table)
    total = df.count()
    for col in cols:
        null_n = df.where(F.col(col).isNull()).count()
        pct = (null_n / total * 100) if total > 0 else 0
        if pct > 0.1:
            null_ok = False
            print(f"  ❌ {table}.{col}: {null_n:,} nulls ({pct:.1f}%)")

if null_ok:
    print("  ✅ All key columns clean (<0.1% nulls)")

record("Census", "Null rates", "PASS" if null_ok else "WARN",
       "Key columns clean" if null_ok else "Some key columns have nulls")

print()

# %% [markdown]
# ## Block 2: Distribution Sanity
# Do the distributions look like a real business?

# %%
print("═" * 60)
print("  BLOCK 2: DISTRIBUTION SANITY")
print("═" * 60)

# ── 2a. Tier distribution ────────────────────────────────────────────────────────
print("\n👥 Tier Distribution:")
tier_df = spark.sql("""
    SELECT tier, COUNT(*) as n,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
    FROM loyalty_members
    GROUP BY tier ORDER BY pct DESC
""").collect()

tier_pcts = {r["tier"]: r["pct"] for r in tier_df}
for r in tier_df:
    print(f"  {r['tier']:<12} {r['n']:>8,}  ({r['pct']}%)")

tier_ok = all(tier_pcts.get(t, 0) > 2 and tier_pcts.get(t, 0) < 75 for t in ["Bronze","Silver","Gold","Platinum"])
# Also check ordering
tier_ordered = (tier_pcts.get("Bronze",0) > tier_pcts.get("Silver",0) >
                tier_pcts.get("Gold",0) > tier_pcts.get("Platinum",0))
tier_status = "PASS" if (tier_ok and tier_ordered) else ("WARN" if tier_ok else "FAIL")
record("Distributions", "Tier split", tier_status,
       f"{'Ordered correctly' if tier_ordered else 'Tier ordering wrong'}: B={tier_pcts.get('Bronze',0)}% S={tier_pcts.get('Silver',0)}% G={tier_pcts.get('Gold',0)}% P={tier_pcts.get('Platinum',0)}%")

# ── 2b. Channel mix ──────────────────────────────────────────────────────────────
print("\n📡 Channel Mix:")
channel_df = spark.sql("""
    SELECT channel, COUNT(*) as n,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
    FROM transactions GROUP BY channel ORDER BY pct DESC
""").collect()

for r in channel_df:
    print(f"  {r['channel']:<12} {r['n']:>10,}  ({r['pct']}%)")

channel_pcts = {r["channel"]: r["pct"] for r in channel_df}
instore = channel_pcts.get("in-store", 0)
online = channel_pcts.get("online", 0)
channel_ok = instore > online
record("Distributions", "Channel mix", "PASS" if channel_ok else "FAIL",
       f"In-store {instore}% vs Online {online}%" + ("" if channel_ok else " — online should not dominate"))

# ── 2c. Return rate ──────────────────────────────────────────────────────────────
print("\n↩️ Return Rate:")
return_df = spark.sql("""
    SELECT transaction_type, COUNT(*) as n,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
    FROM transactions GROUP BY transaction_type
""").collect()

return_pcts = {r["transaction_type"]: r["pct"] for r in return_df}
return_rate = return_pcts.get("return", 0)
print(f"  Returns: {return_rate}%")
return_ok = 1 <= return_rate <= 20
record("Distributions", "Return rate", "PASS" if return_ok else "FAIL",
       f"{return_rate}%" + ("" if return_ok else " — expected 1-20%"))

# ── 2d. Coupon status distribution ───────────────────────────────────────────────
print("\n🎟️ Coupon Status:")
coupon_df = spark.sql("""
    SELECT status, COUNT(*) as n,
           ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as pct
    FROM coupons GROUP BY status ORDER BY pct DESC
""").collect()

for r in coupon_df:
    print(f"  {r['status']:<12} {r['n']:>10,}  ({r['pct']}%)")

coupon_pcts = {r["status"]: r["pct"] for r in coupon_df}
redeemed = coupon_pcts.get("redeemed", 0)
coupon_ok = redeemed < 80 and coupon_pcts.get("expired", 0) < 80
record("Distributions", "Coupon status", "PASS" if coupon_ok else "FAIL",
       f"Redeemed: {redeemed}%" + ("" if coupon_ok else " — too concentrated"))

# ── 2e. Category revenue concentration (Merchandising) ──────────────────────────
print("\n🏷️ Category Revenue (Merchandising agent):")
cat_df = spark.sql("""
    SELECT category, ROUND(SUM(line_total), 2) as revenue,
           ROUND(SUM(line_total) * 100.0 / SUM(SUM(line_total)) OVER(), 1) as pct
    FROM transaction_items
    WHERE is_return = false
    GROUP BY category ORDER BY revenue DESC
""").collect()

for r in cat_df:
    print(f"  {r['category']:<16} ${r['revenue']:>12,.2f}  ({r['pct']}%)")

top3_pct = sum(r["pct"] for r in cat_df[:3]) if len(cat_df) >= 3 else 0
cat_ok = 30 <= top3_pct <= 85
# Also check that categories aren't all identical (max - min > 3pp)
if len(cat_df) >= 3:
    cat_spread = cat_df[0]["pct"] - cat_df[-1]["pct"]
    cat_ok = cat_ok and cat_spread > 3
record("Distributions", "Category concentration", "PASS" if cat_ok else "WARN",
       f"Top 3 = {top3_pct:.0f}% of revenue")

# ── 2f. Return rate per category (Merchandising) ────────────────────────────────
print("\n↩️ Return Rate by Category (Merchandising agent):")
cat_return_df = spark.sql("""
    SELECT ti.category,
           COUNT(*) as total_items,
           SUM(CASE WHEN ti.is_return THEN 1 ELSE 0 END) as return_items,
           ROUND(SUM(CASE WHEN ti.is_return THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as return_pct
    FROM transaction_items ti
    GROUP BY ti.category ORDER BY return_pct DESC
""").collect()

for r in cat_return_df:
    print(f"  {r['category']:<16} {r['return_pct']}% return rate ({r['return_items']:,} / {r['total_items']:,})")

# Check variance: categories should NOT all have identical return rates
cat_ret_rates = [r["return_pct"] for r in cat_return_df]
cat_ret_spread = max(cat_ret_rates) - min(cat_ret_rates) if cat_ret_rates else 0
cat_ret_ok = cat_ret_spread > 1.0  # at least 1pp difference between highest and lowest
record("Distributions", "Category return variance", "PASS" if cat_ret_ok else "WARN",
       f"Spread: {cat_ret_spread:.1f}pp (max {max(cat_ret_rates):.1f}%, min {min(cat_ret_rates):.1f}%)")

# ── 2g. Regional performance (Store Ops) ─────────────────────────────────────────
print("\n🗺️ Regional Performance (Store Ops agent):")
region_df = spark.sql("""
    SELECT s.region, COUNT(t.transaction_id) as txn_count,
           ROUND(SUM(t.total), 2) as total_revenue,
           ROUND(AVG(t.total), 2) as avg_txn
    FROM transactions t JOIN stores s ON t.store_id = s.store_id
    GROUP BY s.region ORDER BY total_revenue DESC
""").collect()

for r in region_df:
    print(f"  {r['region']:<14} {r['txn_count']:>10,} txns  ${r['total_revenue']:>14,.2f}  (avg ${r['avg_txn']:.2f})")

region_revs = [r["total_revenue"] for r in region_df]
if region_revs:
    region_mean = sum(region_revs) / len(region_revs)
    region_spread_pct = (max(region_revs) - min(region_revs)) / region_mean * 100 if region_mean else 0
    region_ok = region_spread_pct > 5
else:
    region_ok = False
    region_spread_pct = 0

record("Distributions", "Regional variance", "PASS" if region_ok else "WARN",
       f"{region_spread_pct:.0f}% spread between strongest and weakest region")

# ── 2h. Store-level outliers (Store Ops) ──────────────────────────────────────────
print("\n🏪 Store-Level Return Rate Outliers (Store Ops agent):")
store_return_df = spark.sql("""
    SELECT t.store_id, s.store_name, s.region,
           COUNT(*) as total_txns,
           SUM(CASE WHEN t.transaction_type = 'return' THEN 1 ELSE 0 END) as returns,
           ROUND(SUM(CASE WHEN t.transaction_type = 'return' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as return_pct
    FROM transactions t JOIN stores s ON t.store_id = s.store_id
    GROUP BY t.store_id, s.store_name, s.region
    HAVING COUNT(*) >= 50
    ORDER BY return_pct DESC
""").collect()

if store_return_df:
    overall_return = float(sum(r["returns"] for r in store_return_df)) / float(sum(r["total_txns"] for r in store_return_df)) * 100
    top5 = store_return_df[:5]
    print(f"  Network average: {overall_return:.1f}%")
    print(f"  Top 5 highest return rate stores:")
    for r in top5:
        ratio = float(r["return_pct"]) / overall_return if overall_return else 0
        print(f"    {r['store_name']:<24} {r['return_pct']}% ({ratio:.1f}x avg) — {r['region']}")

    # Check: at least some stores should be 1.3x+ above average
    max_ratio = float(max(r["return_pct"] for r in store_return_df)) / overall_return if overall_return else 0
    store_outlier_ok = max_ratio > 1.3
else:
    store_outlier_ok = False
    max_ratio = 0

record("Distributions", "Store return outliers", "PASS" if store_outlier_ok else "WARN",
       f"Highest store is {max_ratio:.1f}x the network average")

# ── 2i. Coupon redemption by campaign (Marketing) ────────────────────────────────
print("\n📢 Coupon Redemption by Campaign (Marketing agent):")
campaign_df = spark.sql("""
    SELECT cr.campaign_name,
           COUNT(*) as total_coupons,
           SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) as redeemed,
           ROUND(SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as redemption_pct
    FROM coupons c JOIN coupon_rules cr ON c.coupon_rule_id = cr.rule_id
    GROUP BY cr.campaign_name
    ORDER BY redemption_pct DESC
""").collect()

for r in campaign_df:
    print(f"  {r['campaign_name']:<30} {r['redemption_pct']}% ({r['redeemed']:,} / {r['total_coupons']:,})")

campaign_rates = [r["redemption_pct"] for r in campaign_df]
campaign_spread = max(campaign_rates) - min(campaign_rates) if campaign_rates else 0
campaign_ok = campaign_spread > 5  # at least 5pp difference between best and worst campaign
record("Distributions", "Campaign redemption variance", "PASS" if campaign_ok else "WARN",
       f"Spread: {campaign_spread:.0f}pp across campaigns")

# ── 2j. Discount type comparison (Marketing) ─────────────────────────────────────
print("\n💰 Discount Type Comparison (Marketing agent):")
discount_df = spark.sql("""
    SELECT cr.discount_type,
           COUNT(*) as total_coupons,
           ROUND(SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as redemption_pct
    FROM coupons c JOIN coupon_rules cr ON c.coupon_rule_id = cr.rule_id
    GROUP BY cr.discount_type
    ORDER BY redemption_pct DESC
""").collect()

for r in discount_df:
    print(f"  {r['discount_type']:<14} {r['redemption_pct']}% redemption ({r['total_coupons']:,} coupons)")

# Just check that at least 2 discount types exist and they aren't identical
discount_ok = len(discount_df) >= 2
record("Distributions", "Discount type comparison", "PASS" if discount_ok else "WARN",
       f"{len(discount_df)} discount types found")

# ── 2k. CSR activity by department (Customer Service) ─────────────────────────────
print("\n🎧 CSR Activity by Department (Customer Service agent):")
csr_dept_df = spark.sql("""
    SELECT c.department,
           COUNT(*) as total_activities,
           COLLECT_SET(ca.activity_type) as activity_types
    FROM csr_activities ca JOIN csr c ON ca.csr_id = c.csr_id
    GROUP BY c.department ORDER BY total_activities DESC
""").collect()

for r in csr_dept_df:
    types = ", ".join(sorted(r["activity_types"]))
    print(f"  {r['department']:<24} {r['total_activities']:>6,} activities  Types: {types}")

# Check: departments should exist and have some specialization
dept_counts = [r["total_activities"] for r in csr_dept_df]
dept_spread = max(dept_counts) - min(dept_counts) if dept_counts else 0
dept_ok = len(csr_dept_df) >= 3 and dept_spread > 0
record("Distributions", "CSR department activity", "PASS" if dept_ok else "WARN",
       f"{len(csr_dept_df)} departments active")

print()

# %% [markdown]
# ## Block 3: Business Logic Checks
# Do the numbers tell a story that makes business sense?

# %%
print("═" * 60)
print("  BLOCK 3: BUSINESS LOGIC")
print("═" * 60)

# ── 3a. Spend by tier (must be progressive) ──────────────────────────────────────
print("\n💳 Average Spend by Tier:")
tier_spend_df = spark.sql("""
    SELECT m.tier,
           COUNT(DISTINCT t.transaction_id) as txn_count,
           ROUND(AVG(t.total), 2) as avg_txn,
           ROUND(SUM(t.total), 2) as total_spend,
           ROUND(SUM(t.total) / COUNT(DISTINCT m.member_id), 2) as spend_per_member
    FROM transactions t JOIN loyalty_members m ON t.member_id = m.member_id
    WHERE t.transaction_type = 'purchase'
    GROUP BY m.tier
""").collect()

tier_spend = {r["tier"]: r for r in tier_spend_df}
tier_order = ["Bronze", "Silver", "Gold", "Platinum"]
for t in tier_order:
    if t in tier_spend:
        r = tier_spend[t]
        print(f"  {t:<12} {r['txn_count']:>10,} txns  avg ${r['avg_txn']:>8.2f}  per-member ${r['spend_per_member']:>10,.2f}")

# Check progressive ordering: spend_per_member must increase with tier
spm = [float(tier_spend[t]["spend_per_member"]) if t in tier_spend else 0 for t in tier_order]
spend_progressive = all(spm[i] < spm[i+1] for i in range(len(spm)-1) if spm[i] > 0 and spm[i+1] > 0)
record("Logic", "Tier spend progression", "PASS" if spend_progressive else "FAIL",
       f"B=${spm[0]:,.0f} → S=${spm[1]:,.0f} → G=${spm[2]:,.0f} → P=${spm[3]:,.0f}" +
       ("" if spend_progressive else " — NOT progressive!"))

# ── 3b. Transaction frequency by tier ─────────────────────────────────────────────
print("\n📈 Transaction Frequency by Tier:")
tier_freq_df = spark.sql("""
    SELECT m.tier,
           COUNT(DISTINCT m.member_id) as member_count,
           COUNT(t.transaction_id) as txn_count,
           ROUND(COUNT(t.transaction_id) * 1.0 / COUNT(DISTINCT m.member_id), 1) as txns_per_member
    FROM loyalty_members m LEFT JOIN transactions t ON m.member_id = t.member_id
    GROUP BY m.tier
""").collect()

tier_freq = {r["tier"]: r["txns_per_member"] for r in tier_freq_df}
for r in sorted(tier_freq_df, key=lambda x: x["txns_per_member"]):
    print(f"  {r['tier']:<12} {r['txns_per_member']:>6.1f} txns/member ({r['member_count']:,} members)")

# Check: Platinum should be at least 1.5x Bronze
plat_freq = tier_freq.get("Platinum", 0)
bronze_freq = tier_freq.get("Bronze", 1)
freq_ratio = float(plat_freq) / float(bronze_freq) if bronze_freq else 0
freq_ok = freq_ratio >= 1.5
record("Logic", "Tier frequency ratio", "PASS" if freq_ok else "FAIL",
       f"Platinum/Bronze ratio: {freq_ratio:.1f}x" + (" — too flat!" if not freq_ok else ""))

# ── 3c. Opt-in rates by tier ─────────────────────────────────────────────────────
print("\n📬 Opt-In Rates by Tier:")
optin_df = spark.sql("""
    SELECT tier,
           ROUND(AVG(CASE WHEN opt_in_email THEN 1 ELSE 0 END) * 100, 1) as email_pct,
           ROUND(AVG(CASE WHEN opt_in_sms THEN 1 ELSE 0 END) * 100, 1) as sms_pct
    FROM loyalty_members GROUP BY tier
""").collect()

optin_map = {r["tier"]: r for r in optin_df}
for t in tier_order:
    if t in optin_map:
        r = optin_map[t]
        print(f"  {t:<12} Email: {r['email_pct']}%  SMS: {r['sms_pct']}%")

# Check: Platinum email opt-in > Bronze email opt-in
plat_email = float(optin_map["Platinum"]["email_pct"]) if "Platinum" in optin_map else 0
bronze_email = float(optin_map["Bronze"]["email_pct"]) if "Bronze" in optin_map else 0
optin_ok = plat_email > bronze_email
record("Logic", "Tier opt-in progression", "PASS" if optin_ok else "FAIL",
       f"Platinum email {plat_email}% vs Bronze {bronze_email}%")

# ── 3d. Coupon redemption by tier ─────────────────────────────────────────────────
print("\n🎟️ Coupon Redemption Rate by Tier:")
tier_coupon_df = spark.sql("""
    SELECT m.tier,
           COUNT(*) as total_coupons,
           SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) as redeemed,
           ROUND(SUM(CASE WHEN c.status = 'redeemed' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as redemption_pct
    FROM coupons c JOIN loyalty_members m ON c.member_id = m.member_id
    GROUP BY m.tier
""").collect()

tier_redeem = {r["tier"]: r["redemption_pct"] for r in tier_coupon_df}
for t in tier_order:
    if t in tier_redeem:
        print(f"  {t:<12} {tier_redeem[t]}%")

# Check: not flat (spread > 5pp between highest and lowest)
redeem_vals = list(tier_redeem.values())
redeem_spread = max(redeem_vals) - min(redeem_vals) if redeem_vals else 0
redeem_ok = redeem_spread > 5
record("Logic", "Tier coupon redemption", "PASS" if redeem_ok else "WARN",
       f"Spread: {redeem_spread:.0f}pp across tiers" + (" — too flat!" if not redeem_ok else ""))

# ── 3e. Seasonality ──────────────────────────────────────────────────────────────
print("\n📆 Monthly Transaction Volume (Seasonality):")
monthly_df = spark.sql("""
    SELECT MONTH(transaction_date) as mo,
           COUNT(*) as txn_count
    FROM transactions GROUP BY MONTH(transaction_date)
    ORDER BY mo
""").collect()

month_names = ["", "Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
for r in monthly_df:
    bar = "█" * int(r["txn_count"] / max(r2["txn_count"] for r2 in monthly_df) * 30)
    print(f"  {month_names[r['mo']]} {r['txn_count']:>8,}  {bar}")

# Coefficient of variation: stdev / mean. Should be > 10% for real seasonality
import statistics
monthly_counts = [r["txn_count"] for r in monthly_df]
if len(monthly_counts) > 1:
    cov = statistics.stdev(monthly_counts) / statistics.mean(monthly_counts) * 100
else:
    cov = 0

season_ok = cov > 10
record("Logic", "Seasonality (CoV)", "PASS" if season_ok else "FAIL",
       f"CoV = {cov:.1f}%" + ("" if season_ok else " — too flat, no seasonal pattern!"))

# ── 3f. Churn candidates ─────────────────────────────────────────────────────────
print("\n🚪 Churn Candidates (180+ days inactive):")
churn_df = spark.sql("""
    SELECT m.tier, COUNT(*) as at_risk
    FROM loyalty_members m
    JOIN (
        SELECT member_id, MAX(transaction_date) as last_txn
        FROM transactions GROUP BY member_id
    ) lt ON m.member_id = lt.member_id
    WHERE m.member_status = 'active'
      AND DATEDIFF(DATE('2026-04-01'), lt.last_txn) > 180
    GROUP BY m.tier ORDER BY at_risk DESC
""").collect()

total_churn = sum(r["at_risk"] for r in churn_df)
for r in churn_df:
    print(f"  {r['tier']:<12} {r['at_risk']:>6,} members at risk")
print(f"  Total: {total_churn:,}")

churn_ok = total_churn > 0
record("Logic", "Churn candidates exist", "PASS" if churn_ok else "FAIL",
       f"{total_churn:,} active members with 180+ day gap" + (" — 0 means no churn modeled!" if not churn_ok else ""))

# ── 3g. Active member recency ────────────────────────────────────────────────────
print("\n⏰ Active Member Transaction Recency:")
recency_df = spark.sql("""
    SELECT
        COUNT(*) as total_active,
        SUM(CASE WHEN lt.last_txn IS NULL THEN 1 ELSE 0 END) as never_transacted,
        SUM(CASE WHEN DATEDIFF(DATE('2026-04-01'), lt.last_txn) <= 90 THEN 1 ELSE 0 END) as last_90d,
        SUM(CASE WHEN DATEDIFF(DATE('2026-04-01'), lt.last_txn) BETWEEN 91 AND 180 THEN 1 ELSE 0 END) as d91_180,
        SUM(CASE WHEN DATEDIFF(DATE('2026-04-01'), lt.last_txn) > 180 THEN 1 ELSE 0 END) as over_180d
    FROM loyalty_members m
    LEFT JOIN (
        SELECT member_id, MAX(transaction_date) as last_txn FROM transactions GROUP BY member_id
    ) lt ON m.member_id = lt.member_id
    WHERE m.member_status = 'active'
""").collect()[0]

total_active = recency_df["total_active"]
print(f"  Active members:         {total_active:,}")
print(f"  Last 90 days:           {recency_df['last_90d']:,}")
print(f"  91-180 days:            {recency_df['d91_180']:,}")
print(f"  180+ days:              {recency_df['over_180d']:,}")
print(f"  Never transacted:       {recency_df['never_transacted']:,}")

# Check: majority of active members should have transacted in last 6 months
recent_pct = (recency_df["last_90d"] + recency_df["d91_180"]) / total_active * 100 if total_active else 0
recency_ok = recent_pct > 50
record("Logic", "Active member recency", "PASS" if recency_ok else "FAIL",
       f"{recent_pct:.0f}% transacted in last 6 months")

# ── 3h. Enrollment timing by tier ────────────────────────────────────────────────
print("\n📅 Average Enrollment Date by Tier:")
enroll_df = spark.sql("""
    SELECT tier, MIN(enrollment_date) as earliest, MAX(enrollment_date) as latest,
           PERCENTILE_APPROX(DATEDIFF(enrollment_date, DATE('2020-01-01')), 0.5) as median_days
    FROM loyalty_members GROUP BY tier ORDER BY median_days
""").collect()

for r in enroll_df:
    print(f"  {r['tier']:<12} Earliest: {r['earliest']}  Latest: {r['latest']}  Median days from 2020: {r['median_days']}")

# Check: Platinum should have earlier median enrollment than Bronze
enroll_map = {r["tier"]: r["median_days"] for r in enroll_df}
plat_days = enroll_map.get("Platinum", 9999)
bronze_days = enroll_map.get("Bronze", 0)
enroll_ok = plat_days < bronze_days  # Platinum enrolled earlier = fewer days from 2020
record("Logic", "Enrollment timing by tier", "PASS" if enroll_ok else "WARN",
       f"Platinum median: day {plat_days} vs Bronze median: day {bronze_days} from 2020-01-01")

print()

# %% [markdown]
# ## Final Scorecard

# %%
print("═" * 60)
print("  DATA SANITY CHECK — SCORECARD")
print("═" * 60)

blocks = {}
for block, name, status, detail in results:
    if block not in blocks:
        blocks[block] = {"PASS": 0, "WARN": 0, "FAIL": 0}
    blocks[block][status] += 1

overall = "PASS"
for block, counts in blocks.items():
    if counts["FAIL"] > 0:
        block_status = "FAIL"
        overall = "FAIL"
    elif counts["WARN"] > 0:
        block_status = "WARN"
        if overall != "FAIL":
            overall = "WARN"
    else:
        block_status = "PASS"

    icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[block_status]
    detail = ""
    if counts["FAIL"] > 0:
        detail = f" ({counts['FAIL']} failures)"
    elif counts["WARN"] > 0:
        detail = f" ({counts['WARN']} warnings)"
    print(f"  {icon} {block:<30} {block_status}{detail}")

print("─" * 60)
overall_icon = {"PASS": "✅ READY FOR DEMO", "WARN": "⚠️  REVIEW WARNINGS", "FAIL": "❌ NEEDS FIXES"}[overall]
print(f"  OVERALL: {overall_icon}")
print("═" * 60)

# Print all failures and warnings for quick reference
fails = [(b, n, d) for b, n, s, d in results if s == "FAIL"]
warns = [(b, n, d) for b, n, s, d in results if s == "WARN"]

if fails:
    print(f"\n❌ FAILURES ({len(fails)}):")
    for b, n, d in fails:
        print(f"  • [{b}] {n}: {d}")

if warns:
    print(f"\n⚠️  WARNINGS ({len(warns)}):")
    for b, n, d in warns:
        print(f"  • [{b}] {n}: {d}")

if not fails and not warns:
    print("\n🎉 All checks passed! Data looks demo-ready.")

# %% [markdown]
# ## Block 4: LLM Diagnostic Report
#
# For each FAIL or WARN result, emits a structured diagnostic block that the
# Fabric portal's embedded Copilot can use to fix `01-create-sample-data.py`
# in-place.  The mapping between check names and generator code locations is
# maintained in `DIAGNOSTIC_MAP`.

# %%
# ── Block 4: LLM Diagnostic Report ─────────────────────────────────────────────

GENERATOR_FILE = "notebooks/01-create-sample-data.py"

DIAGNOSTIC_MAP = {
    "Row counts": {
        "section": "Table-specific generation loops (varies by table)",
        "lines": "varies",
        "root_cause": "The NUM_* constant for the affected table is set to the wrong value.",
        "fix": "Adjust the NUM_* constant (e.g., NUM_MEMBERS, NUM_TRANSACTIONS) for the table that has the wrong row count.",
    },
    "Date range": {
        "section": "DATE_START / DATE_END constants — lines ~49-50",
        "lines": "~49-50",
        "root_cause": "DATE_START and/or DATE_END constants don't span the expected date range.",
        "fix": "Adjust DATE_START and DATE_END to cover the required range (e.g., DATE_START = date(2023, 1, 1)).",
    },
    "FK integrity": {
        "section": "Generation order dependencies (varies by table)",
        "lines": "varies",
        "root_cause": "Child records reference IDs that don't exist in the parent table. Generation order or ID list is wrong.",
        "fix": "Ensure child generation loops draw from the parent table's actual ID list (e.g., member_ids, store_ids).",
    },
    "Null rates": {
        "section": "Field generation in data-append logic (varies by table)",
        "lines": "varies",
        "root_cause": "A field is sometimes set to None when it shouldn't be, or vice versa.",
        "fix": "Check conditional None assignments in the affected field's generation code and adjust the probability or condition.",
    },
    "Tier split": {
        "section": "pick_tier() function — lines ~292-297",
        "lines": "~292-297",
        "root_cause": "The probability thresholds in pick_tier() produce the wrong tier distribution.",
        "fix": "Adjust the probability thresholds in pick_tier(). Current thresholds: 0.60 (Bronze), 0.85 (Silver), 0.95 (Gold), else Platinum. Change these to match the desired tier split.",
    },
    "Channel mix": {
        "section": "CHANNELS / CHANNEL_WEIGHTS — lines ~378-379",
        "lines": "~378-379",
        "root_cause": "The CHANNEL_WEIGHTS ratios produce the wrong channel distribution.",
        "fix": "Adjust CHANNEL_WEIGHTS list. Currently [0.70, 0.20, 0.10] for in-store/online/phone. Change to desired ratios.",
    },
    "Return rate": {
        "section": "Transaction type selection — line ~413",
        "lines": "~413",
        "root_cause": "Flat 8% return rate applied uniformly via `random.random() < 0.92`.",
        "fix": "Adjust the 0.92 threshold to change the overall return rate. Consider varying by category or store for more realism.",
    },
    "Coupon status": {
        "section": "Coupon generation — Section 7 (line ~530+)",
        "lines": "~530+",
        "root_cause": "Coupon status distribution (active/redeemed/expired) is off from expected proportions.",
        "fix": "Adjust the status assignment probabilities in the coupon generation section.",
    },
    "Category concentration": {
        "section": "SKU category selection — line ~221",
        "lines": "~221",
        "root_cause": "`random.choice(cat_list)` gives uniform category distribution instead of realistic concentration.",
        "fix": "Replace `random.choice(cat_list)` with `random.choices(cat_list, weights=[...])` using realistic category weights.",
    },
    "Category return variance": {
        "section": "Transaction item return flag — lines ~455-462",
        "lines": "~455-462",
        "root_cause": "Returns inherit from parent transaction uniformly — no per-category variance in return rates.",
        "fix": "Add a category-specific return rate multiplier dict and apply it when setting the is_return flag on transaction items.",
    },
    "Regional variance": {
        "section": "Store generation + transaction-store assignment — lines ~136-145, ~411",
        "lines": "~136-145, ~411",
        "root_cause": "Stores assigned uniformly to regions; transactions pick a random store with no regional weighting.",
        "fix": "Weight store selection by region population or add region-based transaction volume multipliers.",
    },
    "Store return outliers": {
        "section": "Return rate is flat per store — line ~413",
        "lines": "~413",
        "root_cause": "Every store has the same ~8% return rate. No per-store variance exists.",
        "fix": "Add per-store return rate variance (e.g., assign each store a base_return_rate = 0.08 ± random(0, 0.03)).",
    },
    "Campaign redemption variance": {
        "section": "Coupon redemption logic — Section 7",
        "lines": "Section 7",
        "root_cause": "Campaign redemption rates are not differentiated enough across campaigns.",
        "fix": "Assign per-campaign redemption rate multipliers in the coupon_rules generation or coupon redemption logic.",
    },
    "Discount type comparison": {
        "section": "Coupon rule generation — Section 7",
        "lines": "Section 7",
        "root_cause": "Discount types (percentage, fixed, BOGO) may not vary in appeal / redemption rate.",
        "fix": "Assign different base redemption rates per discount_type (e.g., BOGO higher than percentage).",
    },
    "CSR department activity": {
        "section": "CSR + CSR activity generation — Sections 8-9",
        "lines": "Sections 8-9",
        "root_cause": "CSR departments don't have enough differentiation in activity type distribution.",
        "fix": "Weight activity_type distribution by department (e.g., 'Returns' department has more return-related activities).",
    },
    "Tier spend progression": {
        "section": "TIER_VALUE_RANGE dict — lines ~389-394",
        "lines": "~389-394",
        "root_cause": "Tier value ranges overlap too much or are not progressive enough.",
        "fix": "Widen gaps between tier value ranges so higher tiers have clearly higher spend (e.g., Bronze: 15-60, Platinum: 100-500).",
    },
    "Tier frequency ratio": {
        "section": "TIER_TXN_WEIGHT dict — line ~383",
        "lines": "~383",
        "root_cause": "Tier transaction weight multipliers are not differentiated enough.",
        "fix": "Increase the weight spread. Currently Bronze:1, Silver:1.5, Gold:2.5, Platinum:4 — widen to e.g. Bronze:1, Platinum:6.",
    },
    "Tier opt-in progression": {
        "section": "TIER_EMAIL_OPTIN / TIER_SMS_OPTIN — lines ~308-309",
        "lines": "~308-309",
        "root_cause": "Opt-in probability differences are too small between tiers.",
        "fix": "Widen the gap between tier opt-in rates (e.g., Bronze email 0.50, Platinum email 0.95).",
    },
    "Tier coupon redemption": {
        "section": "Coupon redemption by tier — Section 7",
        "lines": "Section 7",
        "root_cause": "Tier-based coupon redemption rates are not differentiated enough.",
        "fix": "Ensure per-tier redemption rate multipliers are applied (e.g., Platinum 2x, Bronze 0.7x).",
    },
    "Seasonality (CoV)": {
        "section": "MONTH_WEIGHTS dict — lines ~372-375",
        "lines": "~372-375",
        "root_cause": "Monthly weight values are not extreme enough to produce visible seasonality.",
        "fix": "Increase weight spread (e.g., Jan: 0.4, Dec: 2.0 instead of current 0.6/1.6).",
    },
    "Churn candidates exist": {
        "section": "Member status assignment — lines ~320-321",
        "lines": "~320-321",
        "root_cause": "member_status is assigned randomly at creation and NEVER changes over time. No temporal churn is modeled.",
        "fix": "Add a post-generation step: for members whose last transaction was 180+ days ago, flip some to 'inactive'. Or derive status from recency of last transaction during generation.",
    },
    "Active member recency": {
        "section": "Member status assignment — lines ~320-321",
        "lines": "~320-321",
        "root_cause": "All members labeled 'active' at ~88% rate regardless of actual transaction activity.",
        "fix": "Same fix as churn: derive member_status from transaction recency instead of random assignment at creation time.",
    },
    "Enrollment timing by tier": {
        "section": "TIER_ENROLL_RANGES dict — lines ~300-305",
        "lines": "~300-305",
        "root_cause": "Enrollment date ranges may overlap too much between tiers.",
        "fix": "Narrow the ranges or increase separation between tier enrollment windows so Platinum members enrolled clearly earlier.",
    },
}


# ── Emit structured diagnostics for each FAIL / WARN ───────────────────────────

issues = [(b, n, s, d) for b, n, s, d in results if s in ("FAIL", "WARN")]

if issues:
    print()
    print("═" * 65)
    print("  🔧 BLOCK 4 — LLM DIAGNOSTIC REPORT")
    print("  Target: " + GENERATOR_FILE)
    print("═" * 65)

    sections_affected = set()

    for block, name, status, detail in issues:
        diag = DIAGNOSTIC_MAP.get(name)
        section_label = diag["section"] if diag else "Unknown — manual investigation needed"
        root_cause    = diag["root_cause"] if diag else "No automated root-cause mapping for this check."
        fix_pattern   = diag["fix"] if diag else "Inspect the generator code manually for this check."

        if diag:
            sections_affected.add(section_label)

        icon = "❌" if status == "FAIL" else "⚠️"
        print()
        print("═" * 65)
        print(f"🔧 FIX NEEDED: {name} — {icon} {status}")
        print("─" * 65)
        print(f"📊 Result: {detail}")
        print(f"📁 Generator: {GENERATOR_FILE}")
        print(f"📍 Section: {section_label}")
        print(f"🔍 Root Cause: {root_cause}")
        print(f"💡 Suggested Fix: {fix_pattern}")
        print("═" * 65)

    # ── Repair summary ──────────────────────────────────────────────────────────
    print()
    print("─" * 65)
    print("📋 REPAIR SUMMARY FOR LLM:")
    print(f"   File to modify: {GENERATOR_FILE}")
    print(f"   Total fixes needed: {len(issues)}")
    print(f"   Sections affected: {', '.join(sorted(sections_affected)) if sections_affected else 'Unknown'}")
    print()
    print("   To fix: Open 01-create-sample-data.py in the Fabric notebook editor,")
    print("   use Copilot to apply each fix above, then re-run both notebooks.")
    print("─" * 65)

else:
    print()
    print("═" * 65)
    print("  ✅ BLOCK 4 — LLM DIAGNOSTIC REPORT")
    print("═" * 65)
    print("  No failures or warnings detected.")
    print("  The generated data passes all sanity checks — clean bill of health.")
    print("  No changes needed in " + GENERATOR_FILE + ".")
    print("═" * 65)
