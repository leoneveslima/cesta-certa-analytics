-- Preço de cada produto em cada mercado (só compara 'un' com 'un' e 'kg' com 'kg').
DROP TABLE IF EXISTS mart_price_by_store;
CREATE TABLE mart_price_by_store AS
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY product_id, mode, store ORDER BY purchase_date DESC) AS rn
    FROM fct_price_history
)
SELECT
    product_id,
    MAX(product_name)                                   AS product_name,
    mode,
    store,
    COUNT(*)                                            AS observations,
    ROUND(AVG(unit_price), 2)                           AS avg_price,
    ROUND(MIN(unit_price), 2)                           AS min_price,
    ROUND(MAX(unit_price), 2)                           AS max_price,
    MAX(CASE WHEN rn = 1 THEN unit_price END)           AS last_price,
    MAX(CASE WHEN rn = 1 THEN purchase_date END)        AS last_date
FROM ranked
GROUP BY product_id, mode, store;
