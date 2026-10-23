"""Create a deterministic, business-shaped financial transaction dataset."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def generate_transactions(rows: int = 6000, seed: int = 42) -> pd.DataFrame:
    if rows < 1:
        raise ValueError("rows must be at least 1")
    rng = np.random.default_rng(seed)
    categories = np.array(["Electronics", "Home", "Apparel", "Beauty", "Grocery", "Sports"])
    category = rng.choice(categories, rows, p=[.20, .17, .18, .13, .19, .13])
    price_ranges = {"Electronics": (90, 1200), "Home": (18, 480), "Apparel": (12, 240),
                    "Beauty": (8, 130), "Grocery": (3, 95), "Sports": (15, 360)}
    low = np.array([price_ranges[c][0] for c in category])
    high = np.array([price_ranges[c][1] for c in category])
    unit_price = np.round(rng.uniform(low, high), 2)
    margin_rate = np.clip(rng.normal(.39, .12, rows), .08, .72)
    unit_cost = np.round(unit_price * (1 - margin_rate), 2)
    units = rng.choice([1, 2, 3, 4, 5, 8, 10], rows, p=[.30, .24, .19, .12, .08, .05, .02])
    discount = np.round(rng.choice([0, .05, .10, .15, .20, .25], rows,
                                   p=[.35, .20, .22, .13, .08, .02]), 2)
    # Add a small number of genuine-looking high-cost outliers for the review queue.
    anomaly_idx = rng.choice(rows, max(1, rows // 100), replace=False)
    unit_cost[anomaly_idx] = np.round(unit_cost[anomaly_idx] * rng.uniform(1.35, 1.8, len(anomaly_idx)), 2)
    dates = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 1000, rows), unit="D")
    regions = rng.choice(["North", "South", "East", "West", "Central"], rows,
                         p=[.24, .23, .18, .20, .15])
    channels = rng.choice(["Online", "Retail", "Wholesale"], rows, p=[.48, .38, .14])
    return pd.DataFrame({
        "transaction_id": [f"TX-{i:07d}" for i in range(1, rows + 1)],
        "transaction_date": dates.strftime("%Y-%m-%d"),
        "customer_id": [f"C-{i:05d}" for i in rng.integers(1, max(100, rows // 3), rows)],
        "category": category,
        "region": regions,
        "channel": channels,
        "units": units,
        "unit_price": unit_price,
        "unit_cost": unit_cost,
        "discount_pct": discount,
        "payment_method": rng.choice(["Card", "Bank transfer", "Wallet", "Cash"], rows,
                                     p=[.53, .19, .20, .08]),
    })


def write_source(path: Path, rows: int = 6000, seed: int = 42) -> pd.DataFrame:
    df = generate_transactions(rows, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(df.to_json(orient="records", indent=2), encoding="utf-8")
    else:
        df.to_csv(path, index=False)
    return df
