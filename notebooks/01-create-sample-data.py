# %% [markdown]
# # AAP Loyalty Program — Sample Data Generator
# 
# **Purpose:** Creates Delta tables in the default Lakehouse that simulate what a
# PostgreSQL mirror from AAP's loyalty database would produce in Fabric OneLake.
#
# **Usage:** Import into a Fabric Lakehouse notebook, attach a Lakehouse, and Run All.
# Tables are written to the default Lakehouse database (no schema prefix — Fabric
# Lakehouse Spark does not support CREATE SCHEMA or custom schema prefixes).
#
# **Tables created (10):**
# | Table | ~Rows | Description |
# |---|---|---|
# | loyalty_members | 50,000 | Member profiles and tier info |
# | transactions | 500,000 | 3 years of purchase/return transactions |
# | transaction_items | 1,500,000 | Line items per transaction |
# | member_points | 500,000 | Points activity ledger |
# | coupons | 200,000 | Coupon issuance and redemption |
# | coupon_rules | 100 | Campaign-aware coupon rule definitions |
# | csr | 500 | Customer Service Rep profiles |
# | csr_activities | 50,000 | CSR audit trail |
# | sku_reference | 5,000 | Product/SKU catalog |
# | stores | 500 | Store reference data |
#
# **Data spans:** 2023-01-01 to 2026-04-01
# **Deterministic:** Uses fixed random seed for reproducibility.
#
# **Distribution improvements over v1:**
# - Tier-correlated transaction frequency (Platinum shops ~3x more than Bronze)
# - Named campaign system with seasonal windows and tier targeting
# - Tier-based coupon redemption rates (Platinum 55% → Bronze 25%)
# - Higher-tier members enrolled earlier, opt-in to comms more
# - Seasonal patterns strengthened (holiday spike, spring maintenance surge)
# - Points correlated with real transaction amounts and tier multipliers

# %%
import random
from datetime import datetime, timedelta, date
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql import functions as F

spark = SparkSession.builder.getOrCreate()

SEED = 42
random.seed(SEED)

# Date range helpers
DATE_START = date(2023, 1, 1)
DATE_END = date(2026, 4, 1)
TOTAL_DAYS = (DATE_END - DATE_START).days

def rand_date(start=DATE_START, end=DATE_END):
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_datetime(start=DATE_START, end=DATE_END):
    d = rand_date(start, end)
    return datetime(d.year, d.month, d.day,
                    random.randint(6, 21), random.randint(0, 59), random.randint(0, 59))

def ts_now():
    return datetime(2026, 4, 1, 0, 0, 0)

# %% [markdown]
# ## 1. Stores — Reference data for transaction locations

