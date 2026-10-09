-- severity: error
-- description: o índice de preços começa em 100 no mês-base
SELECT purchase_month, price_index FROM (SELECT * FROM mart_price_index ORDER BY purchase_month LIMIT 1)
WHERE ABS(price_index - 100) > 0.001;
