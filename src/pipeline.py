"""CSV/JSON -> validation/transforms -> SQLite and business-ready artifacts."""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from src.analytics import enrich_with_ml
from src.data_generator import write_source

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["transaction_id", "transaction_date", "customer_id", "category", "region", "channel",
            "units", "unit_price", "unit_cost", "discount_pct", "payment_method"]


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        return pd.read_json(path)
    return pd.read_csv(path)


def transform(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing_columns = sorted(set(REQUIRED) - set(raw.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    df = raw.copy()
    row_count = len(df)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    numeric = ["units", "unit_price", "unit_cost", "discount_pct"]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    invalid = df["transaction_date"].isna() | df[numeric].isna().any(axis=1)
    invalid |= (df["units"] <= 0) | (df["unit_price"] < 0) | (df["unit_cost"] < 0)
    invalid |= ~df["discount_pct"].between(0, 1)
    invalid |= df["transaction_id"].isna() | df["transaction_id"].duplicated(keep="first")
    dropped_invalid = int(invalid.sum())
    df = df.loc[~invalid].copy()
    df["revenue"] = (df["units"] * df["unit_price"] * (1 - df["discount_pct"])).round(2)
    df["expense"] = (df["units"] * df["unit_cost"]).round(2)
    df["gross_profit"] = (df["revenue"] - df["expense"]).round(2)
    df["margin_pct"] = np.where(df["revenue"] != 0, df["gross_profit"] / df["revenue"] * 100, 0).round(2)
    df["month"] = df["transaction_date"].dt.to_period("M").astype(str)
    df["year"] = df["transaction_date"].dt.year.astype(int)
    df = enrich_with_ml(df)
    quality = {
        "source_rows": row_count,
        "accepted_rows": int(len(df)),
        "rejected_rows": dropped_invalid,
        "duplicate_ids_in_source": int(raw["transaction_id"].duplicated().sum()),
        "nulls_after_cleaning": {k: int(v) for k, v in df[REQUIRED].isna().sum().items() if v},
        "revenue_total": round(float(df["revenue"].sum()), 2),
        "expense_total": round(float(df["expense"].sum()), 2),
        "gross_profit_total": round(float(df["gross_profit"].sum()), 2),
        "reconciliation_difference": round(float((df["revenue"] - df["expense"] - df["gross_profit"]).sum()), 2),
        "anomaly_count": int(df["is_anomaly"].sum()),
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    return df, quality


def run_pipeline(input_path: Path, db_path: Path, output_dir: Path) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raw = read_source(input_path)
    enriched, quality = transform(raw)
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(output_dir / "transactions_enriched.csv", index=False)
    (output_dir / "data_quality.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    monthly = enriched.groupby("month", as_index=False).agg(
        revenue=("revenue", "sum"), expense=("expense", "sum"), gross_profit=("gross_profit", "sum"),
        transactions=("transaction_id", "count"))
    monthly["margin_pct"] = (monthly["gross_profit"] / monthly["revenue"] * 100).round(2)
    monthly.to_csv(output_dir / "monthly_summary.csv", index=False)
    category = enriched.groupby("category", as_index=False).agg(
        revenue=("revenue", "sum"), expense=("expense", "sum"), gross_profit=("gross_profit", "sum"),
        transactions=("transaction_id", "count"))
    category.to_csv(output_dir / "category_summary.csv", index=False)
    kpis = {k: quality[k] for k in ["accepted_rows", "revenue_total", "expense_total", "gross_profit_total", "anomaly_count"]}
    (output_dir / "kpi_summary.json").write_text(json.dumps(kpis, indent=2), encoding="utf-8")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        raw.to_sql("raw_transactions", conn, if_exists="replace", index=False)
        enriched.to_sql("transactions", conn, if_exists="replace", index=False)
        monthly.to_sql("monthly_summary", conn, if_exists="replace", index=False)
        category.to_sql("category_summary", conn, if_exists="replace", index=False)
    logging.info("Loaded %s accepted rows from %s", len(enriched), input_path)
    return quality


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Existing .csv or .json source")
    parser.add_argument("--generate", action="store_true", help="Generate a seeded demo source file")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--rows", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    source = args.input
    if args.generate or source is None:
        source = ROOT / "data" / "raw" / f"transactions.{args.format}"
        write_source(source, args.rows, args.seed)
        logging.info("Generated %s", source)
    report = run_pipeline(source, ROOT / "data" / "finance_demo.db", ROOT / "data" / "processed")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