# %%
NUM_STORES = 500
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
STATES_BY_REGION = {
    "Northeast": ["NY", "NJ", "PA", "CT", "MA", "NH", "ME", "VT", "RI"],
    "Southeast": ["FL", "GA", "NC", "SC", "VA", "TN", "AL", "MS", "LA", "KY"],
    "Midwest": ["OH", "MI", "IL", "IN", "WI", "MN", "MO", "IA", "KS", "NE"],
    "Southwest": ["TX", "AZ", "NM", "OK", "AR"],
    "West": ["CA", "WA", "OR", "CO", "NV", "UT", "ID", "MT"],
}
CITIES = {
    "NY": ["New York", "Buffalo", "Rochester"], "NJ": ["Newark", "Jersey City", "Trenton"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown"], "CT": ["Hartford", "New Haven"],
    "MA": ["Boston", "Worcester", "Springfield"], "FL": ["Miami", "Orlando", "Tampa", "Jacksonville"],
    "GA": ["Atlanta", "Savannah", "Augusta"], "NC": ["Charlotte", "Raleigh", "Durham"],
    "SC": ["Charleston", "Columbia"], "VA": ["Richmond", "Norfolk", "Arlington"],
    "TN": ["Nashville", "Memphis", "Knoxville"], "TX": ["Houston", "Dallas", "Austin", "San Antonio"],
    "AZ": ["Phoenix", "Tucson", "Scottsdale"], "OH": ["Columbus", "Cleveland", "Cincinnati"],
    "MI": ["Detroit", "Grand Rapids", "Ann Arbor"], "IL": ["Chicago", "Springfield", "Naperville"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento"],
    "WA": ["Seattle", "Spokane", "Tacoma"], "CO": ["Denver", "Colorado Springs", "Boulder"],
    "IN": ["Indianapolis", "Fort Wayne"], "WI": ["Milwaukee", "Madison"],
    "MN": ["Minneapolis", "St. Paul"], "MO": ["Kansas City", "St. Louis"],
    "AL": ["Birmingham", "Montgomery"], "LA": ["New Orleans", "Baton Rouge"],
    "OK": ["Oklahoma City", "Tulsa"], "OR": ["Portland", "Eugene"],
    "NV": ["Las Vegas", "Reno"], "UT": ["Salt Lake City", "Provo"],
    "NM": ["Albuquerque", "Santa Fe"], "AR": ["Little Rock"],
    "KY": ["Louisville", "Lexington"], "MS": ["Jackson"],
    "NH": ["Manchester", "Nashua"], "ME": ["Portland"], "VT": ["Burlington"],
    "RI": ["Providence"], "IA": ["Des Moines"], "KS": ["Wichita"],
    "NE": ["Omaha"], "ID": ["Boise"], "MT": ["Billings"],
}

stores_data = []
for i in range(1, NUM_STORES + 1):
    region = random.choice(REGIONS)
    state = random.choice(STATES_BY_REGION[region])
    city = random.choice(CITIES.get(state, [state + " City"]))
    store_type = "retail" if random.random() < 0.85 else "hub"
    stores_data.append((
        i, f"AAP Store #{4000 + i}", city, state,
        f"{random.randint(10000, 99999)}", region, store_type,
        rand_date(date(2005, 1, 1), date(2023, 6, 1))
    ))

stores_schema = StructType([
    StructField("store_id", IntegerType(), False),
    StructField("store_name", StringType(), False),
    StructField("city", StringType()), StructField("state", StringType()),
    StructField("zip_code", StringType()), StructField("region", StringType()),
    StructField("store_type", StringType()),
    StructField("opened_date", DateType()),
])
df_stores = spark.createDataFrame(stores_data, stores_schema)
df_stores.write.format("delta").mode("overwrite").saveAsTable("stores")
print(f"✅ stores: {df_stores.count()} rows")

# %% [markdown]
# ## 2. SKU Reference — Auto parts product catalog (5,000 SKUs)

# %%
NUM_SKUS = 5000

CATEGORIES = {
    "Batteries": {
        "subcategories": ["Car Batteries", "Truck Batteries", "Marine Batteries", "Battery Accessories"],
        "brands": ["DieHard", "Optima", "ACDelco", "Interstate", "EverStart"],
        "price_range": (89.99, 249.99), "names": ["Battery", "AGM Battery", "Deep Cycle Battery"]
    },
    "Engine Oil": {
        "subcategories": ["Conventional Oil", "Synthetic Oil", "Synthetic Blend", "High Mileage"],
        "brands": ["Mobil 1", "Castrol", "Valvoline", "Pennzoil", "Royal Purple"],
        "price_range": (4.99, 42.99), "names": ["Motor Oil 5W-30", "Full Synthetic 5W-20", "High Mileage 10W-30", "Oil 0W-20"]
    },
    "Brakes": {
        "subcategories": ["Brake Pads", "Brake Rotors", "Brake Calipers", "Brake Fluid"],
        "brands": ["Brembo", "Wagner", "ACDelco", "Bosch", "Power Stop"],
        "price_range": (12.99, 189.99), "names": ["Ceramic Brake Pads", "Drilled Rotor", "Brake Caliper", "DOT 4 Brake Fluid"]
    },
    "Filters": {
        "subcategories": ["Oil Filters", "Air Filters", "Cabin Air Filters", "Fuel Filters"],
        "brands": ["Fram", "K&N", "Bosch", "Purolator", "WIX"],
        "price_range": (5.99, 34.99), "names": ["Oil Filter", "Engine Air Filter", "Cabin Filter", "Fuel Filter"]
    },
    "Wipers": {
        "subcategories": ["Wiper Blades", "Wiper Arms", "Wiper Fluid"],
        "brands": ["Rain-X", "Bosch", "Michelin", "ANCO", "Trico"],
        "price_range": (3.99, 29.99), "names": ["Beam Wiper Blade", "Conventional Wiper", "Windshield Washer Fluid"]
    },
    "Spark Plugs": {
        "subcategories": ["Iridium Plugs", "Platinum Plugs", "Copper Plugs", "Plug Wires"],
        "brands": ["NGK", "Denso", "Bosch", "Champion", "Autolite"],
        "price_range": (2.99, 18.99), "names": ["Iridium Spark Plug", "Platinum Spark Plug", "Copper Core Plug", "Spark Plug Wire Set"]
    },
    "Lighting": {
        "subcategories": ["Headlights", "Tail Lights", "Fog Lights", "Bulbs"],
        "brands": ["Sylvania", "Philips", "GE", "Hella", "Osram"],
        "price_range": (4.99, 79.99), "names": ["LED Headlight Bulb", "Halogen Bulb", "Fog Light Assembly", "Tail Light Bulb"]
    },
    "Coolant": {
        "subcategories": ["Antifreeze", "Coolant Additives", "Radiator Hoses", "Thermostats"],
        "brands": ["Prestone", "Zerex", "Peak", "Motorcraft"],
        "price_range": (6.99, 44.99), "names": ["Antifreeze/Coolant", "Radiator Hose", "Thermostat", "Coolant Additive"]
    },
    "Accessories": {
        "subcategories": ["Floor Mats", "Seat Covers", "Phone Mounts", "Air Fresheners", "Tools"],
        "brands": ["WeatherTech", "FH Group", "Chemical Guys", "Armor All"],
        "price_range": (2.99, 89.99), "names": ["Floor Mat Set", "Seat Cover", "Dash Mount", "Tire Pressure Gauge", "Microfiber Cloth"]
    },
    "Electrical": {
        "subcategories": ["Alternators", "Starters", "Fuses", "Relays", "Wiring"],
        "brands": ["Denso", "Bosch", "ACDelco", "Remy", "Standard Motor"],
        "price_range": (3.99, 299.99), "names": ["Alternator", "Starter Motor", "Fuse Kit", "Relay", "Wiring Harness"]
    },
}

sku_data = []
cat_list = list(CATEGORIES.keys())
for i in range(1, NUM_SKUS + 1):
    cat = random.choice(cat_list)
    info = CATEGORIES[cat]
    subcat = random.choice(info["subcategories"])
    brand = random.choice(info["brands"])
    name = f"{brand} {random.choice(info['names'])}"
    price = round(random.uniform(*info["price_range"]), 2)
    sku_code = f"AAP-{cat[:3].upper()}-{i:05d}"
    is_bonus = random.random() < 0.15
    is_skip = random.random() < 0.05
    sku_data.append((
        sku_code, name, cat, subcat, brand, price,
        is_bonus, is_skip, ts_now()
    ))

sku_schema = StructType([
    StructField("sku", StringType(), False),
    StructField("product_name", StringType()), StructField("category", StringType()),
    StructField("subcategory", StringType()), StructField("brand", StringType()),
    StructField("unit_price", DoubleType()),
    StructField("is_bonus_eligible", BooleanType()),
    StructField("is_skip_sku", BooleanType()),
    StructField("created_at", TimestampType()),
])
df_skus = spark.createDataFrame(sku_data, sku_schema)
df_skus.write.format("delta").mode("overwrite").saveAsTable("sku_reference")
print(f"✅ sku_reference: {df_skus.count()} rows")

# Build lookup for transaction item generation
sku_lookup = [(r[0], r[1], r[2], r[5]) for r in sku_data]

# %% [markdown]
# ## 3. Loyalty Members — 50,000 member profiles with realistic tier distribution
#
# **Distribution:** 60% Bronze (30K), 25% Silver (12.5K), 10% Gold (5K), 5% Platinum (2.5K)
#
# Higher tiers have earlier enrollment dates (they've been loyal longer) and are
# more likely to opt-in to email/SMS communications.

# %%
NUM_MEMBERS = 50000

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Andrew", "Kimberly", "Paul", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Jason", "Rebecca", "Edward", "Sharon",
    "Ryan", "Laura", "Jacob", "Cynthia", "Gary", "Kathleen", "Nicholas", "Amy",
    "Eric", "Angela", "Jonathan", "Shirley", "Stephen", "Anna", "Larry", "Brenda",
    "Justin", "Pamela", "Scott", "Emma", "Brandon", "Nicole", "Benjamin", "Helen",
    "Samuel", "Samantha", "Raymond", "Katherine", "Gregory", "Christine", "Frank", "Debra",
    "Alexander", "Rachel", "Patrick", "Carolyn", "Jack", "Janet", "Dennis", "Catherine",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales",
    "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson",
    "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward",
]
ENROLLMENT_SOURCES = ["POS", "Ecomm", "CustomerFirst"]
MEMBER_STATUSES = ["active", "inactive", "suspended"]

# Tier distribution: 60% Bronze, 25% Silver, 10% Gold, 5% Platinum
def pick_tier():
    r = random.random()
    if r < 0.60: return "Bronze"
    if r < 0.85: return "Silver"
    if r < 0.95: return "Gold"
    return "Platinum"

# Higher tiers enrolled earlier (they've been loyal longer)
TIER_ENROLL_RANGES = {
    "Platinum": (date(2020, 1, 1), date(2023, 6, 1)),   # earliest enrollees
    "Gold":     (date(2020, 1, 1), date(2024, 3, 1)),
    "Silver":   (date(2021, 1, 1), date(2025, 6, 1)),
    "Bronze":   (date(2022, 1, 1), date(2026, 3, 1)),    # includes recent sign-ups
}

# Higher tiers more likely to opt-in
TIER_EMAIL_OPTIN = {"Platinum": 0.92, "Gold": 0.85, "Silver": 0.75, "Bronze": 0.65}
TIER_SMS_OPTIN   = {"Platinum": 0.78, "Gold": 0.65, "Silver": 0.48, "Bronze": 0.35}

members_data = []
for i in range(1, NUM_MEMBERS + 1):
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    email = f"{fn.lower()}.{ln.lower()}{random.randint(1, 999)}@{'gmail.com' if random.random() < 0.5 else 'yahoo.com' if random.random() < 0.5 else 'outlook.com'}"
    phone = f"{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
    tier = pick_tier()
    enroll_start, enroll_end = TIER_ENROLL_RANGES[tier]
    enroll = rand_date(enroll_start, enroll_end)
    status_r = random.random()
    status = "active" if status_r < 0.88 else ("inactive" if status_r < 0.97 else "suspended")
    diy_id = f"DIY-{random.randint(100000, 999999)}" if random.random() < 0.35 else None
    created = datetime(enroll.year, enroll.month, enroll.day, random.randint(8, 20), random.randint(0, 59), 0)
    updated = rand_datetime(enroll, DATE_END)
    members_data.append((
        i, fn, ln, email, phone, enroll,
        random.choice(ENROLLMENT_SOURCES), status, tier,
        random.random() < TIER_EMAIL_OPTIN[tier],
        random.random() < TIER_SMS_OPTIN[tier],
        diy_id, created, updated
    ))

members_schema = StructType([
    StructField("member_id", LongType(), False),
    StructField("first_name", StringType()), StructField("last_name", StringType()),
    StructField("email", StringType()), StructField("phone", StringType()),
    StructField("enrollment_date", DateType()),
    StructField("enrollment_source", StringType()),
    StructField("member_status", StringType()), StructField("tier", StringType()),
    StructField("opt_in_email", BooleanType()), StructField("opt_in_sms", BooleanType()),
    StructField("diy_account_id", StringType()),
    StructField("created_at", TimestampType()), StructField("updated_at", TimestampType()),
])
df_members = spark.createDataFrame(members_data, members_schema)
df_members.write.format("delta").mode("overwrite").saveAsTable("loyalty_members")
print(f"✅ loyalty_members: {df_members.count()} rows")

# Print tier breakdown for validation
tier_counts = {}
for m in members_data:
    tier_counts[m[8]] = tier_counts.get(m[8], 0) + 1
print(f"   Tier breakdown: {dict(sorted(tier_counts.items()))}")

# %% [markdown]
# ## 4. Transactions — 500,000 transactions with tier-correlated frequency
# 
# **Tier weighting:** Platinum members generate ~3x more transactions than Bronze.
# Uses weighted member selection so higher-tier members appear more frequently.
#
# **Seasonal patterns (strengthened):**
# - Holiday spike in Nov-Dec (weight 1.4-1.6)
# - Spring maintenance surge in Mar-May (weight 1.2-1.4)
# - Summer steady (weight 1.1-1.2)
# - Jan-Feb winter lull (weight 0.6-0.7)
#
# **Value correlation:** Higher-tier members have higher average transaction values.

# %%
NUM_TRANSACTIONS = 500000

# Strengthened seasonal weights (bigger swings than v1)
MONTH_WEIGHTS = {
    1: 0.6, 2: 0.7, 3: 1.2, 4: 1.4, 5: 1.3, 6: 1.2,
    7: 1.1, 8: 1.0, 9: 0.9, 10: 0.9, 11: 1.4, 12: 1.6,
}
MAX_MONTH_WEIGHT = max(MONTH_WEIGHTS.values())

CHANNELS = ["in-store", "online", "mobile"]
CHANNEL_WEIGHTS = [0.70, 0.20, 0.10]

# Tier-correlated member selection weights
# Platinum gets 4x, Gold 2.5x, Silver 1.5x, Bronze 1.0x the chance of being picked
TIER_TXN_WEIGHT = {"Bronze": 1.0, "Silver": 1.5, "Gold": 2.5, "Platinum": 4.0}
member_ids = list(range(1, NUM_MEMBERS + 1))
member_tiers = {m[0]: m[8] for m in members_data}
member_weights = [TIER_TXN_WEIGHT[member_tiers[mid]] for mid in member_ids]

# Tier-based transaction value ranges (higher tiers spend more per visit)
TIER_VALUE_RANGE = {
    "Bronze":   (5.0, 300.0),
    "Silver":   (10.0, 400.0),
    "Gold":     (15.0, 550.0),
    "Platinum": (25.0, 700.0),
}

store_ids = list(range(1, NUM_STORES + 1))

def weighted_random_date():
    """Accept/reject sampling for seasonal transaction distribution."""
    d = rand_date()
    while random.random() > MONTH_WEIGHTS[d.month] / MAX_MONTH_WEIGHT:
        d = rand_date()
    return d

# Generate transactions in batches of 50K to avoid one giant list comprehension
print("Generating 500K transactions...")
transactions_data = []
for i in range(1, NUM_TRANSACTIONS + 1):
    mid = random.choices(member_ids, weights=member_weights, k=1)[0]
    tier = member_tiers[mid]
    sid = random.choice(store_ids)
    tdate = weighted_random_date()
    ttype = "purchase" if random.random() < 0.92 else "return"
    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
    item_count = random.choices([1, 2, 3, 4, 5, 6], weights=[25, 30, 20, 12, 8, 5], k=1)[0]
    vmin, vmax = TIER_VALUE_RANGE[tier]
    subtotal = round(random.uniform(vmin, vmax), 2)
    tax = round(subtotal * random.uniform(0.05, 0.10), 2)
    total = round(subtotal + tax, 2)
    if ttype == "return":
        total = -abs(total)
        subtotal = -abs(subtotal)
        tax = -abs(tax)
    order_id = f"ORD-{random.randint(10000000, 99999999)}" if channel in ("online", "mobile") else None
    created = datetime(tdate.year, tdate.month, tdate.day,
                       random.randint(7, 20), random.randint(0, 59), random.randint(0, 59))
    transactions_data.append((
        i, mid, sid, tdate, ttype, subtotal, tax, total, item_count, channel, order_id, created
    ))
    if i % 100000 == 0:
        print(f"   ...{i:,} transactions generated")

txn_schema = StructType([
    StructField("transaction_id", LongType(), False),
    StructField("member_id", LongType()), StructField("store_id", IntegerType()),
    StructField("transaction_date", DateType()), StructField("transaction_type", StringType()),
    StructField("subtotal", DoubleType()), StructField("tax", DoubleType()),
    StructField("total", DoubleType()), StructField("item_count", IntegerType()),
    StructField("channel", StringType()), StructField("order_id", StringType()),
    StructField("created_at", TimestampType()),
])
df_txn = spark.createDataFrame(transactions_data, txn_schema)
df_txn.write.format("delta").mode("overwrite").saveAsTable("transactions")
print(f"✅ transactions: {df_txn.count()} rows")

# %% [markdown]
# ## 5. Transaction Items — ~1,500,000 line items (3 per transaction avg)

# %%
print("Generating ~1.5M transaction items...")
items_data = []
item_id = 1
for txn in transactions_data:
    txn_id = txn[0]
    is_return = txn[4] == "return"
    num_items = txn[8]  # item_count
    for _ in range(num_items):
        sku_code, prod_name, cat, unit_price = random.choice(sku_lookup)
        qty = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5], k=1)[0]
        line_total = round(unit_price * qty, 2)
        if is_return:
            line_total = -line_total
        items_data.append((
            item_id, txn_id, sku_code, prod_name, cat, qty, unit_price, line_total, is_return
        ))
        item_id += 1
    if txn_id % 100000 == 0:
        print(f"   ...items for {txn_id:,} transactions generated ({len(items_data):,} items)")

