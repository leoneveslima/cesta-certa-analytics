-- Quem é mais barato? Compara cada par de mercados só nos produtos que os dois têm
-- (mesma regra do app: o veredito vale apenas para itens em comum), usando o último preço.
DROP TABLE IF EXISTS mart_store_comparison;
CREATE TABLE mart_store_comparison AS
WITH pares AS (
    SELECT a.store AS store_a, b.store AS store_b, a.last_price AS price_a, b.last_price AS price_b
    FROM mart_price_by_store a
    JOIN mart_price_by_store b
      ON a.product_id = b.product_id AND a.mode = b.mode AND a.store < b.store
)
SELECT
    store_a,
    store_b,
    COUNT(*)                                                       AS common_products,
    ROUND(SUM(price_a), 2)                                         AS basket_a,
    ROUND(SUM(price_b), 2)                                         AS basket_b,
    CASE WHEN SUM(price_a) < SUM(price_b) THEN store_a
         WHEN SUM(price_b) < SUM(price_a) THEN store_b
         ELSE 'empate' END                                         AS cheaper,
    ROUND(100.0 * ABS(SUM(price_a) - SUM(price_b)) / MIN(SUM(price_a), SUM(price_b)), 1) AS diff_pct
FROM pares
GROUP BY store_a, store_b
HAVING COUNT(*) >= 3;
