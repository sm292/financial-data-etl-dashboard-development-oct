"""Machine-learning enrichment for transaction review and exploratory segmentation."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


FEATURES = ["revenue", "expense", "gross_profit", "margin_pct", "units", "discount_pct"]


def enrich_with_ml(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    out = df.copy()
    if len(out) < 10:
        out["anomaly_score"] = 0.0
        out["is_anomaly"] = False
        out["segment"] = "Insufficient data"
        return out
    x = out[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(x)
    model = IsolationForest(n_estimators=200, contamination="auto", random_state=seed, n_jobs=-1)
    model.fit(scaled)
    # Higher values mean more unusual; score is normalized only for readable display.
    raw_score = -model.score_samples(scaled)
    lo, hi = np.quantile(raw_score, [.01, .99])
    out["anomaly_score"] = np.round(np.clip((raw_score - lo) / max(hi - lo, 1e-9), 0, 1), 4)
    out["is_anomaly"] = model.predict(scaled) == -1
    clusters = min(4, max(2, len(out) // 100))
    km = KMeans(n_clusters=clusters, n_init=10, random_state=seed)
    raw_labels = km.fit_predict(scaled)
    # Give segments stable descriptive ordering by mean revenue within this run.
    means = out.assign(_label=raw_labels).groupby("_label")["revenue"].mean().sort_values()
    names = ["Value", "Core", "Premium", "Strategic"][:clusters]
    mapping = {label: names[i] for i, label in enumerate(means.index)}
    out["segment"] = pd.Series(raw_labels, index=out.index).map(mapping)
    return out