items_schema = StructType([
    StructField("item_id", LongType(), False),
    StructField("transaction_id", LongType()), StructField("sku", StringType()),
    StructField("product_name", StringType()), StructField("category", StringType()),
    StructField("quantity", IntegerType()), StructField("unit_price", DoubleType()),
    StructField("line_total", DoubleType()), StructField("is_return", BooleanType()),
])
df_items = spark.createDataFrame(items_data, items_schema)
df_items.write.format("delta").mode("overwrite").saveAsTable("transaction_items")
print(f"✅ transaction_items: {df_items.count()} rows")

# %% [markdown]
# ## 6. Member Points — 500,000 points activity records
#
# Points rules: 1 pt/dollar for Bronze/Silver, 1.5x for Gold, 2x for Platinum.
# Activity types: earn, redeem, expire, adjust, bonus.
#
# **Improvements:** Earn events reference real transaction amounts. Bonus events
# tie to campaign windows (double-points weeks). Higher-tier members accumulate
# more points from both higher spend and tier multipliers.

# %%
NUM_POINTS = 500000

TIER_MULTIPLIER = {"Bronze": 1.0, "Silver": 1.0, "Gold": 1.5, "Platinum": 2.0}
POINT_SOURCES = ["purchase", "campaign", "bonus_activity", "manual_adjust"]
ACTIVITY_TYPES = ["earn", "redeem", "expire", "adjust", "bonus"]
ACTIVITY_WEIGHTS = [55, 20, 10, 5, 10]

