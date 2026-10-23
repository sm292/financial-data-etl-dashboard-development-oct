"""Interactive executive dashboard for the financial transaction demo."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "finance_demo.db"
QUALITY_PATH = ROOT / "data" / "processed" / "data_quality.json"

st.set_page_config(page_title="Finance Performance | Executive Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
  .stApp { background: #f4f7fb; color: #172b4d; }
  h1,h2,h3 { font-family: Manrope, sans-serif; letter-spacing: -.03em; }
  [data-testid="stMetric"] { background: white; border: 1px solid #e6ebf2; padding: 16px 18px; border-radius: 12px; box-shadow: 0 2px 8px #122b4908; }
  [data-testid="stSidebar"] { background: #10233f; }
  [data-testid="stSidebar"] * { color: #edf3fb !important; }
  .eyebrow { color: #53708f; font-size: .78rem; text-transform: uppercase; letter-spacing: .12em; font-weight: 700; }
  .subtle { color: #64748b; margin-top: -.5rem; }
  div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(db_mtime: float) -> pd.DataFrame:
    del db_mtime
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM transactions", conn, parse_dates=["transaction_date"])
    return df


def money(value: float) -> str:
    return f"${value:,.0f}"


st.sidebar.markdown("## FINANCE / INSIGHTS")
st.sidebar.caption("Executive performance workspace")
if not DB_PATH.exists():
    st.title("Financial performance dashboard")
    st.info("Prepare the demo dataset to get started: run `python -m src.pipeline --generate --format csv --rows 6000`, then refresh this page.")
    st.stop()

df = load_data(DB_PATH.stat().st_mtime)
if df.empty:
    st.warning("The database contains no valid transactions. Run the ETL pipeline with a valid CSV or JSON source.")
    st.stop()

date_min = df["transaction_date"].min().date()
date_max = df["transaction_date"].max().date()
st.sidebar.markdown("### Filters")
date_range = st.sidebar.date_input("Transaction dates", value=(date_min, date_max), min_value=date_min, max_value=date_max)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range
filter_fields = ["region", "category", "channel", "segment"]
filters: dict[str, list[str]] = {}
for field in filter_fields:
    values = sorted(df[field].dropna().astype(str).unique())
    filters[field] = st.sidebar.multiselect(field.title(), values, default=values)

mask = df["transaction_date"].dt.date.between(start_date, end_date)
for field, selected in filters.items():
    mask &= df[field].astype(str).isin(selected)
view = df.loc[mask].copy()
st.sidebar.markdown("---")
st.sidebar.caption(f"{len(view):,} of {len(df):,} transactions shown")
st.sidebar.caption("Demo data · generated for illustration")

st.markdown('<div class="eyebrow">Executive overview</div>', unsafe_allow_html=True)
st.title("Financial performance")
st.markdown('<p class="subtle">Revenue, cost, and margin trends across your selected period.</p>', unsafe_allow_html=True)
if view.empty:
    st.warning("No transactions match these filters. Adjust the date range or selections.")
    st.stop()

revenue = view["revenue"].sum()
expense = view["expense"].sum()
profit = view["gross_profit"].sum()
margin = profit / revenue * 100 if revenue else 0
prior_start = (pd.Timestamp(start_date) - pd.Timedelta(days=(end_date-start_date).days + 1)).date()
prior_end = (pd.Timestamp(start_date) - pd.Timedelta(days=1)).date()
prior_mask = df["transaction_date"].dt.date.between(prior_start, prior_end)
for field, selected in filters.items():
    prior_mask &= df[field].astype(str).isin(selected)
prior = df.loc[prior_mask]
prior_revenue = prior["revenue"].sum()
revenue_delta = (revenue / prior_revenue - 1) * 100 if prior_revenue else None
anomalies = int(view["is_anomaly"].sum())

cols = st.columns(5)
cols[0].metric("Net revenue", money(revenue), f"{revenue_delta:+.1f}% vs prior period" if revenue_delta is not None else "Selected period")
cols[1].metric("Operating expense", money(expense), f"{expense/revenue*100:.1f}% of revenue" if revenue else None)
cols[2].metric("Gross profit", money(profit), "Revenue less transaction cost")
cols[3].metric("Gross margin", f"{margin:.1f}%", "Profit / revenue")
cols[4].metric("Review flags", f"{anomalies:,}", f"{anomalies/len(view)*100:.1f}% of transactions")

st.markdown("### Performance over time")
monthly = view.assign(month=view["transaction_date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False).agg(
    Revenue=("revenue", "sum"), Expenses=("expense", "sum"), Profit=("gross_profit", "sum"))
left, right = st.columns([1.55, 1])
with left:
    trend = go.Figure()
    for label, color in [("Revenue", "#2563eb"), ("Expenses", "#f59e0b"), ("Profit", "#0f9d76")]:
        trend.add_trace(go.Scatter(x=monthly["month"], y=monthly[label], name=label, mode="lines+markers",
                                   line={"color": color, "width": 3}, marker={"size": 5}))
    trend.update_layout(height=350, margin={"l": 10, "r": 10, "t": 15, "b": 10},
                        legend={"orientation": "h", "y": 1.12}, hovermode="x unified",
                        paper_bgcolor="white", plot_bgcolor="white", yaxis_title="Amount ($)")
    st.plotly_chart(trend, use_container_width=True)
with right:
    by_category = view.groupby("category", as_index=False).agg(Revenue=("revenue", "sum"), Profit=("gross_profit", "sum"))
    cat_fig = px.bar(by_category.sort_values("Revenue"), x="Revenue", y="category", orientation="h",
                     color="Profit", color_continuous_scale=["#f59e0b", "#12a77d"],
                     labels={"category": "Category", "Revenue": "Net revenue ($)"})
    cat_fig.update_layout(height=350, margin={"l": 10, "r": 10, "t": 15, "b": 10},
                          paper_bgcolor="white", plot_bgcolor="white", coloraxis_showscale=False)
    st.plotly_chart(cat_fig, use_container_width=True)

st.markdown("### Business mix")
mix1, mix2, mix3 = st.columns(3)
with mix1:
    region = view.groupby("region", as_index=False)[["revenue", "gross_profit"]].sum()
    st.plotly_chart(px.bar(region, x="region", y="revenue", color="gross_profit", color_continuous_scale="Blues",
                           labels={"revenue": "Revenue ($)", "region": "Region", "gross_profit": "Profit ($)"}, title="Revenue by region").update_layout(height=300, margin={"l": 4, "r": 4, "t": 45, "b": 5}, paper_bgcolor="white", plot_bgcolor="white"), use_container_width=True)
with mix2:
    seg = view.groupby("segment", as_index=False).agg(Transactions=("transaction_id", "count"), Revenue=("revenue", "sum"))
    st.plotly_chart(px.pie(seg, names="segment", values="Transactions", hole=.62, title="Transaction segments",
                           color_discrete_sequence=["#2563eb", "#12a77d", "#f59e0b", "#7c5ce7"]).update_layout(height=300, margin={"l": 4, "r": 4, "t": 45, "b": 5}, paper_bgcolor="white", legend={"orientation": "h", "y": -.08}), use_container_width=True)
with mix3:
    channel = view.groupby("channel", as_index=False).agg(Revenue=("revenue", "sum"), Profit=("gross_profit", "sum"))
    st.plotly_chart(px.bar(channel, x="channel", y=["Revenue", "Profit"], barmode="group", title="Channel performance",
                           color_discrete_sequence=["#2563eb", "#0f9d76"]).update_layout(height=300, margin={"l": 4, "r": 4, "t": 45, "b": 5}, paper_bgcolor="white", plot_bgcolor="white", legend={"orientation": "h", "y": 1.15}), use_container_width=True)

st.markdown("### Transaction review")
tab1, tab2, tab3 = st.tabs(["Anomaly review", "Segment profiles", "Transactions"])
with tab1:
    flagged = view.loc[view["is_anomaly"]].sort_values("anomaly_score", ascending=False)
    st.caption("Isolation Forest surfaces unusual cost and profitability patterns for human review. A flag is not a fraud conclusion.")
    if flagged.empty:
        st.success("No transactions were flagged in this filtered view.")
    else:
        st.dataframe(flagged[["transaction_id", "transaction_date", "category", "region", "channel", "units", "revenue", "expense", "gross_profit", "margin_pct", "anomaly_score"]],
                     use_container_width=True, hide_index=True, column_config={
                         "transaction_date": st.column_config.DateColumn("Date"),
                         "revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
                         "expense": st.column_config.NumberColumn("Expense", format="$%.2f"),
                         "gross_profit": st.column_config.NumberColumn("Gross profit", format="$%.2f"),
                         "anomaly_score": st.column_config.ProgressColumn("Anomaly score", min_value=0, max_value=1, format="%.2f")})
with tab2:
    profiles = view.groupby("segment", as_index=False).agg(
        Transactions=("transaction_id", "count"), Customers=("customer_id", "nunique"),
        Avg_revenue=("revenue", "mean"), Avg_profit=("gross_profit", "mean"),
        Avg_margin=("margin_pct", "mean"), Avg_discount=("discount_pct", "mean"),
        Anomaly_rate=("is_anomaly", "mean"))
    profiles["Anomaly_rate"] *= 100
    st.dataframe(profiles, use_container_width=True, hide_index=True, column_config={
        "Avg_revenue": st.column_config.NumberColumn("Avg revenue", format="$%.2f"),
        "Avg_profit": st.column_config.NumberColumn("Avg profit", format="$%.2f"),
        "Avg_margin": st.column_config.NumberColumn("Avg margin", format="%.1f%%"),
        "Avg_discount": st.column_config.NumberColumn("Avg discount", format="%.1f%%"),
        "Anomaly_rate": st.column_config.NumberColumn("Anomaly rate", format="%.1f%%")})
    st.caption("K-Means segments transactions on scaled value, margin, units, and discount features. Names are relative to the current dataset.")
with tab3:
    shown = view.sort_values("transaction_date", ascending=False)
    st.dataframe(shown[["transaction_id", "transaction_date", "customer_id", "category", "region", "channel", "units", "revenue", "expense", "gross_profit", "margin_pct", "segment", "is_anomaly"]],
                 use_container_width=True, hide_index=True, height=420,
                 column_config={"transaction_date": st.column_config.DateColumn("Date"),
                                "revenue": st.column_config.NumberColumn("Revenue", format="$%.2f"),
                                "expense": st.column_config.NumberColumn("Expense", format="$%.2f"),
                                "gross_profit": st.column_config.NumberColumn("Gross profit", format="$%.2f"),
                                "margin_pct": st.column_config.NumberColumn("Margin", format="%.1f%%"),
                                "is_anomaly": st.column_config.CheckboxColumn("Review flag")})

st.markdown("### Data quality & reconciliation")
q1, q2 = st.columns([1, 2])
try:
    quality = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    quality = {"accepted_rows": len(df), "rejected_rows": None, "reconciliation_difference": None}
with q1:
    st.metric("Accepted rows", f"{quality.get('accepted_rows', len(df)):,}")
    st.metric("Rejected source rows", f"{quality.get('rejected_rows', 0):,}" if quality.get("rejected_rows") is not None else "—")
    st.metric("Reconciliation difference", money(quality.get("reconciliation_difference", 0) or 0))
with q2:
    st.caption("Revenue − expense − gross profit should equal $0. The quality report covers the full ETL run; dashboard figures reflect active filters.")
    with st.expander("View ETL quality report"):
        st.json(quality)
csv = view.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered transaction detail (CSV)", csv, "financial_transactions_filtered.csv", "text/csv")
st.caption("Financial Data ETL & Dashboard · synthetic demonstration data · amounts in USD")
