-- Gasto mensal por categoria.
DROP TABLE IF EXISTS mart_monthly_spend;
CREATE TABLE mart_monthly_spend AS
SELECT purchase_month, category, ROUND(SUM(line_total), 2) AS spend, COUNT(*) AS items
FROM fct_price_history
GROUP BY purchase_month, category
ORDER BY purchase_month, category;