# Pre-build a map of member_id -> list of (txn_date, abs_total) for realistic earn references.
# To avoid O(n^2), sample a subset of transactions per member.
member_txn_lookup = {}
for txn in transactions_data:
    mid = txn[1]
    if mid not in member_txn_lookup:
        member_txn_lookup[mid] = []
    # Only keep purchase transactions, and cap at 20 per member to save memory
    if txn[4] == "purchase" and len(member_txn_lookup[mid]) < 20:
        member_txn_lookup[mid].append((txn[0], txn[3], abs(txn[7])))  # txn_id, date, abs_total

# Double-points campaign windows (tied to major campaigns)
BONUS_WINDOWS = [
    (date(2023, 11, 20), date(2023, 12, 5)),   # Holiday Blitz double-points
    (date(2024, 3, 10), date(2024, 3, 24)),     # Spring Tune-Up double-points
    (date(2024, 6, 15), date(2024, 6, 30)),     # Summer Road Trip double-points
    (date(2024, 11, 20), date(2024, 12, 5)),    # Holiday Blitz double-points
    (date(2025, 3, 10), date(2025, 3, 24)),     # Spring Tune-Up double-points
    (date(2025, 6, 15), date(2025, 6, 30)),     # Summer Road Trip double-points
    (date(2025, 11, 20), date(2025, 12, 5)),    # Holiday Blitz double-points
]

