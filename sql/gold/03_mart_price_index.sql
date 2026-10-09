-- Índice de preços da cesta pessoal (base 100 no primeiro mês).
-- Cesta fixa: produtos comprados em pelo menos 6 meses distintos, ponderados pela quantidade média.
-- Em cada mês compara-se só com os produtos que existem no mês-base e no mês (índice de Laspeyres encadeado nos itens em comum).
DROP TABLE IF EXISTS mart_price_index;
CREATE TABLE mart_price_index AS
WITH mensal AS (
    SELECT product_id, mode, purchase_month,
           AVG(unit_price) AS price, AVG(qty) AS qty
    FROM fct_price_history
    GROUP BY product_id, mode, purchase_month
),
cesta AS (
    SELECT product_id, mode, AVG(qty) AS weight
    FROM mensal GROUP BY product_id, mode
    HAVING COUNT(*) >= 6
),
base AS (SELECT MIN(purchase_month) AS month FROM mensal),
precos AS (
    SELECT m.purchase_month, m.product_id, m.mode, c.weight, m.price,
           b.price AS base_price
    FROM mensal m
    JOIN cesta c USING (product_id, mode)
    JOIN mensal b ON b.product_id = m.product_id AND b.mode = m.mode
                 AND b.purchase_month = (SELECT month FROM base)
)
SELECT
    purchase_month,
    COUNT(*)                                                    AS products_in_basket,
    ROUND(100.0 * SUM(weight * price) / SUM(weight * base_price), 2) AS price_index,
    ROUND(SUM(weight * price), 2)                               AS basket_cost
FROM precos
GROUP BY purchase_month
ORDER BY purchase_month;
