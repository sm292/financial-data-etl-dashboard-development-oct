# Financial Data ETL & Business Dashboard

A reproducible portfolio project for ingesting financial transactions, checking and transforming them, storing them in SQLite, applying unsupervised machine learning, and exploring business performance in Streamlit.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m src.pipeline --generate --format csv --rows 6000
streamlit run app.py
```

The pipeline creates `data/raw/transactions.csv`, loads a local SQLite database at `data/finance_demo.db`, validates and transforms records, and writes `data/processed/transactions_enriched.csv`, `data/processed/kpi_summary.json`, and `data/processed/data_quality.json`. Use `--format json` to generate JSON instead. To rerun ETL from an existing CSV/JSON input, run `python -m src.pipeline --input data/raw/transactions.csv`.

## Dashboard

- Revenue, expenses, gross profit, and margin KPIs with period-over-period context.
- Monthly, category, region, channel, and customer segment views with interactive filters.
- Revenue-versus-expense reconciliation and transaction-level drill-down.
- Isolation Forest expense anomaly scores and K-Means transaction segments.
- Download filtered transactions and the quality/reconciliation report.

## Data model and method

Each transaction has a stable ID, date, customer, product category, region, sales channel, units, unit price, unit cost, discount, and payment method. Net revenue is units × unit price × (1 − discount); expense is units × unit cost; gross profit is revenue − expense. A seeded synthetic dataset avoids external data-source dependencies and makes results reproducible. The SQLite database includes raw and enriched transaction tables plus monthly/category aggregates.

Isolation Forest flags unusual expense transactions; it is an exploratory review queue, not a fraud verdict. K-Means segments transactions using scaled revenue, expense, margin, units, and discount features. Segment labels are data-dependent and should be interpreted using their displayed profiles. This synthetic dataset is for demonstration and must not be presented as actual company performance.

## Project layout

```text
app.py
src/
  data_generator.py
  pipeline.py
  analytics.py
data/
  raw/                 # reproducible source CSV/JSON
  processed/           # ETL outputs
  finance_demo.db      # SQLite database
```