def is_in_bonus_window(d):
    for ws, we in BONUS_WINDOWS:
        if ws <= d <= we:
            return True
    return False

# Use tier-weighted member selection so higher-tier members get more points activity
print("Generating 500K points records...")
points_data = []
member_balances = {}
for i in range(1, NUM_POINTS + 1):
    mid = random.choices(member_ids, weights=member_weights, k=1)[0]
    tier = member_tiers[mid]
    mult = TIER_MULTIPLIER[tier]
    atype = random.choices(ACTIVITY_TYPES, weights=ACTIVITY_WEIGHTS, k=1)[0]
    adate = rand_date()

    if atype == "earn":
        # Try to reference a real transaction for this member
        txns = member_txn_lookup.get(mid)
        if txns:
            ref_txn = random.choice(txns)
            ref_id = str(ref_txn[0])
            base_pts = int(ref_txn[2] * mult)  # points from transaction total
            adate = ref_txn[1]  # use actual transaction date
        else:
            ref_id = str(random.randint(1, NUM_TRANSACTIONS))
            base_pts = int(random.uniform(5, 250) * mult)
        # Double points during bonus windows
        if is_in_bonus_window(adate):
            base_pts = base_pts * 2
        pts = max(1, base_pts)
        source = "purchase"
        desc = f"Points earned on purchase #{ref_id}"
    elif atype == "redeem":
        pts = -random.randint(50, 500)
        source = "purchase"
        ref_id = str(random.randint(1, NUM_TRANSACTIONS))
        desc = f"Points redeemed on transaction #{ref_id}"
    elif atype == "expire":
        pts = -random.randint(10, 200)
        source = "purchase"
        ref_id = None
        desc = "Quarterly points expiration"
    elif atype == "bonus":
        pts = int(random.randint(25, 500) * mult)
        source = "bonus_activity"
        ref_id = f"CAMP-{random.randint(100, 999)}"
        desc = random.choice([
            "Bonus: Oil change month promo", "Bonus: Battery recycling reward",
            "Bonus: Double points weekend", "Bonus: Birthday points",
            "Bonus: Referral reward", "Bonus: Tier upgrade bonus",
            "Bonus: Holiday Blitz double points", "Bonus: Spring Tune-Up bonus",
            "Bonus: Premium Member Exclusive reward", "Bonus: Summer Road Trip promo",
        ])
    else:  # adjust
        pts = random.randint(-100, 100)
        source = "manual_adjust"
        ref_id = f"TICKET-{random.randint(10000, 99999)}"
        desc = "Manual adjustment by CSR"

    bal = member_balances.get(mid, 0) + pts
    if bal < 0:
        bal = 0
    member_balances[mid] = bal
    created = datetime(adate.year, adate.month, adate.day,
                       random.randint(6, 22), random.randint(0, 59), random.randint(0, 59))
    points_data.append((
        i, mid, adate, atype, pts, bal, source, ref_id, desc, created
    ))
    if i % 100000 == 0:
        print(f"   ...{i:,} points records generated")

points_schema = StructType([
    StructField("point_id", LongType(), False),
    StructField("member_id", LongType()), StructField("activity_date", DateType()),
    StructField("activity_type", StringType()), StructField("points_amount", IntegerType()),
    StructField("balance_after", IntegerType()), StructField("source", StringType()),
    StructField("reference_id", StringType()), StructField("description", StringType()),
    StructField("created_at", TimestampType()),
])
df_points = spark.createDataFrame(points_data, points_schema)
df_points.write.format("delta").mode("overwrite").saveAsTable("member_points")
print(f"✅ member_points: {df_points.count()} rows")

# Free large intermediate data
del member_txn_lookup

# %% [markdown]
# ## 7. Coupon Rules — 100 campaign-aware rule definitions
#
# **Campaign system:** Each campaign defines a time window, target tier(s), and weight.
# Multiple coupon rules are generated per campaign (different discount types within
# the same campaign). The `campaign_name` column groups rules by campaign.

# %%
CAMPAIGNS = [
    {"name": "Holiday Blitz",             "start": (11, 15), "end": (12, 31), "target_tiers": None,                               "weight": 3.0},
    {"name": "New Year Kickoff",          "start": (1, 1),   "end": (1, 31),  "target_tiers": None,                               "weight": 1.5},
    {"name": "Spring Tune-Up",            "start": (3, 1),   "end": (4, 30),  "target_tiers": None,                               "weight": 2.0},
    {"name": "Summer Road Trip",          "start": (6, 1),   "end": (7, 31),  "target_tiers": None,                               "weight": 2.0},
    {"name": "Back to School",            "start": (8, 1),   "end": (9, 15),  "target_tiers": None,                               "weight": 1.5},
    {"name": "Premium Member Exclusive",  "start": (1, 1),   "end": (12, 31), "target_tiers": ["Gold", "Platinum"],               "weight": 1.0},
    {"name": "Silver+ Appreciation",      "start": (1, 1),   "end": (12, 31), "target_tiers": ["Silver", "Gold", "Platinum"],     "weight": 0.8},
    {"name": "Welcome Offer",             "start": (1, 1),   "end": (12, 31), "target_tiers": None,                               "weight": 1.0},
    {"name": "Flash Sale",                "start": None,      "end": None,     "target_tiers": None,                               "weight": 0.5},
    {"name": "Birthday Reward",           "start": (1, 1),   "end": (12, 31), "target_tiers": None,                               "weight": 0.8},
]

