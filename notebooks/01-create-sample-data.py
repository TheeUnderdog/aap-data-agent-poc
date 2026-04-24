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
# | loyalty_members | 5,000 | Member profiles and tier info |
# | transactions | 50,000 | 3 years of purchase/return transactions |
# | transaction_items | 150,000 | Line items per transaction |
# | member_points | 100,000 | Points activity ledger |
# | coupons | 20,000 | Coupon issuance and redemption |
# | coupon_rules | 50 | Coupon rule definitions |
# | agents | 200 | CSR agent profiles |
# | agent_activities | 10,000 | Agent audit trail |
# | sku_reference | 2,000 | Product/SKU catalog |
# | stores | 500 | Store reference data |
#
# **Data spans:** 2023-01-01 to 2026-04-01
# **Deterministic:** Uses fixed random seed for reproducibility.

# %%
import random
import hashlib
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
# ## 2. SKU Reference — Auto parts product catalog

# %%
NUM_SKUS = 2000

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
sku_lookup = [(r["sku"], r["product_name"], r["category"], r["unit_price"]) for r in sku_data]

# %% [markdown]
# ## 3. Loyalty Members — 5,000 member profiles with realistic tier distribution

# %%
NUM_MEMBERS = 5000

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

members_data = []
for i in range(1, NUM_MEMBERS + 1):
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    email = f"{fn.lower()}.{ln.lower()}{random.randint(1, 999)}@{'gmail.com' if random.random() < 0.5 else 'yahoo.com' if random.random() < 0.5 else 'outlook.com'}"
    phone = f"{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
    enroll = rand_date(date(2020, 1, 1), date(2026, 3, 1))
    status_r = random.random()
    status = "active" if status_r < 0.88 else ("inactive" if status_r < 0.97 else "suspended")
    tier = pick_tier()
    diy_id = f"DIY-{random.randint(100000, 999999)}" if random.random() < 0.35 else None
    created = datetime(enroll.year, enroll.month, enroll.day, random.randint(8, 20), random.randint(0, 59), 0)
    updated = rand_datetime(enroll, DATE_END)
    members_data.append((
        i, fn, ln, email, phone, enroll,
        random.choice(ENROLLMENT_SOURCES), status, tier,
        random.random() < 0.72, random.random() < 0.45,
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

# %% [markdown]
# ## 4. Transactions — 50,000 transactions with seasonal patterns
# 
# Spring/summer months get more transactions (seasonal auto maintenance).

# %%
NUM_TRANSACTIONS = 50000

# Seasonal weight: spring/summer heavier
MONTH_WEIGHTS = {1: 0.7, 2: 0.7, 3: 0.9, 4: 1.2, 5: 1.3, 6: 1.3,
                 7: 1.2, 8: 1.1, 9: 1.0, 10: 0.9, 11: 0.8, 12: 0.8}
CHANNELS = ["in-store", "online", "mobile"]
CHANNEL_WEIGHTS = [0.70, 0.20, 0.10]

member_ids = list(range(1, NUM_MEMBERS + 1))
store_ids = list(range(1, NUM_STORES + 1))

# Pre-generate weighted dates for seasonal patterns
def weighted_random_date():
    d = rand_date()
    # Accept/reject based on month weight
    while random.random() > MONTH_WEIGHTS.get(d.month, 1.0) / 1.3:
        d = rand_date()
    return d

transactions_data = []
for i in range(1, NUM_TRANSACTIONS + 1):
    mid = random.choice(member_ids)
    sid = random.choice(store_ids)
    tdate = weighted_random_date()
    ttype = "purchase" if random.random() < 0.92 else "return"
    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
    item_count = random.choices([1, 2, 3, 4, 5, 6], weights=[25, 30, 20, 12, 8, 5], k=1)[0]
    subtotal = round(random.uniform(5.0, 500.0), 2)
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
# ## 5. Transaction Items — ~150,000 line items (3 per transaction avg)

# %%
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
# ## 6. Member Points — ~100,000 points activity records
#
# Points rules: 1 pt/dollar for Bronze/Silver, 1.5x for Gold, 2x for Platinum.
# Activity types: earn, redeem, expire, adjust, bonus.

# %%
NUM_POINTS = 100000

TIER_MULTIPLIER = {"Bronze": 1.0, "Silver": 1.0, "Gold": 1.5, "Platinum": 2.0}
POINT_SOURCES = ["purchase", "campaign", "bonus_activity", "manual_adjust"]
ACTIVITY_TYPES = ["earn", "redeem", "expire", "adjust", "bonus"]
ACTIVITY_WEIGHTS = [55, 20, 10, 5, 10]

# Build tier lookup
member_tiers = {m[0]: m[8] for m in members_data}

points_data = []
member_balances = {}
for i in range(1, NUM_POINTS + 1):
    mid = random.choice(member_ids)
    tier = member_tiers.get(mid, "Bronze")
    mult = TIER_MULTIPLIER[tier]
    atype = random.choices(ACTIVITY_TYPES, weights=ACTIVITY_WEIGHTS, k=1)[0]
    adate = rand_date()

    if atype == "earn":
        pts = int(random.uniform(5, 250) * mult)
        source = "purchase"
        ref_id = str(random.randint(1, NUM_TRANSACTIONS))
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
        pts = random.randint(25, 500)
        source = "bonus_activity"
        ref_id = f"CAMP-{random.randint(100, 999)}"
        desc = random.choice([
            "Bonus: Oil change month promo", "Bonus: Battery recycling reward",
            "Bonus: Double points weekend", "Bonus: Birthday points",
            "Bonus: Referral reward", "Bonus: Tier upgrade bonus",
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

# %% [markdown]
# ## 7. Coupon Rules — 50 rule definitions

# %%
NUM_RULES = 50
DISCOUNT_TYPES = ["percentage", "fixed", "bogo"]
RULE_TEMPLATES = [
    ("Welcome Discount", "New member welcome offer"),
    ("Oil Change Special", "Discount on oil change products"),
    ("Battery Promo", "Battery purchase promotion"),
    ("Brake Service Deal", "Brake pads and rotors discount"),
    ("Seasonal Sale", "Seasonal clearance discount"),
    ("Birthday Reward", "Member birthday special"),
    ("Tier Upgrade Bonus", "Bonus for reaching new tier"),
    ("Referral Reward", "New member referral discount"),
    ("Weekend Flash Sale", "Limited time weekend offer"),
    ("Holiday Special", "Holiday season promotion"),
    ("Double Points Coupon", "Earn double points on purchase"),
    ("Filter Bundle", "Buy 2 filters get discount"),
    ("Wiper Blade Deal", "Wiper blade replacement offer"),
    ("Loyalty Anniversary", "Anniversary membership reward"),
    ("Premium Member Exclusive", "Gold/Platinum exclusive offer"),
]

rules_data = []
for i in range(1, NUM_RULES + 1):
    tmpl = RULE_TEMPLATES[i % len(RULE_TEMPLATES)]
    dtype = random.choice(DISCOUNT_TYPES)
    dval = round(random.uniform(5, 50), 2) if dtype == "percentage" else round(random.uniform(3, 75), 2)
    if dtype == "bogo":
        dval = 0.0
    min_purchase = round(random.choice([0, 10, 15, 20, 25, 30, 50]), 2)
    valid_days = random.choice([7, 14, 30, 60, 90])
    target_tier = random.choice([None, None, None, "Gold", "Platinum", "Silver"])
    rules_data.append((
        i, f"{tmpl[0]} #{i}", tmpl[1], dtype, dval, min_purchase,
        valid_days, random.random() < 0.80, target_tier, ts_now()
    ))

rules_schema = StructType([
    StructField("rule_id", LongType(), False),
    StructField("rule_name", StringType()), StructField("description", StringType()),
    StructField("discount_type", StringType()), StructField("discount_value", DoubleType()),
    StructField("min_purchase", DoubleType()), StructField("valid_days", IntegerType()),
    StructField("is_active", BooleanType()), StructField("target_tier", StringType()),
    StructField("created_at", TimestampType()),
])
df_rules = spark.createDataFrame(rules_data, rules_schema)
df_rules.write.format("delta").mode("overwrite").saveAsTable("coupon_rules")
print(f"✅ coupon_rules: {df_rules.count()} rows")

# %% [markdown]
# ## 8. Coupons — 20,000 issued coupons with redemption tracking

# %%
NUM_COUPONS = 20000
COUPON_STATUSES = ["issued", "redeemed", "expired", "voided"]
COUPON_STATUS_WEIGHTS = [30, 35, 30, 5]
SOURCE_SYSTEMS = ["GK", "POS", "Ecomm"]

coupons_data = []
for i in range(1, NUM_COUPONS + 1):
    rule = random.choice(rules_data)
    rule_id = rule[0]
    dtype = rule[3]
    dval = rule[4]
    mid = random.choice(member_ids) if random.random() < 0.85 else None
    issued = rand_date()
    expiry = issued + timedelta(days=rule[6])
    status = random.choices(COUPON_STATUSES, weights=COUPON_STATUS_WEIGHTS, k=1)[0]
    redeemed_date = None
    redeemed_txn = None
    if status == "redeemed":
        rd = rand_date(issued, min(expiry, DATE_END))
        redeemed_date = rd
        redeemed_txn = random.randint(1, NUM_TRANSACTIONS)
    code = f"AAP-{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(1000, 9999)}-{i:05d}"
    created = datetime(issued.year, issued.month, issued.day,
                       random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
    coupons_data.append((
        i, code, rule_id, mid, issued, expiry, status,
        redeemed_date, redeemed_txn, dtype, dval,
        random.choice(SOURCE_SYSTEMS), created
    ))

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

# %% [markdown]
# ## 9. Agents — 200 CSR agent profiles

# %%
NUM_AGENTS = 200
DEPARTMENTS = ["Customer Service", "Loyalty Support", "Fraud Prevention", "Tier Management", "Escalations"]

agents_data = []
for i in range(1, NUM_AGENTS + 1):
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    agents_data.append((
        i, f"{fn} {ln}", f"{fn.lower()}.{ln.lower()}@advanceautoparts.com",
        random.choice(DEPARTMENTS), random.random() < 0.90, ts_now()
    ))

agents_schema = StructType([
    StructField("agent_id", LongType(), False),
    StructField("agent_name", StringType()), StructField("agent_email", StringType()),
    StructField("department", StringType()), StructField("is_active", BooleanType()),
    StructField("created_at", TimestampType()),
])
df_agents = spark.createDataFrame(agents_data, agents_schema)
df_agents.write.format("delta").mode("overwrite").saveAsTable("agents")
print(f"✅ agents: {df_agents.count()} rows")

# %% [markdown]
# ## 10. Agent Activities — 10,000 audit trail records

# %%
NUM_ACTIVITIES = 10000
AGENT_ACTIVITY_TYPES = ["enrollment", "status_change", "coupon_adjust", "tier_override"]
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
    ],
}

agent_ids = list(range(1, NUM_AGENTS + 1))
activities_data = []
for i in range(1, NUM_ACTIVITIES + 1):
    aid = random.choice(agent_ids)
    mid = random.choice(member_ids)
    atype = random.choice(AGENT_ACTIVITY_TYPES)
    details = random.choice(ACTIVITY_DETAILS[atype])
    adate = rand_datetime()
    created = adate
    activities_data.append((
        i, aid, mid, atype, adate.date(), details, created
    ))

aa_schema = StructType([
    StructField("activity_id", LongType(), False),
    StructField("agent_id", LongType()), StructField("member_id", LongType()),
    StructField("activity_type", StringType()), StructField("activity_date", DateType()),
    StructField("details", StringType()), StructField("created_at", TimestampType()),
])
df_aa = spark.createDataFrame(activities_data, aa_schema)
df_aa.write.format("delta").mode("overwrite").saveAsTable("agent_activities")
print(f"✅ agent_activities: {df_aa.count()} rows")

# %% [markdown]
# ## Summary — Row counts for all tables

# %%
print("\n" + "=" * 60)
print("📊 AAP LOYALTY SAMPLE DATA — GENERATION COMPLETE")
print("=" * 60)

tables = [
    "stores", "sku_reference", "loyalty_members", "transactions",
    "transaction_items", "member_points", "coupon_rules", "coupons",
    "agents", "agent_activities"
]
total = 0
for t in tables:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {t}").collect()[0]["cnt"]
    print(f"  {t:25s} → {count:>10,} rows")
    total += count

print(f"\n  {'TOTAL':25s} → {total:>10,} rows")
print("=" * 60)
print("\n✅ Next step: Run scripts/create-semantic-views.sql to create the semantic layer.")
