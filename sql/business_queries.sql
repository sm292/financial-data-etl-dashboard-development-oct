-- Reusable SQLite queries for analysts and dashboard integrations.

-- Monthly executive scorecard
SELECT month,
       ROUND(SUM(revenue), 2) AS revenue,
       ROUND(SUM(expense), 2) AS expense,
       ROUND(SUM(gross_profit), 2) AS gross_profit,
       ROUND(100.0 * SUM(gross_profit) / NULLIF(SUM(revenue), 0), 2) AS gross_margin_pct,
       COUNT(*) AS transactions
FROM transactions
GROUP BY month
ORDER BY month;

-- Profitability by category and region
SELECT category, region,
       ROUND(SUM(revenue), 2) AS revenue,
       ROUND(SUM(expense), 2) AS expense,
       ROUND(SUM(gross_profit), 2) AS gross_profit,
       ROUND(100.0 * SUM(gross_profit) / NULLIF(SUM(revenue), 0), 2) AS gross_margin_pct
FROM transactions
GROUP BY category, region
ORDER BY gross_profit DESC;

-- Human review queue for unusual transactions
SELECT transaction_id, transaction_date, category, region, channel,
       revenue, expense, gross_profit, margin_pct, anomaly_score
FROM transactions
WHERE is_anomaly = 1
ORDER BY anomaly_score DESC;

-- Transaction segment profiles
SELECT segment, COUNT(*) AS transactions,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(AVG(revenue), 2) AS avg_revenue,
       ROUND(AVG(gross_profit), 2) AS avg_profit,
       ROUND(AVG(margin_pct), 2) AS avg_margin_pct
FROM transactions
GROUP BY segment
ORDER BY avg_revenue;