DISCOUNT_TYPES = ["percentage", "fixed", "bogo"]

# Rule name templates per campaign — each campaign gets multiple rules
CAMPAIGN_RULE_TEMPLATES = {
    "Holiday Blitz":            ["Holiday % Off", "Holiday $ Savings", "Holiday BOGO", "Holiday Battery Deal", "Holiday Oil Special"],
    "New Year Kickoff":         ["New Year % Off", "New Year $ Off", "New Year BOGO"],
    "Spring Tune-Up":           ["Spring Brake Check", "Spring Oil Change", "Spring Filter Bundle", "Spring % Off"],
    "Summer Road Trip":         ["Summer Coolant Deal", "Summer Wiper Special", "Summer % Off", "Summer Road Kit"],
    "Back to School":           ["BTS Battery Deal", "BTS Oil Change", "BTS % Off"],
    "Premium Member Exclusive": ["VIP % Off", "VIP $ Savings", "VIP BOGO", "VIP Double Points"],
    "Silver+ Appreciation":     ["Silver+ % Off", "Silver+ $ Off", "Silver+ Bonus"],
    "Welcome Offer":            ["Welcome 15% Off", "Welcome $10 Off", "Welcome Bonus Points"],
    "Flash Sale":               ["Flash 20% Off", "Flash BOGO", "Flash $ Off"],
    "Birthday Reward":          ["Birthday % Off", "Birthday $ Gift", "Birthday Bonus Points"],
}

NUM_RULES = 100
rules_data = []
rule_id = 0

# Distribute ~100 rules across campaigns proportional to their weights
total_weight = sum(c["weight"] for c in CAMPAIGNS)
rules_per_campaign = {}
allocated = 0
for c in CAMPAIGNS:
    n = max(2, round(NUM_RULES * c["weight"] / total_weight))
    rules_per_campaign[c["name"]] = n
    allocated += n
# Adjust to hit exactly NUM_RULES
diff = NUM_RULES - allocated
if diff != 0:
    rules_per_campaign[CAMPAIGNS[0]["name"]] += diff

for campaign in CAMPAIGNS:
    cname = campaign["name"]
    templates = CAMPAIGN_RULE_TEMPLATES[cname]
    n_rules = rules_per_campaign[cname]
    target_tiers = campaign["target_tiers"]
    # Pick the primary target tier for the rule (or None for mass campaigns)
    if target_tiers:
        tier_cycle = target_tiers
    else:
        tier_cycle = [None]

    for j in range(n_rules):
        rule_id += 1
        tmpl_name = templates[j % len(templates)]
        dtype = DISCOUNT_TYPES[j % len(DISCOUNT_TYPES)]
        if dtype == "percentage":
            dval = round(random.uniform(5, 50), 2)
        elif dtype == "fixed":
            dval = round(random.uniform(3, 75), 2)
        else:  # bogo
            dval = 0.0
        min_purchase = float(random.choice([0, 10, 15, 20, 25, 30, 50]))
        valid_days = random.choice([7, 14, 30, 60, 90])
        target_tier = tier_cycle[j % len(tier_cycle)]
        rules_data.append((
            rule_id, f"{tmpl_name} #{rule_id}", f"{cname} promotion",
            dtype, dval, min_purchase, valid_days,
            random.random() < 0.80, target_tier, cname, ts_now()
        ))

rules_schema = StructType([
    StructField("rule_id", LongType(), False),
    StructField("rule_name", StringType()), StructField("description", StringType()),
    StructField("discount_type", StringType()), StructField("discount_value", DoubleType()),
    StructField("min_purchase", DoubleType()), StructField("valid_days", IntegerType()),
    StructField("is_active", BooleanType()), StructField("target_tier", StringType()),
    StructField("campaign_name", StringType()),
    StructField("created_at", TimestampType()),
])
df_rules = spark.createDataFrame(rules_data, rules_schema)
df_rules.write.format("delta").mode("overwrite").saveAsTable("coupon_rules")
print(f"✅ coupon_rules: {df_rules.count()} rows")

# Print campaign breakdown
campaign_rule_counts = {}
for r in rules_data:
    campaign_rule_counts[r[9]] = campaign_rule_counts.get(r[9], 0) + 1
for cname, cnt in campaign_rule_counts.items():
    print(f"   {cname}: {cnt} rules")

# %% [markdown]
# ## 8. Coupons — 200,000 issued coupons with campaign-aware distribution
#
# **70% of coupons** are tied to a campaign window (issued during that campaign's dates).
# **Tier targeting:** Premium campaigns (Gold/Platinum rules) only issue to eligible members.
# **Redemption rates by tier:** Platinum 55%, Gold 45%, Silver 35%, Bronze 25%.

# %%
NUM_COUPONS = 200000
SOURCE_SYSTEMS = ["GK", "POS", "Ecomm"]

# Tier-based redemption rates
TIER_REDEMPTION_RATE = {"Platinum": 0.55, "Gold": 0.45, "Silver": 0.35, "Bronze": 0.25}
# Remaining coupons split: issued (waiting), expired, voided
# These ratios apply to the non-redeemed portion
NON_REDEEMED_SPLIT = {"issued": 0.35, "expired": 0.55, "voided": 0.10}

# Data range years for campaign window date generation
DATA_YEARS = [2023, 2024, 2025, 2026]

