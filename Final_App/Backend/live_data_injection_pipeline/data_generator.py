"""
data_generator.py
Generates realistic supply-chain order records with controlled randomness.
Each call to generate_order() produces a new order dict ready for ML inference.
"""

import random
import math
from datetime import datetime

# ─── Lookup tables ──────────────────────────────────────────────────────────

CUSTOMER_SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SHIPPING_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
MARKETS = ["LATAM", "Europe", "USCA", "Asia Pacific", "Africa"]
DEPARTMENTS = ["Technology", "Furniture", "Office Supplies"]
CLASSES = ["Regular Air", "Delivery Truck", "Express Air"]

# Realistic value ranges per segment
_SEGMENT_PROFILES = {
    "Consumer": {
        "sales_range": (15, 800),
        "quantity_range": (1, 8),
        "profit_margin_range": (0.02, 0.45),
        "high_value_prob": 0.08,
        "bulk_prob": 0.03,
    },
    "Corporate": {
        "sales_range": (80, 4500),
        "quantity_range": (2, 30),
        "profit_margin_range": (0.05, 0.35),
        "high_value_prob": 0.30,
        "bulk_prob": 0.25,
    },
    "Home Office": {
        "sales_range": (20, 1200),
        "quantity_range": (1, 12),
        "profit_margin_range": (0.03, 0.40),
        "high_value_prob": 0.12,
        "bulk_prob": 0.06,
    },
}

_LEAD_TIME_BY_MODE = {
    "Standard Class": (5, 18),
    "Second Class": (3, 12),
    "First Class": (2, 7),
    "Same Day": (0, 2),
}

_SHIPPING_COST_BY_MODE = {
    "Standard Class": (2.0, 12.0),
    "Second Class": (5.0, 20.0),
    "First Class": (10.0, 35.0),
    "Same Day": (20.0, 60.0),
}

# Demand history pools (realistic monthly demand values)
_DEMAND_POOLS = [
    (3200, 3400, 3600),
    (3800, 3750, 3900),
    (4100, 4300, 4000),
    (4675, 4146, 4823),
    (5100, 4800, 5200),
    (3500, 3900, 4200),
    (4400, 4600, 4500),
    (5500, 5200, 4900),
    (3000, 3100, 3300),
    (4900, 5100, 5300),
]


def _jitter(value: float, pct: float = 0.15) -> float:
    """Add random noise within ±pct of value."""
    return value * random.uniform(1 - pct, 1 + pct)


def generate_order() -> dict:
    """
    Generate a single realistic supply-chain order record
    with all 25 features required by the ML models.
    """
    now = datetime.now()

    segment = random.choice(CUSTOMER_SEGMENTS)
    profile = _SEGMENT_PROFILES[segment]

    shipping_mode = random.choice(SHIPPING_MODES)
    market = random.choice(MARKETS)
    department = random.choice(DEPARTMENTS)
    item_class = random.choice(CLASSES)

    sales = round(random.uniform(*profile["sales_range"]), 2)
    quantity = random.randint(*profile["quantity_range"])
    profit_margin = round(random.uniform(*profile["profit_margin_range"]), 4)
    profit = round(sales * profit_margin, 2)

    lt_lo, lt_hi = _LEAD_TIME_BY_MODE[shipping_mode]
    lead_time = random.randint(lt_lo, lt_hi)

    sc_lo, sc_hi = _SHIPPING_COST_BY_MODE[shipping_mode]
    avg_shipping_cost = round(random.uniform(sc_lo, sc_hi), 2)

    is_high_value = 1 if random.random() < profile["high_value_prob"] else 0
    is_bulk_order = 1 if random.random() < profile["bulk_prob"] else 0

    order_processing_days = random.randint(1, 6)
    num_orders_30d = random.randint(1, 15)
    avg_order_value_30d = round(_jitter(sales, 0.3), 2)

    # Defect rates — occasionally spike for anomaly-triggering orders
    if random.random() < 0.10:
        # ~10% of orders have elevated defect rates (anomaly candidates)
        avg_defect_rate = round(random.uniform(5.0, 18.0), 2)
        max_defect_rate = round(avg_defect_rate * random.uniform(1.2, 2.5), 2)
    else:
        avg_defect_rate = round(random.uniform(0.3, 4.0), 2)
        max_defect_rate = round(avg_defect_rate * random.uniform(1.1, 2.0), 2)

    return {
        "product_id": random.randint(1, 1500),
        "customer_id": random.randint(1, 800),
        "customer_segment": segment,
        "sales": sales,
        "quantity": quantity,
        "shipping_mode": shipping_mode,
        "market": market,
        "lead_time": lead_time,
        "avg_order_value_30d": avg_order_value_30d,
        "num_orders_30d": num_orders_30d,
        "is_high_value": is_high_value,
        "is_bulk_order": is_bulk_order,
        "day_of_week": now.weekday(),
        "month": now.month,
        "quarter": (now.month - 1) // 3 + 1,
        "year": now.year,
        "department": department,
        "class": item_class,
        "profit": profit,
        "order_processing_days": order_processing_days,
        "avg_lead_time_by_mode": round(_jitter(lead_time, 0.2), 1),
        "avg_shipping_cost": avg_shipping_cost,
        "avg_defect_rate": avg_defect_rate,
        "max_defect_rate": max_defect_rate,
        "profit_margin": profit_margin,
    }


def generate_demand_input() -> dict:
    """
    Generate realistic demand lag inputs for the demand forecasting model.
    Picks from curated pools and adds jitter for variation.
    """
    base = random.choice(_DEMAND_POOLS)
    now = datetime.now()

    return {
        "lag_1": round(_jitter(base[0], 0.08)),
        "lag_2": round(_jitter(base[1], 0.08)),
        "lag_3": round(_jitter(base[2], 0.08)),
        "month": now.month,
    }