# Build rule lookup by campaign for weighted selection
campaign_rules = {}  # campaign_name -> list of rules
for r in rules_data:
    cn = r[9]  # campaign_name
    if cn not in campaign_rules:
        campaign_rules[cn] = []
    campaign_rules[cn].append(r)

# Build campaign weights for selection (70% campaign-aware, 30% random)
campaign_weight_list = [(c["name"], c["weight"]) for c in CAMPAIGNS]
campaign_names = [cw[0] for cw in campaign_weight_list]
campaign_wts = [cw[1] for cw in campaign_weight_list]

# Build member-id lists by tier for targeted issuance
members_by_tier = {"Bronze": [], "Silver": [], "Gold": [], "Platinum": []}
for m in members_data:
    members_by_tier[m[8]].append(m[0])
all_member_ids = list(range(1, NUM_MEMBERS + 1))

def get_campaign_issue_date(campaign, year):
    """Generate an issue date within a campaign's window for a given year."""
    c = None
    for cc in CAMPAIGNS:
        if cc["name"] == campaign:
            c = cc
            break
    if not c or c["start"] is None:
        # Flash Sale: random 2-week window
        start_d = rand_date(date(year, 1, 1), min(date(year, 12, 1), DATE_END))
        end_d = min(start_d + timedelta(days=14), DATE_END)
        return rand_date(start_d, end_d)
    start_d = date(year, c["start"][0], c["start"][1])
    end_m, end_day = c["end"]
    end_d = date(year, end_m, end_day)
    # Clamp to data range
    start_d = max(start_d, DATE_START)
    end_d = min(end_d, DATE_END)
    if start_d > end_d:
        return None
    return rand_date(start_d, end_d)

print("Generating 200K coupons...")
coupons_data = []
for i in range(1, NUM_COUPONS + 1):
    is_campaign_coupon = random.random() < 0.70

    if is_campaign_coupon:
        # Pick a campaign weighted by campaign weight
        cname = random.choices(campaign_names, weights=campaign_wts, k=1)[0]
        rule = random.choice(campaign_rules[cname])
        year = random.choice(DATA_YEARS)
        issued = get_campaign_issue_date(cname, year)
        if issued is None:
            issued = rand_date()
    else:
        # Random rule, random date
        rule = random.choice(rules_data)
        issued = rand_date()

    rule_id = rule[0]
    dtype = rule[3]
    dval = rule[4]
    target_tier = rule[8]  # target_tier from the rule
    valid_days = rule[6]

    # Assign member — respect tier targeting
    if target_tier and random.random() < 0.85:
        eligible_tiers = []
        if target_tier == "Gold":
            eligible_tiers = ["Gold", "Platinum"]
        elif target_tier == "Platinum":
            eligible_tiers = ["Platinum"]
        elif target_tier == "Silver":
            eligible_tiers = ["Silver", "Gold", "Platinum"]
        else:
            eligible_tiers = [target_tier]
        eligible_members = []
        for t in eligible_tiers:
            eligible_members.extend(members_by_tier.get(t, []))
        mid = random.choice(eligible_members) if eligible_members else random.choice(all_member_ids)
    elif random.random() < 0.85:
        mid = random.choice(all_member_ids)
    else:
        mid = None  # anonymous coupon

    expiry = issued + timedelta(days=valid_days)

    # Determine status based on member tier (tier-based redemption rates)
    member_tier = member_tiers.get(mid, "Bronze") if mid else "Bronze"
    redeem_rate = TIER_REDEMPTION_RATE[member_tier]

    if random.random() < redeem_rate:
        status = "redeemed"
    else:
        r = random.random()
        if r < NON_REDEEMED_SPLIT["issued"]:
            status = "issued"
        elif r < NON_REDEEMED_SPLIT["issued"] + NON_REDEEMED_SPLIT["expired"]:
            status = "expired"
        else:
            status = "voided"

    redeemed_date = None
    redeemed_txn = None
    if status == "redeemed":
        rd = rand_date(issued, min(expiry, DATE_END))
        redeemed_date = rd
        redeemed_txn = random.randint(1, NUM_TRANSACTIONS)

    code = f"AAP-{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000, 9999)}-{i:06d}"
    created = datetime(issued.year, issued.month, issued.day,
                       random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
    coupons_data.append((
        i, code, rule_id, mid, issued, expiry, status,
        redeemed_date, redeemed_txn, dtype, dval,
        random.choice(SOURCE_SYSTEMS), created
    ))
    if i % 50000 == 0:
        print(f"   ...{i:,} coupons generated")

coupons_schema = StructType([
    StructField("coupon_id", LongType(), False),
    StructField("coupon_code", StringType()), StructField("coupon_rule_id", LongType()),
    StructField("member_id", LongType()), StructField("issued_date", DateType()),
    StructField("expiry_date", DateType()), StructField("status", StringType()),
    StructField("redeemed_date", DateType()), StructField("redeemed_transaction_id", LongType()),
    StructField("discount_type", StringType()), StructField("discount_value", DoubleType()),
    StructField("source_system", StringType()), StructField("created_at", TimestampType()),
])
df_coupons = spark.createDataFrame(coupons_data, coupons_schema)
df_coupons.write.format("delta").mode("overwrite").saveAsTable("coupons")
print(f"✅ coupons: {df_coupons.count()} rows")

# Print redemption rate by tier for validation
tier_coupon_stats = {}  # tier -> (total, redeemed)
for c in coupons_data:
    mid = c[3]
    if mid:
        t = member_tiers.get(mid, "Bronze")
        if t not in tier_coupon_stats:
            tier_coupon_stats[t] = [0, 0]
        tier_coupon_stats[t][0] += 1
        if c[6] == "redeemed":
            tier_coupon_stats[t][1] += 1
for t in ["Bronze", "Silver", "Gold", "Platinum"]:
    if t in tier_coupon_stats:
        total, redeemed = tier_coupon_stats[t]
        print(f"   {t}: {redeemed:,}/{total:,} redeemed ({100*redeemed/total:.1f}%)")

# %% [markdown]
# ## 9. CSR — 500 Customer Service Rep profiles

# %%
NUM_CSRS = 500
DEPARTMENTS = ["Customer Service", "Loyalty Support", "Fraud Prevention", "Tier Management", "Escalations"]

csr_data = []
for i in range(1, NUM_CSRS + 1):
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    csr_data.append((
        i, f"{fn} {ln}", f"{fn.lower()}.{ln.lower()}@advanceautoparts.com",
        random.choice(DEPARTMENTS), random.random() < 0.90, ts_now()
    ))

csr_schema = StructType([
    StructField("csr_id", LongType(), False),
    StructField("csr_name", StringType()), StructField("csr_email", StringType()),
    StructField("department", StringType()), StructField("is_active", BooleanType()),
    StructField("created_at", TimestampType()),
])
df_csr = spark.createDataFrame(csr_data, csr_schema)
df_csr.write.format("delta").mode("overwrite").saveAsTable("csr")
print(f"✅ csr: {df_csr.count()} rows")

# %% [markdown]
# ## 10. CSR Activities — 50,000 audit trail records
#
# **Improvements:** More tier_override activities (especially Gold→Platinum upgrades).
# Seasonal spikes around campaign periods (more enrollment and coupon adjustments).

# %%
NUM_ACTIVITIES = 50000
# Weighted activity types: more enrollments and tier overrides than v1
CSR_ACTIVITY_TYPES = ["enrollment", "status_change", "coupon_adjust", "tier_override"]
CSR_ACTIVITY_WEIGHTS = [35, 20, 25, 20]  # v1 was uniform; now tier_override is significant

ACTIVITY_DETAILS = {
    "enrollment": [
        '{"action": "new_enrollment", "source": "POS", "store": "AAP Store #4123"}',
        '{"action": "new_enrollment", "source": "Ecomm", "platform": "web"}',
        '{"action": "new_enrollment", "source": "CustomerFirst", "channel": "phone"}',
    ],
    "status_change": [
        '{"from_status": "active", "to_status": "inactive", "reason": "member_request"}',
        '{"from_status": "suspended", "to_status": "active", "reason": "review_complete"}',
        '{"from_status": "inactive", "to_status": "active", "reason": "reactivation"}',
        '{"from_status": "active", "to_status": "suspended", "reason": "fraud_review"}',
    ],
    "coupon_adjust": [
        '{"coupon_id": "XXXXX", "action": "void", "reason": "system_error"}',
        '{"coupon_id": "XXXXX", "action": "extend", "new_expiry": "2026-06-01"}',
        '{"coupon_id": "XXXXX", "action": "reissue", "reason": "customer_complaint"}',
    ],
    "tier_override": [
        '{"from_tier": "Bronze", "to_tier": "Silver", "reason": "goodwill_upgrade"}',
        '{"from_tier": "Silver", "to_tier": "Gold", "reason": "promotion"}',
        '{"from_tier": "Gold", "to_tier": "Platinum", "reason": "executive_override"}',
        '{"from_tier": "Gold", "to_tier": "Platinum", "reason": "loyalty_milestone"}',
        '{"from_tier": "Silver", "to_tier": "Gold", "reason": "campaign_upgrade"}',
        '{"from_tier": "Bronze", "to_tier": "Silver", "reason": "retention_offer"}',
    ],
}

# Seasonal weighting for CSR activities — more activity during campaign periods
CSR_MONTH_WEIGHTS = {
    1: 1.2, 2: 0.8, 3: 1.3, 4: 1.2, 5: 0.9, 6: 1.1,
    7: 1.0, 8: 1.1, 9: 0.9, 10: 0.8, 11: 1.4, 12: 1.5,
}
MAX_CSR_MONTH_WEIGHT = max(CSR_MONTH_WEIGHTS.values())

def weighted_csr_date():
    d = rand_datetime()
    while random.random() > CSR_MONTH_WEIGHTS[d.month] / MAX_CSR_MONTH_WEIGHT:
        d = rand_datetime()
    return d

csr_ids = list(range(1, NUM_CSRS + 1))
activities_data = []
for i in range(1, NUM_ACTIVITIES + 1):
    aid = random.choice(csr_ids)
    mid = random.choice(all_member_ids)
    atype = random.choices(CSR_ACTIVITY_TYPES, weights=CSR_ACTIVITY_WEIGHTS, k=1)[0]
    details = random.choice(ACTIVITY_DETAILS[atype])
    adate = weighted_csr_date()
    created = adate
    activities_data.append((
        i, aid, mid, atype, adate.date(), details, created
    ))

aa_schema = StructType([
    StructField("activity_id", LongType(), False),
    StructField("csr_id", LongType()), StructField("member_id", LongType()),
    StructField("activity_type", StringType()), StructField("activity_date", DateType()),
    StructField("details", StringType()), StructField("created_at", TimestampType()),
])
df_aa = spark.createDataFrame(activities_data, aa_schema)
df_aa.write.format("delta").mode("overwrite").saveAsTable("csr_activities")
print(f"✅ csr_activities: {df_aa.count()} rows")

# %% [markdown]
# ## Summary — Row counts for all tables

# %%
print("\n" + "=" * 60)
print("📊 AAP LOYALTY SAMPLE DATA — GENERATION COMPLETE")
print("=" * 60)

tables = [
    "stores", "sku_reference", "loyalty_members", "transactions",
    "transaction_items", "member_points", "coupon_rules", "coupons",
    "csr", "csr_activities"
]
total = 0
for t in tables:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {t}").collect()[0]["cnt"]
    print(f"  {t:25s} → {count:>10,} rows")
    total += count

print(f"\n  {'TOTAL':25s} → {total:>10,} rows")
print("=" * 60)
print("\n✅ Next step: Run scripts/create-semantic-views.sql to create the semantic layer.")
